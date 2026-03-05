import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from unittest.mock import ANY
from django.core.cache import caches

from apps.users.models import User
from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule
from apps.rules.services.rule_processor import RuleProcessor
from apps.rules.services.condition_evaluator import ConditionEvaluator
from apps.rules.services.action import Action
from apps.rules.utils.rule_engine_utils import PostgresTelemetryRepository

# ========
# Helpers
# ========

def create_telemetry(device_metric, value, created_at=None):
    """Helper function to create telemetry"""
    return Telemetry.objects.create(
        device_metric=device_metric,
        value_jsonb={"t": "numeric", "v": value},
        created_at=created_at or timezone.now(),
    )


def create_rule(device_metric, condition, action="notify", is_active=True):
    """Helper function to create rule"""
    return Rule.objects.create(
        device_metric=device_metric, condition=condition, action=action, is_active=is_active
    )


# =========
# Fixtures
# =========

@pytest.fixture
def user():
    return User.objects.create(username="test", email="a@b.com", password="123")


@pytest.fixture
def device(user):
    return Device.objects.create(user=user, serial_id="dev1", name="Device 1")


@pytest.fixture
def temperature_metric():
    return Metric.objects.create(metric_type="temperature", data_type="numeric")


@pytest.fixture
def device_metric_temperature(device, temperature_metric):
    """Creates device_metric on temperature"""
    return DeviceMetric.objects.create(device=device, metric=temperature_metric)


@pytest.fixture
def rule_processor():
    return RuleProcessor()


@pytest.fixture
def condition_evaluator():
    return ConditionEvaluator()


@pytest.fixture
def temperature_threshold_rule(device_metric_temperature):
    """Return threshold type rule"""
    return create_rule(
        device_metric_temperature,
        {"type": "threshold", "operator": ">", "value": 100}
    )


@pytest.fixture
def rule_with_three_temperature_telemeties(device_metric_temperature):
    """Create a rate-type rule and 3 telemetry entries within duration"""
    now = timezone.now()
    for v in [100, 105, 110]:
        create_telemetry(device_metric_temperature, v, now - timedelta(minutes=1))
    
    rule = create_rule(device_metric_temperature, {"type": "rate", "count": 3, "duration_minutes": 5})
    latest_telemetry = Telemetry.objects.last()
    return rule, latest_telemetry


@pytest.fixture
def rule_with_two_temperature_telemeties(device_metric_temperature):
    """Create a rate-type rule and 2 telemetry entries within duration"""
    now = timezone.now()
    for v in [100, 105]:
        create_telemetry(device_metric_temperature, v, now - timedelta(minutes=1))
    
    rule = create_rule(device_metric_temperature, {"type": "rate", "count": 3, "duration_minutes": 5})
    latest_telemetry = Telemetry.objects.last()
    return rule, latest_telemetry


@pytest.fixture
def setup_mocks():
    with patch.object(ConditionEvaluator, "evaluate") as mock_eval, \
        patch.object(Action, "dispatch_action") as mock_dispatch:
        yield {"eval": mock_eval, "dispatch": mock_dispatch}


@pytest.fixture
def high_temperature_telemetry(device_metric_temperature):
    """Cretes telemetry with high value (111)"""
    return create_telemetry(device_metric_temperature, value=111)


@pytest.fixture
def low_temperature_telemetry(device_metric_temperature):
    """Cretes telemetry with low value (80)"""
    return create_telemetry(device_metric_temperature, value=80)


@pytest.fixture
def humidity_metric():
    return Metric.objects.create(metric_type="humidity", data_type="numeric")


@pytest.fixture
def other_device(user):
    return Device.objects.create(user=user, serial_id="dev2", name="Device 2")


@pytest.fixture
def other_device_metric_humidity(other_device, humidity_metric):
    return DeviceMetric.objects.create(device=other_device, metric=humidity_metric)


@pytest.fixture
def high_humidity_telemetry_other_device(other_device_metric_humidity):
    """Cretes telemetry with high humidity value (80)"""
    return create_telemetry(other_device_metric_humidity, value=60)


@pytest.fixture
def low_humidity_telemetry_other_device(other_device_metric_humidity):
    """Cretes telemetry with low humidity value (20)"""
    return create_telemetry(other_device_metric_humidity, value=20)


@pytest.fixture
def humidity_threshold_rule_other_device(other_device_metric_humidity):
    """Return threshold type rule"""
    return create_rule(
        other_device_metric_humidity,
        {"type": "threshold", "operator": ">", "value": 50}
    )


