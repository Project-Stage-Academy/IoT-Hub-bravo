import logging
from celery import current_task

from ..utils.logging_context import request_duration, request_id

class RequestContextFilter(logging.Filter):
    """
    Add request context for request logging
    """
    
    def filter(self, record):
        record.duration = request_duration.get()
        record.request_id = request_id.get()
        return True

class CeleryContextFilter(logging.Filter):
    """
    Add context for celery logging
    """
    def filter(self, record):
        record.task_id = None
        record.task_name = None

        if current_task and current_task.request:
            record.task_id = current_task.request.id
            record.task_name = current_task.name

        return True    