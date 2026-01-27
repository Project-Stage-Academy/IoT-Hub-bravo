import logging
import uuid
import time

from .utils import generate_request_id

class RequestLoggingMiddleware:
    """
    Middleware for request-level observability.

    Responsibilities:
    - Assign a unique request_id to each incoming HTTP request
    - Measure request processing duration
    - Log structured request metadata (method, path, status, user_id, duration)

    This middleware is part of the application's observability layer
    and is used for debugging, monitoring, and tracing requests
    across the system.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = generate_request_id()
        request.request_id = request_id
        start_time = time.time()

        response = self.get_response(request)

        duration = round(time.time() - start_time, 3)
        user_id = getattr(request.user, "id", None)


        logging.info(
            msg="Request completed",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "path": request.path,
                "method": request.method,
                "status": response.status_code,
                "duration": duration,
                "logger_name": "djangocustom",
            }
        )

        return response
