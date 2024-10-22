from config import url
from celery.schedules import crontab

broker_url = url
result_backend = url
worker_concurrency = 1
#autoscale = 8,1
imports = ('geordash.checks.mapstore', 'geordash.checks.ows', 'geordash.checks.csw')
#worker_pool = solo
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s/%(threadName)s] WORKER %(message)s"
worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s/%(threadName)s] TASK %(task_name)s[%(task_id)s]: %(message)s"


# create the task entry in the backend when its started, not only when its finished
task_track_started = True
# debug print sql requests done to the backend
database_engine_options = {'echo': True}
# store task name etc in the backend https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
result_extended = True
result_expires = None
task_send_sent_event = True

# sample schedule, adapt for your platform
beat_schedule = {
  'check-ms-resources-every-night': {
    'task': 'geordash.checks.mapstore.check_resources',
    'schedule': crontab(minute=0, hour=0),
  },
  'check-gs-wms-layers-every-night': {
    'task': 'geordash.checks.ows.owsservice',
    'args': ('wms','/geoserver/ows'),
    'schedule': crontab(minute=15, hour=0),
  },
  'check-gs-wfs-layers-every-night': {
    'task': 'geordash.checks.ows.owsservice',
    'args': ('wfs','/geoserver/ows'),
    'schedule': crontab(minute=30, hour=0),
  },
  'check-gn-metadatas-every-night': {
    'task': 'geordash.checks.csw.check_catalog',
    'args': ['/geonetwork/srv/fre/csw'],
    'schedule': crontab(minute=45, hour=0),
  },
}
#otherwise scheduled hours is taken as UTC
timezone = 'Europe/Paris'
