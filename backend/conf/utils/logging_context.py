from contextvars import ContextVar

# Context variables for logging
request_id: ContextVar[str] = ContextVar('request_id', default='no-request-id')
request_duration: ContextVar[float] = ContextVar('request_duration', default=None)

# optional
user_id: ContextVar[str] = ContextVar('user_id', default=None)
request_path: ContextVar[str] = ContextVar('request_path', default='')