@pytest.fixture
def mock_action():
    with patch.object(Action, "dispatch_action") as mock:
        yield mock


@pytest.fixture(autouse=True)
def clear_rules_cache():
    caches["rules"].clear()


@pytest.fixture(autouse=True)
def force_postgres_repository():
    """Force rule engine to use PostgreSQL repository, bypassing Redis"""
    with patch(
        "apps.rules.services.rule_processor.choose_repository",
        return_value=PostgresTelemetryRepository()
    ):
        yield


@pytest.fixture
def composite_and_rule_with_three_temperature_telemetry(device_metric_temperature):
    now = timezone.now()

    for v in [100, 95, 99]:
        create_telemetry(device_metric_temperature, v, now - timedelta(minutes=1))

    rule = create_rule(
        device_metric_temperature,
        {
            "type": "composite",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 90},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
    )

    latest_telemetry = Telemetry.objects.last()
    
    return rule, latest_telemetry


@pytest.fixture
def composite_and_rule_with_three_low_temperature_telemetry(device_metric_temperature):
    """Create 3 low temparature telemetries with OR composite rule"""
    now = timezone.now()

    for v in [20, 10, 9]:
        create_telemetry(device_metric_temperature, v, now - timedelta(minutes=1))

    rule = create_rule(
        device_metric_temperature,
        {
            "type": "composite",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 90},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
    )

    latest_telemetry = Telemetry.objects.last()
    
    return rule, latest_telemetry


@pytest.fixture
def composite_or_rule_with_two_temperature_telemetry(device_metric_temperature):
    """Create 2 temparature telemetries with OR composite rule"""
    now = timezone.now()

    for v in [100, 95]:
        create_telemetry(device_metric_temperature, v, now - timedelta(minutes=1))

    rule = create_rule(
        device_metric_temperature,
        {
            "type": "composite",
            "operator": "OR",
            "conditions": [
                {"type": "threshold", "operator": ">", "value": 90},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ],
        },
    )

    latest_telemetry = Telemetry.objects.last()
    
    return rule, latest_telemetry


@pytest.fixture
def threshold_condition_factory():
    def _create(operator=">", value=100):
        return {
            "type": "threshold",
            "operator": operator,
            "value": value,
        }
    return _create


@pytest.fixture
def rate_condition_factory():
    def _create(count=3, duration_minutes=5):
        return {
            "type": "rate",
            "count": count,
            "duration_minutes": duration_minutes,
        }
    return _create


@pytest.fixture
def composite_condition_factory():
    def _create(operator="AND", conditions=None):
        if conditions is None:
            conditions = [
                {"type": "threshold", "operator": ">", "value": 90},
                {"type": "rate", "count": 3, "duration_minutes": 5},
            ]
        return {
            "type": "composite",
            "operator": operator,
            "conditions": conditions,
        }
    return _create


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.django_db
def test_rule_processor_calls_dispatch_and_eval(rule_processor, device_metric_temperature, setup_mocks, high_temperature_telemetry):
    create_rule(device_metric_temperature, {"type": "threshold", "operator": ">", "value": 100})

    setup_mocks["eval"].return_value = True

    rule_processor.run(high_temperature_telemetry)

    assert setup_mocks["eval"].called
    assert setup_mocks["dispatch"].called


@pytest.mark.django_db
def test_rule_processor_triggers_action_for_threshold(rule_processor, temperature_threshold_rule, high_temperature_telemetry, mock_action):
    """Dispatch action when telemetry exceeds threshold"""
    rule_processor.run(high_temperature_telemetry)

    mock_action.assert_called_once_with(temperature_threshold_rule, ANY)


@pytest.mark.django_db
def test_rule_processor_no_dispatch_action_when_condition_threshold_type_false(
    rule_processor, temperature_threshold_rule, mock_action, low_temperature_telemetry
):
    """Dispatch should NOT be called when condition is FALSE"""
    rule_processor.run(low_temperature_telemetry)

    mock_action.assert_not_called()


@pytest.mark.django_db
def test_rule_processor_only_processes_matching_device_metric_threshold_type(
    rule_processor, high_humidity_telemetry_other_device, temperature_threshold_rule, mock_action
):
    """Test that rules only process telemetry from their device_metric"""
    rule_processor.run(high_humidity_telemetry_other_device)

    mock_action.assert_not_called()


