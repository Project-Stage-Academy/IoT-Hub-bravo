import uuid

def generate_request_id() -> str:
    """Generate a unique request ID for logging and request tracing"""
    
    return str(uuid.uuid4())