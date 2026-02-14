import logging
from datetime import timedelta
from datetime import datetime
from typing import Tuple, Any
from django.db.models import Q, Count, Case, When

from apps.devices.models.telemetry import Telemetry
from apps.rules.models.rule import Rule

logger = logging.getLogger(__name__)

COMPARISON_OPERATOR_MAP = { # for filter
    ">": "gt",
    "<": "lt",
    ">=": "gte",
    "<=": "lte",
    "==": "exact",
    "!=": "exact",
}

DEFAULT_DURATION_MINUTES = 5  # default value for time window
DEFAULT_THRESHOLD_PERCENTAGE = 0.8  # default value to meet "threshold"


def _get_window(telemetry: Telemetry, minutes: int) -> Tuple[datetime, datetime]:
    """Returns the start and end of the time window for the given telemetry"""
    end = telemetry.created_at
    start = end - timedelta(minutes=minutes)
    return start, end


def _get_comparison_operator(condition: dict) -> str:
    """Returns the comparison operator for the condition"""
    op = condition.get("operator")
    if not op:
        raise ValueError("No comparison operator")
    return op


def _get_value(condition: dict, key: str = 'value') -> Any:
    """Extract value from condition dictionary"""
    value = condition.get(key)
    if value is None:
        logger.error(f"Missing required field '{key}' in condition")
        raise ValueError(f"Missing required field '{key}' in condition")
    return value


def _validate_metric(device_metric, telemetry: Telemetry) -> None:
    """Checks that the rule has a metric and it matches the telemetry metric"""
    condition_metric = device_metric.metric.metric_type
    if condition_metric is None:
        logger.error("Rule must contain a 'metric' field")
        raise ValueError("Rule must contain a 'metric' field")
    if condition_metric != telemetry.device_metric.metric.metric_type:
        logger.debug(
            "Rule metric does not match telemetry metric",
            extra={
                "condition_metric": condition_metric,
                "telemetry_metric": telemetry.device_metric.metric.metric_type,
            },
        )
        raise ValueError("Rule metric must match a telemetry metric field")


def _get_telemetries_in_window(telemetry: Telemetry, minutes: int):
    """Return all Telemetry objects for the same device_metric within the past `minutes` minutes"""
    start, end = _get_window(telemetry, minutes)
    return Telemetry.objects.filter(
        device_metric=telemetry.device_metric, created_at__gte=start, created_at__lte=end
    )


def _get_duration_minutes(condition: dict) -> int:
    """Get minutes duration for time window from rule.condition"""
    if "minutes" in condition:
        return condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

    if "duration_minutes" in condition:
        return condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

    return DEFAULT_DURATION_MINUTES


def _get_value_field(telemetry: Telemetry):
    """Get name (type) of the value telemtry field"""
    if telemetry.value_numeric is not None:
        return "value_numeric"
    if telemetry.value_bool is not None:
        return "value_bool"
    if telemetry.value_str is not None:
        return "value_str"

    raise ValueError("Telemetry has no value set")


def _build_filter_condition(telemetry: Telemetry, comparison_operator: str, condition_value: Any) -> Q:
    """Filter for match_count in threshold evaluator"""
    field_name = _get_value_field(telemetry)
    lookup = COMPARISON_OPERATOR_MAP.get(comparison_operator)

    if not lookup:
        raise ValueError(f"Invalid operator")

    if comparison_operator == "!=":
        return ~Q(**{f"{field_name}__{lookup}": condition_value})

    return Q(**{f"{field_name}__{lookup}": condition_value})


class ThresholdEvaluator:
    @staticmethod
    def evaluate(condition: dict, telemetry: Telemetry, **kwargs) -> bool:
        """Evaluate rule for 'threshold' type"""
        condition_value = _get_value(condition)
        comparison_operator = _get_comparison_operator(condition)
        duration_minutes = _get_duration_minutes(condition)
        telemetries_in_window = _get_telemetries_in_window(telemetry, duration_minutes)

        total_count = telemetries_in_window.count()
        if total_count == 0:
            logger.info("No telemetries in window")
            return False
        
        filter_q = _build_filter_condition(telemetry, comparison_operator, condition_value)

        matching_count = telemetries_in_window.aggregate(matches=Count(Case(When(filter_q, then=1))))['matches']

        logger.info(
            f"Threshold check: {matching_count} out of {total_count} events meet {comparison_operator} {condition_value}"
        )

        threshold_percentage = condition.get("threshold_percentage", DEFAULT_THRESHOLD_PERCENTAGE)
        match_ratio = matching_count / total_count

        return match_ratio >= threshold_percentage


class RateEvaluator:
    @staticmethod
    def evaluate(condition: dict, telemetry: Telemetry, **kwargs) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events for the same device_metric
        in the past `duration_minutes` meets or exceeds `count`.
        """
        count_required = condition.get("count")
        duration_minutes = _get_duration_minutes(condition)

        if count_required is None or duration_minutes is None:
            logger.error("Rate rule missing 'count' or 'duration_minutes'")
            return False

        event_count = _get_telemetries_in_window(telemetry, duration_minutes).count()

        logger.info(
            f"Rate rule check: {event_count} events in last {duration_minutes} min, need {count_required}"
        )

        return event_count >= count_required


class CompositeEvaluator:
    @staticmethod
    def evaluate(condition: dict, device_metric, telemetry: Telemetry) -> bool:
        """
        Evaluate composite rules combining multiple subconditions with AND/OR.
        """
        operator_type = condition.get("operator", "AND").upper()
        subconditions = condition.get("conditions", [])

        if not subconditions:
            logger.warning("Composite rule has no subconditions")
            return False

        results = []
        for i, subcondition in enumerate(subconditions):
            result = ConditionEvaluator.evaluate(subcondition, device_metric, telemetry)
            logger.info(f"Subcondition {i} (type={subcondition.get('type')}): {result}")
            results.append(result)

        logger.info(
            f"Composite {operator_type} evaluation: {results} -> {all(results) if operator_type == 'AND' else any(results)}"
        )

        if operator_type == "AND":
            return all(results)
        elif operator_type == "OR":
            return any(results)
        else:
            logger.warning(f"Unknown operator in composite rule: {operator_type}")
            return False


class ConditionEvaluator:
    _evaluators = {
        "threshold": ThresholdEvaluator.evaluate,
        "rate": RateEvaluator.evaluate,
        "composite": CompositeEvaluator.evaluate,
    }

    @staticmethod
    def register(rule_type: str, evaluator_callable):
        """Register a new evaluator for a custom rule type"""
        ConditionEvaluator._evaluators[rule_type] = evaluator_callable

    @staticmethod
    def evaluate(condition: dict, device_metric: Any, telemetry: Telemetry) -> bool:
        """Evaluate rule"""
        _validate_metric(device_metric, telemetry)
        rule_type = condition.get("type")
        if not rule_type:
            raise ValueError(f"Missing 'type' in rule.condition: {condition}")
        
        evaluator = ConditionEvaluator._evaluators.get(rule_type)
        # condition = rule.condition
        
        if evaluator is None:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False
        
        return evaluator(condition=condition, device_metric=device_metric, telemetry=telemetry)
