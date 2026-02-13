import logging
import operator
from datetime import timedelta
from datetime import datetime
from typing import Tuple, Any

from apps.devices.models.telemetry import Telemetry
from apps.rules.models.rule import Rule

logger = logging.getLogger(__name__)

COMPARISON_OPERATORS = {
    "==": operator.eq,  # or '=' for non tech user (?)
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

DEFAULT_DURATION_MINUTES = 5  # default value for time window
DEFAULT_THRESHOLD_PERCENTAGE = 0.8  # default value to meet "threshold"


def _extract_telemetry_value(telemetry: Telemetry) -> float | bool | str | None:
    """Extract value from telemetry regardless of type"""
    if telemetry.value_numeric is not None:
        return telemetry.value_numeric
    elif telemetry.value_bool is not None:
        return telemetry.value_bool
    elif telemetry.value_str is not None:
        return telemetry.value_str
    return None


def _get_window(telemetry: Telemetry, minutes: int) -> Tuple[datetime, datetime]:
    """Returns the start and end of the time window for the given telemetry"""
    end = telemetry.created_at
    start = end - timedelta(minutes=minutes)
    return start, end


def _get_comparator(condition: str) -> operator:
    """Returns the comparison operator for the condition"""
    op = condition.get("operator")
    if not op:
        raise ValueError("No operator")
    comparator = COMPARISON_OPERATORS.get(op)
    if not comparator:
        raise ValueError("Invalid operator")
    return comparator


def _compare_safe(comparator: operator, telemetry_value: Any, condition_value: Any) -> bool:
    """Compare values"""
    return comparator(telemetry_value, condition_value)


def _get_value(condition: dict, key: str = 'value') -> Any:
    """Extract value from condition dictionary"""
    value = condition.get(key)
    if value is None:
        logger.error(f"Missing required field '{key}' in condition")
        raise ValueError(f"Missing required field '{key}' in condition")
    return value


def _validate_metric(rule: Rule, telemetry: Telemetry) -> bool:
    """Checks that the rule has a metric and it matches the telemetry metric"""
    condition_metric = rule.device_metric.metric.metric_type
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
        raise TypeError("Rule metric must match a telemetry metric field")


def _get_telemetries_in_window(telemetry: Telemetry, minutes: int):
    """Return all Telemetry objects for the same device_metric within the past `minutes` minutes"""
    start, end = _get_window(telemetry, minutes)
    return Telemetry.objects.filter(
        device_metric=telemetry.device_metric, created_at__gte=start, created_at__lte=end
    )


class ThresholdEvaluator:
    @staticmethod
    def evaluate(rule: Rule, telemetry: Telemetry) -> bool:
        """Evaluate rule for 'threshold' type"""
        _validate_metric(rule, telemetry)
        condition = rule.condition
        condition_value = _get_value(condition)
        comparator = _get_comparator(condition)
        duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)
        telemetries_in_window = _get_telemetries_in_window(telemetry, duration_minutes)

        total_count = telemetries_in_window.count()
        if total_count == 0:
            logger.info("No telemetries in window")
            return False

        matching_count = 0
        for t in telemetries_in_window:
            value = _extract_telemetry_value(t)
            if value is None:
                logger.warning(f"No value present in telemetry id={t.id}")
                continue

            if _compare_safe(comparator, value, condition_value):
                matching_count += 1

        logger.info(
            f"Threshold check: {matching_count} out of {total_count} events meet {comparator} {condition_value}"
        )

        threshold_percentage = condition.get("threshold_percentage", DEFAULT_THRESHOLD_PERCENTAGE)
        match_ratio = matching_count / total_count

        return match_ratio >= threshold_percentage


class RateEvaluator:
    @staticmethod
    def evaluate(rule: Rule, telemetry: Telemetry) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events for the same device_metric
        in the past `duration_minutes` meets or exceeds `count`.
        """
        condition = rule.condition
        count_required = condition.get("count")
        duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

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
    def evaluate(rule: Rule, telemetry: Telemetry) -> bool:
        """
        Evaluate composite rules combining multiple subconditions with AND/OR.
        """
        condition = rule.condition
        operator_type = condition.get("operator", "AND").upper()
        subconditions = condition.get("conditions", [])

        if not subconditions:
            logger.warning("Composite rule has no subconditions")
            return False

        results = []
        for i, subcondition in enumerate(subconditions):
            temp_rule = Rule(device_metric=rule.device_metric, condition=subcondition)
            result = ConditionEvaluator.evaluate(temp_rule, telemetry)
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
    def evaluate(rule: Rule, telemetry: Telemetry) -> bool:
        """Evaluate rule"""
        rule_type = rule.condition.get("type")
        if not rule_type:
            raise ValueError(f"Missing 'type' in rule.condition: {rule.condition}")
        evaluator = ConditionEvaluator._evaluators.get(rule_type)

        if evaluator is None:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False
        return evaluator(rule, telemetry)
