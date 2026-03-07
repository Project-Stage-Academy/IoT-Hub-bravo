import json
from typing import Any


def is_json_serializable(value: Any) -> bool:
    """Check if the value is a valid JSON object."""
    try:
        json.dumps(value, ensure_ascii=False)
        return True
    except (TypeError, ValueError):
        return False
