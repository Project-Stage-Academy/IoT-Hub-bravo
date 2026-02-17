from __future__ import annotations

from typing import Any, Optional

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.rules.models.event import Event
from apps.rules.serializers.event_serializer import (
    EventListQuerySerializer,
    EventListItemSerializer,
    EventDetailSerializer,
)
from apps.rules.services.event_service import (
    event_list,
    event_get,
    event_ack,
    EventListResult,
)


@csrf_exempt
@require_http_methods(["GET"])
def list_events(request):
    """
    GET /api/events/
    Supports filters:
    - rule_id
    - device_id
    - acknowledged
    - severity (reserved, ignored)
    Pagination:
    - limit
    - offset
    """
    serializer = EventListQuerySerializer(request.GET)

    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)

    result = event_list(query=serializer.validated_data)

    return JsonResponse(
        _list_response_json(
            count=result.count,
            limit=serializer.validated_data.limit,
            offset=serializer.validated_data.offset,
            events=result.results,
        ),
        status=200,
    )


@csrf_exempt
@require_http_methods(["GET"])
def event_detail(request, event_id: int):
    """
    GET /api/events/{id}/
    """
    try:
        event = event_get(event_id=event_id)
    except Event.DoesNotExist:
        return JsonResponse({"detail": "Event not found."}, status=404)

    data = EventDetailSerializer.to_dict(event)
    return JsonResponse(data, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def ack_event(request, event_id: int):
    """
    POST /api/events/{id}/ack
    Body: none
    """
    try:
        event = event_ack(event_id=event_id)
    except Event.DoesNotExist:
        return JsonResponse({"detail": "Event not found."}, status=404)

    return JsonResponse(EventDetailSerializer.to_dict(event), status=200)



# =========================
# Helpers
# =========================

def _list_response_json(
    *,
    count: int,
    limit: int,
    offset: int,
    events: list[Event],
) -> dict[str, Any]:
    return {
        "count": count,
        "limit": limit,
        "offset": offset,
        "results": [EventListItemSerializer.to_dict(e) for e in events],
    }
