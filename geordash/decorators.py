#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
from functools import wraps
from flask import request, abort, jsonify
from flask import current_app as app


def is_superuser():
    roles = request.headers.get("sec-roles", "").split(";")
    return "ROLE_SUPERUSER" in roles


def debug_only(f):
    @wraps(f)
    def wrapped(**kwargs):
        if not app.debug:
            abort(404)
        return f(**kwargs)

    return wrapped


def check_role(role, json=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_roles = request.headers.get("sec-roles", "").split(";")
            if "ROLE_" + role not in user_roles:
                if json:
                    return jsonify({"message": "not authorized"}), 403
                return abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def non_concurrent_task(taskname):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            fqtn = taskname.__module__ + "." + taskname.__name__
            active_tasks = app.extensions["celery"].control.inspect().active()
            # if no worker is found, queue the task anyway
            if active_tasks is None:
                return func(*args, **kwargs)
            # look for a task with the same name and args
            for worker, tasks in active_tasks.items():
                for active_task in tasks:
                    if (
                        active_task["type"] == fqtn
                        and list(kwargs.values()) == active_task["args"]
                    ):
                        app.logger.warn(
                            f"{ fqtn }() task with args { list(kwargs.values()) } already "
                            + "running on { worker } with id {active_task['id']}, returning it"
                        )
                        return {"taskid": active_task["id"]}
            # didnt find the task, execute it
            return func(*args, **kwargs)

        return wrapper

    return decorator