@pytest.mark.django_db
def test_rule_processor_triggers_action_for_rate_type_when_count_met(
    rule_processor, rule_with_three_temperature_telemeties, mock_action
):
    """Dispatch action when telemetry count within duration meets the rule count"""
    rule, latest_telemetry = rule_with_three_temperature_telemeties

    rule_processor.run(latest_telemetry)

    mock_action.assert_called_once_with(rule, ANY)



@pytest.mark.django_db
def test_rule_processor_dispatch_action_when_condition_rate_type_false(rule_processor, rule_with_two_temperature_telemeties, mock_action):
    _, latest_telemetry = rule_with_two_temperature_telemeties

    rule_processor.run(latest_telemetry)
    mock_action.assert_not_called()


@pytest.mark.django_db
def test_rule_processor_dispatch_when_condition_composite_and_true(
    rule_processor,
    composite_and_rule_with_three_temperature_telemetry, mock_action
):  
    rule, latest_telemetry = composite_and_rule_with_three_temperature_telemetry

    rule_processor.run(latest_telemetry)

    mock_action.assert_called_once_with(rule, ANY)


@pytest.mark.django_db
def test_rule_processor_dispatch_when_condition_composite_or_true(
    rule_processor,
    composite_or_rule_with_two_temperature_telemetry, mock_action
):  
    rule, latest_telemetry = composite_or_rule_with_two_temperature_telemetry

    rule_processor.run(latest_telemetry)

    mock_action.assert_called_once_with(rule, ANY)


@pytest.mark.django_db
def test_rule_processor_dispatch_when_condition_composite_and_false(
    rule_processor,
    composite_and_rule_with_three_low_temperature_telemetry, mock_action
):  
    _, latest_telemetry = composite_and_rule_with_three_low_temperature_telemetry

    rule_processor.run(latest_telemetry)

    mock_action.assert_not_called()


@pytest.mark.django_db
def test_rule_processor_unknown_rule_type(rule_processor, device_metric_temperature, high_temperature_telemetry, mock_action):
    """Dispatch should NOT be called with unknown rule type"""
    create_rule(
        device_metric_temperature,
        {"type": "custom", "operator": ">", "value": 100},
    )

    rule_processor.run(high_temperature_telemetry)

    mock_action.assert_not_called()


@pytest.mark.django_db
def test_dispatch_invalid_condition_operator(rule_processor, device_metric_temperature, high_temperature_telemetry, mock_action):
    """Dispatch should NOT be called with INVALID operator"""
    create_rule(
        device_metric_temperature,
        {"type": "threshold", "operator": "INVALID", "value": 100},
    )

    rule_processor.run(high_temperature_telemetry)

    mock_action.assert_not_called()


@pytest.mark.django_db
def test_rule_condition_parsing_threshold_valid(
    device_metric_temperature,
    threshold_condition_factory,
):
    condition = threshold_condition_factory(">", 100)

    rule = create_rule(device_metric_temperature, condition)

    assert rule.condition == condition


@pytest.mark.django_db
def test_rule_condition_parsing_rate_valid(
    device_metric_temperature,
    rate_condition_factory,
):
    condition = rate_condition_factory(count=3, duration_minutes=5)

    rule = create_rule(device_metric_temperature, condition)

    assert rule.condition == condition


@pytest.mark.django_db
def test_rule_condition_parsing_composite_valid(
    device_metric_temperature,
    threshold_condition_factory,
    rate_condition_factory,
    composite_condition_factory,
):
    condition = composite_condition_factory(
        operator="AND",
        conditions=[
            threshold_condition_factory(">", 90),
            rate_condition_factory(3, 5),
        ],
    )

    rule = create_rule(device_metric_temperature, condition)

    assert rule.condition == condition
    assert rule.condition["type"] == "composite"
    assert rule.condition["operator"] == "AND"
    assert len(rule.condition["conditions"]) == 2


@pytest.mark.django_db
def test_threshold_operator_with_float_values(device_metric_temperature, rule_processor, mock_action):
    """Test threshold operators work with float values"""
    telemetry = create_telemetry(device_metric_temperature, 25.7)
    rule = create_rule(device_metric_temperature, {"type": "threshold", "operator": ">", "value": 25.5})

    rule_processor.run(telemetry)

    mock_action.assert_called_once_with(rule, ANY) # "Float comparison should work: 25.7 > 25.5"


@pytest.mark.django_db
def test_threshold_operator_with_negative_values(device_metric_temperature, rule_processor, mock_action):
    """Test threshold operators work with negative values"""
    telemetry = create_telemetry(device_metric_temperature, -10)
    rule = create_rule(device_metric_temperature, {"type": "threshold", "operator": "<", "value": -5})

    rule_processor.run(telemetry)

    mock_action.assert_called_once_with(rule, ANY) # "Negative comparison should work: -10 < -5"


