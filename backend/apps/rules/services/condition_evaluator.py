import logging
from typing import Any, Callable
import operator

from apps.devices.models.device_metric import DeviceMetric
from apps.rules.utils.rule_engine_utils import TelemetryEvent


logger = logging.getLogger(__name__)

PYTHON_OPERATOR_MAP = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

DEFAULT_THRESHOLD_PERCENTAGE = 0.8  # default value to meet "threshold"


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


def _validate_metric(device_metric, telemetry: TelemetryEvent) -> None:
    """Checks that the rule has a metric and it matches the telemetry metric"""
    condition_metric = device_metric.metric.metric_type
    if condition_metric is None:
        logger.error("Rule must contain a 'metric' field")
        raise ValueError("Rule must contain a 'metric' field")
    if condition_metric != telemetry.metric_type:
        logger.debug(
            "Rule metric does not match telemetry metric",
            extra={
                "condition_metric": condition_metric,
                "telemetry_metric": telemetry.metric_type,
            },
        )
        raise ValueError("Rule metric must match a telemetry metric field")


def _validate_count(value: Any) -> int:
    """Ensure count is int > 0"""
    if isinstance(value, int) and value > 0:
        return value
    raise ValueError("Invalid count value")


class ThresholdEvaluator:
    @staticmethod
    def evaluate(condition: dict, telemetries_in_window: list, **kwargs) -> bool:
        """Evaluate rule for 'threshold' type"""
        condition_value = _get_value(condition)

        total_count = len(telemetries_in_window)
        if total_count == 0:
            logger.info("No telemetries in window")
            return False

        comparison_operator = _get_comparison_operator(condition)
        compare_func = PYTHON_OPERATOR_MAP.get(comparison_operator)
        if compare_func is None:
            logger.warning(f"Unsupported operator: {comparison_operator}")
            return False

        matching_count = sum(
            1 for t in telemetries_in_window if compare_func(t.value, condition_value)
        )

        logger.info(
            f"Threshold check: {matching_count} out of {total_count} events meet {comparison_operator} {condition_value}"
        )

        threshold_percentage = condition.get("threshold_percentage", DEFAULT_THRESHOLD_PERCENTAGE)
        match_ratio = matching_count / total_count

        return match_ratio >= threshold_percentage


class RateEvaluator:
    @staticmethod
    def evaluate(condition: dict, telemetries_in_window: list, **kwargs) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events for the same device_metric
        in the past `duration_minutes` meets or exceeds `count`.
        """
        count_required = _validate_count(condition.get("count"))

        if count_required is None:
            logger.error("Rate rule missing 'count'")
            return False

        event_count = len(telemetries_in_window)

        logger.info(
            f"Rate rule check: {event_count} events, need {count_required}"
        )

        return event_count >= count_required


class CompositeEvaluator:
    @staticmethod
    def evaluate(
        condition: dict,
        device_metric: DeviceMetric,
        telemetry: TelemetryEvent,
        telemetries_in_window: list,
    ) -> bool:
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
            result = ConditionEvaluator.evaluate(
                subcondition, device_metric, telemetry, telemetries_in_window
            )
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
    def register(rule_type: str, evaluator_callable: Callable):
        """Register a new evaluator for a custom rule type"""
        ConditionEvaluator._evaluators[rule_type] = evaluator_callable

    @staticmethod
    def evaluate(
        condition: dict,
        device_metric: DeviceMetric,
        telemetry: TelemetryEvent,
        telemetries_in_window: list,
    ) -> bool:
        """Evaluate rule"""
        try:
            _validate_metric(device_metric, telemetry)
        except ValueError as e:
            logger.warning(
                str(e),
                extra={
                    "rule_metric": device_metric.metric.metric_type,
                    "telemetry_metric": telemetry.metric_type,
                    "error": str(e),
                },
            )
            return False

        rule_type = condition.get("type")
        if not rule_type:
            raise ValueError(f"Missing 'type' in rule.condition: {condition}")

        evaluator = ConditionEvaluator._evaluators.get(rule_type)
        if evaluator is None:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False

        return evaluator(
            condition=condition,
            device_metric=device_metric,
            telemetry=telemetry,
            telemetries_in_window=telemetries_in_window,
        )
