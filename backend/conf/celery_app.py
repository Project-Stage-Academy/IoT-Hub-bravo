import os
from celery import Celery
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('iot-hub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# for logging
app.conf.worker_hijack_root_logger = False # to keep custom logging; don't hijack root logger
app.conf.worker_redirect_stdouts = True # False = no print() stuff as logs, True is default

### TEST 1
@app.task
def add(x, y):
    time.sleep(1)
    return x + y

### TEST 2
@app.task
def check_logging():
    print("HELLO FROM PRINT")    
