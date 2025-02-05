#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery import Celery
from celery import Task
from flask import Flask
from flask_bootstrap import Bootstrap5
from geordash.events import CeleryEventsHandler
from geordash.owscapcache import OwsCapCache
from geordash.georchestraconfig import GeorchestraConfig
from geordash.result_backend.redisbackend import RedisClient
from geordash.checks.mapstore import MapstoreChecker
from config import url as redisurl
import threading
import logging
from os import getenv

from datetime import datetime, date, time
def format_datetime(value, format="%d %b %Y %I:%M %p"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    if  isinstance(value, float):
        return datetime.fromtimestamp(value).strftime(format)
    if  isinstance(value, str):
        return datetime.fromtimestamp(int(value)).strftime(format)
    return value.strftime(format)

def create_app() -> Flask:
    app = Flask(__name__, static_url_path='/gaia/static')

    @app.context_processor
    def inject_globals():
        instancename = app.extensions["conf"].get('instancename')
        return { 'instancename': instancename,
                'headerScript': app.extensions["conf"].get('headerScript'),
                'headerHeight': app.extensions["conf"].get('headerHeight'),
                'headerUrl': app.extensions["conf"].get('headerUrl'),
                'headerConfigFile': app.extensions["conf"].get('headerConfigFile'),
                'useLegacyHeader': app.extensions["conf"].get('useLegacyHeader'),
                'georchestraStyleSheet': app.extensions["conf"].get('georchestraStyleSheet'),
                'logoUrl': app.extensions["conf"].get('logoUrl')
            }

    app.jinja_env.filters['datetimeformat'] = format_datetime
    # cant work since its at /bootstrap and cant be below /gaia ?
    # app.config.update(BOOTSTRAP_SERVE_LOCAL=True)
    app.config.from_prefixed_env()
    # needs FLASK_DEBUG in the env, or flask --debug
    # app.config.update(EXPLAIN_TEMPLATE_LOADING=True)
    app.extensions["bootstrap"] = Bootstrap5(app)
    celery_init_app(app)

    conf = GeorchestraConfig()
    app.extensions["conf"] = conf
    app.extensions["owscache"] = OwsCapCache(conf, app)
    app.extensions["msc"] = MapstoreChecker(conf)
    app.extensions["rcli"] = RedisClient(redisurl, app)
    from . import views, api, admin, dashboard

    dashboard.dash_bp.register_blueprint(views.tasks_bp)
    dashboard.dash_bp.register_blueprint(api.api_bp)
    dashboard.dash_bp.register_blueprint(admin.admin_bp)
    app.register_blueprint(dashboard.dash_bp)
    if getenv('INVOCATION_ID') != None:
        gunicorn_logger = logging.getLogger('gunicorn.error')
        if len(gunicorn_logger.handlers) == 0:
            return app
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.handlers[0].setFormatter(logging.Formatter("%(levelname)s in %(module)s: %(message)s"))
        app.logger.setLevel(gunicorn_logger.level)
    else:
        app.logger.setLevel(logging.DEBUG)
    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object('geordash.celeryconfig')
    celery_app.set_default()
    if getenv('INVOCATION_ID') != None:
        celery_app.conf.worker_log_format = "%(levelname)s: %(message)s"
        celery_app.conf.worker_task_log_format = "%(task_name)s[%(task_id)s] - %(levelname)s: %(message)s"
    app.extensions["celery"] = celery_app
    events_handler = CeleryEventsHandler(app)
    evht = threading.Thread(name='evh',target=events_handler.start_listening, daemon=True)
    evht.start()
    return celery_app