@pytest.mark.django_db
def test_inactive_rule_does_not_trigger_threshold(
    device_metric_temperature,
    rule_processor,
    threshold_condition_factory,
    high_temperature_telemetry,
    mock_action
):
    """Inactive rule should not create events even when condition is met"""

    condition = threshold_condition_factory(">", 100)

    create_rule(
        device_metric_temperature,
        condition,
        is_active=False,
    )

    rule_processor.run(high_temperature_telemetry)

    mock_action.assert_not_called()


# @pytest.mark.django_db
# def test_inactive_rule_does_not_trigger_rate(
#     device_metric,
#     rule_processor,
#     rate_condition_factory,
# ):
#     """Inactive rate rule should not create events"""

#     condition = rate_condition_factory(count=3, duration_minutes=5)

#     rule = create_rule(
#         device_metric,
#         condition,
#         is_active=False,
#     )

#     rule_processor.run(rate_satisfied_telemetry)

#     assert Event.objects.filter(rule=rule).count() == 0

# @pytest.mark.django_db
# @pytest.mark.parametrize(
#     "operator,threshold,telemetry_value,should_trigger",
#     [
#         # Greater than
#         (">", 100, 111, True),
#         (">", 100, 100, False),
#         (">", 100, 90, False),
#         # Less than
#         ("<", 100, 90, True),
#         ("<", 100, 100, False),
#         ("<", 100, 111, False),
#         # Greater than or equal
#         (">=", 100, 111, True),
#         (">=", 100, 100, True),
#         (">=", 100, 90, False),
#         # Less than or equal
#         ("<=", 100, 90, True),
#         ("<=", 100, 100, True),
#         ("<=", 100, 111, False),
#         # Equal
#         ("==", 100, 100, True),
#         ("==", 100, 99, False),
#         ("==", 100, 101, False),
#         # Not equal
#         ("!=", 100, 99, True),
#         ("!=", 100, 101, True),
#         ("!=", 100, 100, False),
#     ],
# )
# def test_threshold_all_operators(
#     device_metric, rule_processor, operator, threshold, telemetry_value, should_trigger
# ):
#     """Test all threshold operators with various values"""
#     telemetry = create_telemetry(device_metric, telemetry_value)
#     rule = create_rule(
#         device_metric, {"type": "threshold", "operator": operator, "value": threshold}
#     )

#     rule_processor.run(telemetry)

#     events = Event.objects.filter(rule=rule)
#     expected_count = 1 if should_trigger else 0
#     assert events.count() == expected_count, (
#         f"Operator '{operator}': {telemetry_value} {operator} {threshold} "
#         f"should {'trigger' if should_trigger else 'not trigger'}"
#     )





# # ============================================================================
# # RATE RULE EDGE CASES
# # ============================================================================


# @pytest.mark.django_db
# def test_rate_rule_exact_count_at_boundary(device_metric, rule_processor):
#     """Test rate rule triggers when exactly at count threshold"""
#     now = timezone.now()

#     # Create exactly 3 telemetry entries within 5 minutes
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(device_metric, {"type": "rate", "count": 3, "duration_minutes": 5})

#     rule_processor.run(Telemetry.objects.last())

#     events = Event.objects.filter(rule=rule)
#     assert events.count() == 1, "Should trigger with exactly 3 events"


# @pytest.mark.django_db
# def test_rate_rule_exact_duration_boundary(device_metric, rule_processor):
#     """Test rate rule at exact duration boundary (edge case)"""
#     now = timezone.now()

#     # Create telemetry exactly at the 5-minute boundary
#     create_telemetry(device_metric, 100, now - timedelta(minutes=5))
#     create_telemetry(device_metric, 105, now - timedelta(minutes=3))
#     create_telemetry(device_metric, 110, now - timedelta(minutes=1))

#     rule = create_rule(device_metric, {"type": "rate", "count": 3, "duration_minutes": 5})

#     rule_processor.run(Telemetry.objects.last())

#     events = Event.objects.filter(rule=rule)
#     # This tests the boundary behavior - adjust assertion based on implementation
#     assert events.count() in [0, 1], "Boundary behavior should be consistent"


# @pytest.mark.django_db
# def test_rate_rule_with_zero_duration(device_metric, rule_processor):
#     """Test rate rule behavior with zero duration (edge case)"""
#     now = timezone.now()

