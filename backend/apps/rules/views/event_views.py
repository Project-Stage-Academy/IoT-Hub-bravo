from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.rules.models.event import Event
from apps.rules.serializers.event_serializer import (
    EventListQuerySerializer,
    EventListItemSerializer,
    EventDetailSerializer,
    ExternalEventRequestSerializer,
    map_external_to_internal,
)
from apps.common.checker.redis_checker import build_redis_checker
from producers.kafka_producer import KafkaProducer, ProduceResult
from apps.rules.services.event_service import (
    event_list,
    event_get,
    event_ack,
)
from apps.users.decorators import jwt_required, role_required
from apps.rules.producers import get_external_events_producer


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
@role_required({"GET": ["client", "admin"]})
def list_events(request):
    """
    GET /api/events/
    Supports filters:
    - rule_id
    - device_serial_id
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
@jwt_required
@role_required({"GET": ["client", "admin"]})
def event_detail(request, event_uuid: UUID):
    """
    GET /api/events/{event_uuid}/
    """
    try:
        event = event_get(event_uuid=event_uuid)
    except Event.DoesNotExist:
        return JsonResponse({"detail": "Event not found."}, status=404)

    data = EventDetailSerializer.to_dict(event)
    return JsonResponse(data, status=200)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@role_required({"POST": ["client", "admin"]})
def ack_event(request, event_uuid: UUID):
    """
    POST /api/events/{event_uuid}/ack
    Body: none
    """
    try:
        event = event_ack(event_uuid=event_uuid)
    except Event.DoesNotExist:
        return JsonResponse({"detail": "Event not found."}, status=404)

    return JsonResponse(EventDetailSerializer.to_dict(event), status=200)


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


@csrf_exempt
@require_http_methods(["POST"])
# @jwt_required
# @role_required({"POST": ["client", "admin"]})
def receive_external_event(request):
    """
    POST /api/events/external/
    Receives events from external systems (webhooks/IoT platforms).
    Maps external data to internal actions and triggers rules.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"code": 400, "message": "Invalid JSON"}, status=400)

    serializer = ExternalEventRequestSerializer(body)
    if not serializer.is_valid():
        return JsonResponse(
            {"code": 400, "message": "Invalid event payload", "errors": serializer.errors},
            status=400,
        )

    validated_data = serializer.validated_data
    mapped_event = map_external_to_internal(validated_data)

    return _produce_data(payload=mapped_event, producer=None)


CHECKER = build_redis_checker()


def _produce_data(
    *,
    payload: dict,
    producer: Optional[KafkaProducer] = None,
):
    if not isinstance(payload, (dict, list)):
        return JsonResponse(
            {'errors': {'json': 'Payload must be a JSON object or a JSON array.'}},
            status=400,
        )

    if isinstance(payload, dict):
        payload = [payload]

    if len(payload) == 0:
        return JsonResponse(
            {'status': 'rejected', 'errors': {'payload': 'Payload array is empty.'}},
            status=422,
        )

    if producer is None:
        producer = get_external_events_producer()

    results = {
        'accepted': 0,
        'skipped': 0,
        'errors': {},
    }

    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            results['errors'][index] = 'Payload items must be JSON objects.'
            results['skipped'] += 1
            continue

        event_uuid = record.get("event_uuid")
        rule_triggered_at = record.get("rule_triggered_at")
        if not event_uuid:
            results['skipped'] += 1
            results['errors'][index] = "Missing event UUID"
            continue

        if not rule_triggered_at:
            results['skipped'] += 1
            results['errors'][index] = "Missing event timestamp of triggered rule"
            continue

        if not CHECKER.process(f"{event_uuid}:{rule_triggered_at}"):
            results['skipped'] += 1
            results['errors'][index] = "Duplicate event skipped"
            continue

        key = record.get("source", None)
        result = producer.produce(payload=record, key=key)
        if result == ProduceResult.ENQUEUED:
            results['accepted'] += 1
        else:
            results['errors'][index] = result.value

    body = {'status': 'accepted', **results}
    status_code = 202

    if results['accepted'] == 0 and results['skipped'] > 0:
        body['status'] = 'rejected'
        status_code = 422
    elif results['accepted'] == 0 and results['errors']:
        body['status'] = 'unavailable'
        status_code = 503

    return JsonResponse(body, status=status_code)
