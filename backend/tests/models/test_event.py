"""Unit tests for Event model."""

import pytest
from datetime import timedelta
from django.utils import timezone

from apps.rules.models import Event
from tests.fixtures.factories import EventFactory, RuleFactory


pytestmark = pytest.mark.django_db


class TestEventCreation:
    """Tests for Event model creation."""

    def test_create_event_with_required_fields(self):
        """Test creating an event with required fields."""
        event = EventFactory()

        assert event.id is not None
        assert event.rule is not None
        assert event.timestamp is not None
        assert event.created_at is not None

    def test_event_default_not_acknowledged(self):
        """Test that events are not acknowledged by default."""
        event = EventFactory()

        assert event.acknowledged is False

    def test_create_acknowledged_event(self):
        """Test creating an acknowledged event."""
        event = EventFactory(acknowledged=True)

        assert event.acknowledged is True

    def test_event_has_auto_timestamp(self):
        """Test that event gets automatic timestamp."""
        event = EventFactory()
        event.refresh_from_db()

        assert event.timestamp is not None
        assert event.created_at is not None

    def test_event_with_custom_timestamp(self):
        """Test creating event with custom timestamp."""
        custom_time = timezone.now() - timedelta(hours=1)
        event = EventFactory(timestamp=custom_time)

        assert event.timestamp == custom_time


class TestEventRelationships:
    """Tests for Event foreign key relationships."""

    def test_event_belongs_to_rule(self):
        """Test that event is associated with a rule."""
        rule = RuleFactory()
        event = EventFactory(rule=rule)

        assert event.rule == rule
        assert event.rule.id == rule.id

    def test_cascade_delete_on_rule(self):
        """Test that deleting rule cascades to events."""
        event = EventFactory()
        rule = event.rule
        event_id = event.id

        rule.delete()

        assert not Event.objects.filter(id=event_id).exists()

    def test_multiple_events_per_rule(self):
        """Test that a rule can have multiple events."""
        rule = RuleFactory()
        time1 = timezone.now()
        time2 = time1 + timedelta(seconds=1)

        event1 = EventFactory(rule=rule, timestamp=time1)
        event2 = EventFactory(rule=rule, timestamp=time2)

        assert event1.rule == event2.rule
        assert Event.objects.filter(rule=rule).count() == 2


class TestEventAcknowledgement:
    """Tests for Event acknowledgement functionality."""

    def test_acknowledge_event(self):
        """Test acknowledging an event."""
        event = EventFactory(acknowledged=False)

        event.acknowledged = True
        event.save()
        event.refresh_from_db()

        assert event.acknowledged is True

    def test_unacknowledge_event(self):
        """Test removing acknowledgement from event."""
        event = EventFactory(acknowledged=True)

        event.acknowledged = False
        event.save()
        event.refresh_from_db()

        assert event.acknowledged is False


class TestEventStringRepresentation:
    """Tests for Event __str__ method."""

    def test_str_returns_formatted_string(self):
        """Test that __str__ returns formatted event info."""
        rule = RuleFactory(name="High Temp Alert")
        event = EventFactory(rule=rule)

        result = str(event)

        assert f"Event {event.id}" in result
        assert "High Temp Alert" in result
