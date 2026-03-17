import json
from typing import Any, Optional

from django.http import JsonResponse

JsonPayload = dict[str, Any] | list[Any]


def parse_json_body(
    body: bytes,
    *,
    allow_array: bool = False,
) -> tuple[Optional[JsonPayload], Optional[JsonResponse]]:
    """
    Parse JSON from request body.

    Returns:
        (payload, None) on success
        (None, JsonResponse) on failure
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON.'}, status=400)

    if allow_array:
        ok = isinstance(payload, (dict, list))
        message = 'Payload must be a JSON object or a JSON array.'
    else:
        ok = isinstance(payload, dict)
        message = 'Payload must be a JSON object.'

    if not ok:
        return None, JsonResponse({'error': message}, status=400)
    return payload, None
