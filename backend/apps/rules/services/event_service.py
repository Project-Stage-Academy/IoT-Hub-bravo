from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet

from apps.rules.models.event import Event
from apps.rules.serializers.event_serializer import EventListQuery


@dataclass(slots=True)
class EventListResult:
    count: int
    results: list[Event]


def event_list(*, query: EventListQuery) -> EventListResult:
    """
    Returns paginated list of events with filters.

    Filters supported:
    - rule_id
    - acknowledged
    - device_serial_id (filter by trigger device serial ID)
    - severity (reserved, ignored for now)

    Pagination:
    - limit
    - offset

    Ordering:
    - newest first (rule_triggered_at desc)
    """
    qs = Event.objects.select_related("rule").all()

    qs = _apply_filters(qs, query=query)

    total = qs.count()

    qs = qs.order_by("-rule_triggered_at", "-id")[query.offset : query.offset + query.limit]

    return EventListResult(
        count=total,
        results=list(qs),
    )


def event_get(*, event_uuid: UUID | str) -> Event:
    """
    Get a single event by event_uuid.
    """
    return Event.objects.select_related("rule").get(event_uuid=event_uuid)


def event_ack(*, event_uuid: UUID | str) -> Event:
    """
    Acknowledge an event.

    Idempotent behavior:
    - if already acknowledged: keep it true
    - return updated event
    """
    event = Event.objects.select_related("rule").get(event_uuid=event_uuid)

    if not event.acknowledged:
        event.acknowledged = True
        event.save(update_fields=["acknowledged"])

    return event


def _apply_filters(qs: QuerySet[Event], *, query: EventListQuery) -> QuerySet[Event]:
    """TODO: severity filter is reserved for future use when severity field is added to Event model"""

    if query.rule_id is not None:
        qs = qs.filter(rule_id=query.rule_id)

    if query.acknowledged is not None:
        qs = qs.filter(acknowledged=query.acknowledged)

    # severity is not supported by model yet
    # if query.severity is not None:
    #     ...

    if query.device_serial_id is not None:
        qs = qs.filter(trigger_device_serial_id=query.device_serial_id)

    return qs