#     create_telemetry(device_metric, 100, now)
#     create_telemetry(device_metric, 105, now)
#     create_telemetry(device_metric, 110, now)

#     rule = create_rule(device_metric, {"type": "rate", "count": 3, "duration_minutes": 0})

#     rule_processor.run(Telemetry.objects.last())

#     # Should handle gracefully - either raise error or treat as instant
#     events = Event.objects.filter(rule=rule)
#     assert events.count() >= 0, "Should handle zero duration without crashing"


# # ============================================================================
# # INACTIVE RULE TESTS
# # ============================================================================


# @pytest.mark.django_db
# def test_inactive_rule_does_not_trigger_rate(device_metric, rule_processor):
#     """Inactive rate rule should not create events"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(
#         device_metric, {"type": "rate", "count": 3, "duration_minutes": 5}, is_active=False
#     )

#     rule_processor.run(Telemetry.objects.last())

#     assert Event.objects.filter(rule=rule).count() == 0, "Inactive rate rule should not trigger"


# @pytest.mark.django_db
# def test_inactive_rule_does_not_trigger_composite(device_metric, rule_processor):
#     """Inactive composite rule should not create events"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(
#         device_metric,
#         {
#             "type": "composite",
#             "operator": "AND",
#             "conditions": [
#                 {"type": "threshold", "operator": ">", "value": 90},
#                 {"type": "rate", "count": 3, "duration_minutes": 5},
#             ],
#         },
#         is_active=False,
#     )

#     rule_processor.run(Telemetry.objects.last())

#     assert (
#         Event.objects.filter(rule=rule).count() == 0
#     ), "Inactive composite rule should not trigger"


# # ============================================================================
# # CONDITION EVALUATOR UNIT TESTS
# # ============================================================================


# @pytest.mark.django_db
# def test_condition_evaluator_threshold_direct(device_metric, condition_evaluator):
#     """Direct unit test of ConditionEvaluator.evaluate() for threshold"""
#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 100})

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is True, "Evaluator should return True for 111 > 100"


# @pytest.mark.django_db
# def test_condition_evaluator_threshold_false_direct(device_metric, condition_evaluator):
#     """Direct unit test of ConditionEvaluator.evaluate() returning False"""
#     telemetry = create_telemetry(device_metric, 90)
#     rule = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 100})

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is False, "Evaluator should return False for 90 > 100"


# @pytest.mark.django_db
# def test_condition_evaluator_rate_direct(device_metric, condition_evaluator):
#     """Direct unit test of ConditionEvaluator.evaluate() for rate"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(device_metric, {"type": "rate", "count": 3, "duration_minutes": 5})
#     telemetry = Telemetry.objects.last()

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is True, "Evaluator should return True when rate condition is met"


# @pytest.mark.django_db
# def test_condition_evaluator_composite_and_direct(device_metric, condition_evaluator):
#     """Direct unit test of ConditionEvaluator.evaluate() for composite AND"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(
#         device_metric,
#         {
#             "type": "composite",
#             "operator": "AND",
#             "conditions": [
#                 {"type": "threshold", "operator": ">", "value": 90},
#                 {"type": "rate", "count": 3, "duration_minutes": 5},
#             ],
#         },
#     )
#     telemetry = Telemetry.objects.last()

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is True, "Evaluator should return True when both AND conditions are met"


# @pytest.mark.django_db
# def test_condition_evaluator_composite_or_direct(device_metric, condition_evaluator):
#     """Direct unit test of ConditionEvaluator.evaluate() for composite OR"""
#     now = timezone.now()
#     # Only threshold passes, rate fails
#     create_telemetry(device_metric, 111, now)

#     rule = create_rule(
#         device_metric,
#         {
#             "type": "composite",
#             "operator": "OR",
#             "conditions": [
#                 {"type": "threshold", "operator": ">", "value": 100},
#                 {"type": "rate", "count": 5, "duration_minutes": 5},  # Will fail
#             ],
#         },
#     )
#     telemetry = Telemetry.objects.last()

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is True, "Evaluator should return True when at least one OR condition is met"


# @pytest.mark.django_db
# def test_condition_evaluator_unknown_type_returns_false(device_metric, condition_evaluator):
#     """Test that unknown condition type returns False and logs warning"""
#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(device_metric, {"type": "unknown_type", "operator": ">", "value": 100})

#     result = condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert result is False, "Unknown condition type should return False, not raise exception"


