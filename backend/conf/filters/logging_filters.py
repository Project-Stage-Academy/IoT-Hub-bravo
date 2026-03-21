import logging

from ..utils.logging_context import (
    request_duration,
    request_id,
    task_id_var,
    task_name_var,
)


class RequestContextFilter(logging.Filter):
    """
    Add request context for request logging
    """

    def filter(self, record):
        record.duration = request_duration.get()
        record.request_id = request_id.get()
        return True


class CeleryContextFilter(logging.Filter):
    def filter(self, record):
        record.task_id = task_id_var.get()
        record.task_name = task_name_var.get()
        return True
