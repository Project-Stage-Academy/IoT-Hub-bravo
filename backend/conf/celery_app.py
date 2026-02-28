import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

app = Celery("iot-hub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.imports = [
    "scripts.DB.delete_chunks",
    "scripts.DB.compress_chunks",
]
# for logging
app.conf.worker_hijack_root_logger = (
    False  # to keep custom logging; don't hijack root logger
)
app.conf.worker_redirect_stdouts = (
    True  # False = no print() stuff as logs, True is default
)


app.conf.beat_schedule = {
    # Compression every 30 days at 03:00
    "compress-every-30-days-3am": {
        "task": "scripts.DB.compress_chunks.compress_chunks",
        "schedule": crontab(hour=3, minute=0, day_of_month="1"),
    },
    # Deletion every year on January 13 at 03:00
    "delete-yearly-jan13-3am": {
        "task": "scripts.DB.delete_chunks.delete_chunks",
        "schedule": crontab(hour=3, minute=0, day_of_month="13", month_of_year="1"),
    },
}
