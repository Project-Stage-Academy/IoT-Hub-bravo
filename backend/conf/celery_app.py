import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('iot-hub')
app.config_from_object('django.conf:settings', namespace='CELERY')
# app.autodiscover_tasks()
app.autodiscover_tasks(['apps.devops'])

# for logging
app.conf.worker_hijack_root_logger = False # to keep custom logging; don't hijack root logger
app.conf.worker_redirect_stdouts = True # False = no print() stuff as logs, True is default


app.conf.beat_schedule = {
    'cleanup-every-day-3am': {
        'task': 'apps.devops.cleanup.cleanup_old_partitions',
        'schedule': crontab(hour=3, minute=0),
    },
}
