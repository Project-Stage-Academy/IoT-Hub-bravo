import json
from typing import Any


def is_json_serializable(value: Any) -> bool:
    """Check if the value is a valid JSON object."""
    try:
        json.dumps(value, ensure_ascii=False)
        return True
    except (TypeError, ValueError):
        return False


def json_equal(a: Any, b: Any) -> bool:
    """Compare two JSON-serializable values for equality."""
    json_a = json.dumps(a, sort_keys=True, ensure_ascii=False)
    json_b = json.dumps(b, sort_keys=True, ensure_ascii=False)
    return json_a == json_b
