from typing import Union
import json
from django.http import JsonResponse


def parse_json_request(body: bytes) -> Union[dict, JsonResponse]:
    """
    Safely parse JSON from request body.

    Args:
        body (bytes): Raw request body.

    Returns:
        dict: Parsed JSON object if valid.
        JsonResponse: JSON error response with status 400 if body is not valid JSON.
    """
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"code": 400, "message": "Invalid JSON"}, status=400)