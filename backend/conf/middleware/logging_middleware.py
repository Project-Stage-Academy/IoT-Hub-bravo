import uuid
import time

from ..utils.logging_context import request_duration, request_id


class LoggingMiddleware:
    """Middleware to set request context for logging"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        request_id.set(str(uuid.uuid4()))
        duration_ms = round(
            (time.time() - start_time) * 1000, 3
        )  # duration in miliseconds
        request_duration.set(duration_ms)
        response = self.get_response(request)

        return response
