"""Unit tests for Rule model."""

import pytest
from django.db import IntegrityError

from apps.rules.models import Rule
from tests.fixtures.factories import RuleFactory, DeviceMetricFactory

pytestmark = pytest.mark.django_db


class TestRuleCreation:
    """Tests for Rule model creation."""

    def test_create_rule_with_required_fields(self):
        """Test creating a rule with all required fields."""
        rule = RuleFactory()

        assert rule.id is not None
        assert rule.name is not None
        assert rule.condition is not None
        assert rule.action is not None
        assert rule.device_metric is not None

    def test_rule_default_is_active(self):
        """Test that rules are active by default."""
        rule = RuleFactory()

        assert rule.is_active is True

    def test_create_inactive_rule(self):
        """Test creating an inactive rule."""
        rule = RuleFactory(is_active=False)

        assert rule.is_active is False

    def test_rule_with_description(self):
        """Test creating a rule with optional description."""
        rule = RuleFactory(description="Temperature threshold alert")

        assert rule.description == "Temperature threshold alert"

    def test_rule_without_description(self):
        """Test that description is optional (can be null)."""
        rule = RuleFactory(description=None)

        assert rule.description is None


class TestRuleConditionAndAction:
    """Tests for Rule condition and action JSON fields."""

    def test_rule_condition_json(self):
        """Test that condition stores JSON correctly."""
        condition = {"operator": ">", "threshold": 30}
        rule = RuleFactory(condition=condition)

        assert rule.condition == condition
        assert rule.condition["operator"] == ">"
        assert rule.condition["threshold"] == 30

    def test_rule_action_json(self):
        """Test that action stores JSON correctly."""
        action = {"type": "email", "recipient": "admin@example.com"}
        rule = RuleFactory(action=action)

        assert rule.action == action
        assert rule.action["type"] == "email"

    def test_rule_complex_condition(self):
        """Test rule with complex nested condition."""
        condition = {
            "type": "and",
            "conditions": [
                {"field": "value", "operator": ">", "threshold": 25},
                {"field": "value", "operator": "<", "threshold": 100},
            ],
        }
        rule = RuleFactory(condition=condition)

        assert rule.condition["type"] == "and"
        assert len(rule.condition["conditions"]) == 2


class TestRuleRelationships:
    """Tests for Rule foreign key relationships."""

    def test_rule_belongs_to_device_metric(self):
        """Test that rule is associated with a device_metric."""
        device_metric = DeviceMetricFactory()
        rule = RuleFactory(device_metric=device_metric)

        assert rule.device_metric == device_metric
        assert rule.device_metric.id == device_metric.id

    def test_cascade_delete_on_device_metric(self):
        """Test that deleting device_metric cascades to rules."""
        rule = RuleFactory()
        device_metric = rule.device_metric
        rule_id = rule.id

        device_metric.delete()

        assert not Rule.objects.filter(id=rule_id).exists()

    def test_multiple_rules_per_device_metric(self):
        """Test that a device_metric can have multiple rules."""
        device_metric = DeviceMetricFactory()

        rule1 = RuleFactory(device_metric=device_metric, name="Rule 1")
        rule2 = RuleFactory(device_metric=device_metric, name="Rule 2")

        assert rule1.device_metric == rule2.device_metric
        assert Rule.objects.filter(device_metric=device_metric).count() == 2


class TestRuleStringRepresentation:
    """Tests for Rule __str__ method."""

    def test_str_returns_name(self):
        """Test that __str__ returns the rule name."""
        rule = RuleFactory(name="High Temperature Alert")

        assert str(rule) == "High Temperature Alert"