# @pytest.mark.django_db
# def test_condition_evaluator_unknown_type_logs_warning(device_metric, condition_evaluator, caplog):
#     """Test that unknown condition type logs appropriate warning"""
#     import logging

#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(device_metric, {"type": "unknown_type", "operator": ">", "value": 100})

#     with caplog.at_level(logging.WARNING):
#         condition_evaluator.evaluate(rule.condition, device_metric, telemetry)

#     assert "Unknown condition type: unknown_type" in caplog.text


# @pytest.mark.django_db
# def test_rule_processor_invalid_condition_duration_minutes_rate_rule(
#     device_metric, rule_processor
# ):
#     """Event should not be created when condition duration_minutes has invalid type"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     rule = create_rule(device_metric, {"type": "rate", "duration_minutes": "12", "count": 3})

#     rule_processor.run(Telemetry.objects.last())

#     events = Event.objects.filter(rule=rule)
#     assert (
#         events.count() == 1
#     ), "Event created when duration_minutes has invlid type (because of default value)"


# @pytest.mark.django_db
# def test_rule_processor_invalid_condition_count_type_rate_rule(device_metric, rule_processor):
#     """Event should not be created when condition duration_minutes has invalid type"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     create_rule(device_metric, {"type": "rate", "duration_minutes": 12, "count": "3"})

#     with pytest.raises(ValueError, match="Invalid count value"):
#         rule_processor.run(Telemetry.objects.last())


# @pytest.mark.django_db
# def test_rule_processor_invalid_condition_count_value_rate_rule(device_metric, rule_processor):
#     """Count can't be <0"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     create_rule(device_metric, {"type": "rate", "duration_minutes": 12, "count": -1})

#     with pytest.raises(ValueError, match="Invalid count value"):
#         rule_processor.run(Telemetry.objects.last())


# @pytest.mark.django_db
# def test_rule_processor_invalid_condition_minutes_value_rate_rule(device_metric, rule_processor):
#     """Minutes can't be <0"""
#     now = timezone.now()
#     for v in [100, 105, 110]:
#         create_telemetry(device_metric, v, now - timedelta(minutes=1))

#     create_rule(device_metric, {"type": "rate", "duration_minutes": 12, "count": -1})

#     with pytest.raises(ValueError, match="Invalid count value"):
#         rule_processor.run(Telemetry.objects.last())


# # ============================================================================
# # MULTIPLE RULES TESTS
# # ============================================================================


# @pytest.mark.django_db
# def test_multiple_rules_for_same_device_metric(device_metric, rule_processor):
#     """Test that multiple rules can be triggered by the same telemetry"""
#     telemetry = create_telemetry(device_metric, 111)

#     rule1 = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 100})
#     rule2 = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 50})

#     rule_processor.run(telemetry)

#     # Both rules should trigger
#     assert Event.objects.filter(rule=rule1).count() == 1
#     assert Event.objects.filter(rule=rule2).count() == 1


# @pytest.mark.django_db
# def test_rule_does_not_create_duplicate_events(device_metric, rule_processor):
#     """Test that running processor twice doesn't create duplicate events"""
#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 100})

#     # Run processor twice with same telemetry
#     rule_processor.run(telemetry)
#     rule_processor.run(telemetry)

#     # Should only create one event (or test the actual expected behavior)
#     events = Event.objects.filter(rule=rule)
#     # Adjust assertion based on actual business logic
#     assert events.count() >= 1, "Should handle multiple runs gracefully"


# # ============================================================================
# # EVENT CREATION TESTS
# # ============================================================================


# @pytest.mark.django_db
# def test_event_contains_correct_data(device_metric, rule_processor):
#     """Test that created Event contains correct reference data"""
#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(device_metric, {"type": "threshold", "operator": ">", "value": 100})

#     rule_processor.run(telemetry)

#     event = Event.objects.filter(rule=rule).first()
#     assert event is not None
#     assert event.rule == rule
#     # Add more assertions based on Event model fields
#     # assert event.telemetry == telemetry  # if such field exists
#     # assert event.created_at is not None


# @pytest.mark.django_db
# def test_event_action_field_set_correctly(device_metric, rule_processor):
#     """Test that Event inherits action from Rule"""
#     telemetry = create_telemetry(device_metric, 111)
#     rule = create_rule(
#         device_metric, {"type": "threshold", "operator": ">", "value": 100}, action="email_alert"
#     )

#     rule_processor.run(telemetry)

#     event = Event.objects.filter(rule=rule).first()
#     # Adjust based on how Event stores action
#     assert event.rule.action == "email_alert"
