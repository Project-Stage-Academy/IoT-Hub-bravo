import logging

from ..utils.logging_context import request_duration, request_id

class RequestContextFilter(logging.Filter):
    """Add request context for logs"""
    
    def filter(self, record):
        record.duration = request_duration.get()
        record.request_id = request_id.get()
        return True