import logging
from typing import Any, Callable, List, Optional
import operator
from dataclasses import dataclass

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
    if key not in condition:
        logger.error(f"Missing required field '{key}' in condition")
        raise ValueError(f"Missing required field '{key}' in condition")
    return condition[key]


def _validate_count(value: Any) -> int:
    """Ensure count is int > 0"""
    if isinstance(value, int) and value > 0:
        return value
    raise ValueError("Invalid count value")


@dataclass
class EvaluationContext:
    telemetry: Optional[TelemetryEvent]
    telemetries_in_window: List[TelemetryEvent]


class ThresholdEvaluator:
    rule_type = "threshold"
    schema = {
        "required": {"operator": str, "value": (int, float)},
        "operators": [">", "<", ">=", "<=", "==", "!="],
    }

    @staticmethod
    def evaluate(condition: dict, context: EvaluationContext, **kwargs) -> bool:
        """Evaluate rule for 'threshold' type"""
        condition_value = _get_value(condition)
        telemetries_in_window = context.telemetries_in_window

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
    rule_type = "rate"
    schema = { 
        "required": {"count": int},
        "validators": {
            "count": lambda x: x > 0,
        }
    }    
    
    @staticmethod
    def evaluate(condition: dict, context, **kwargs) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events
        in the past `duration_minutes` meets or exceeds `count`.
        """
        try: 
            count_required = _validate_count(condition.get("count"))
        except ValueError as e:
            return False
        
        telemetries_in_window = context.telemetries_in_window
        event_count = len(telemetries_in_window)
        logger.debug(f"Rate rule check: {event_count} events, need {count_required}")

        return event_count >= count_required


class BooleanEvaluator:
    rule_type = "boolean"
    schema = {
        "required": {"value": bool},
        "operators": ["==", "!="],
    }
    
    @staticmethod
    def evaluate(condition: dict, context: EvaluationContext, **kwargs) -> bool:
        try:
            expected = _get_value(condition)
        except ValueError:
            return False
 
        op = condition.get("operator", "==")
        compare_func = PYTHON_OPERATOR_MAP.get(op)
        if compare_func is None:
            logger.warning(f"BooleanEvaluator: unsupported operator '{op}'")
            return False
 
        actual = context.telemetry.value if context.telemetry else None
        return compare_func(actual, expected)


class StringMatchEvaluator:
    rule_type = "string_match"
    schema = {
        "required": {"value": str},
        "operators": ["==", "!=", "in"],
    }
    
    @staticmethod
    def evaluate(condition: dict, context: EvaluationContext, **kwargs) -> bool:
        try:
            expected = _get_value(condition)
        except ValueError:
            return False
 
        op = condition.get("operator", "==")
        actual = context.telemetry.value if context.telemetry else None
 
        if op == "in":
            return str(actual) in str(expected)
        compare_func = PYTHON_OPERATOR_MAP.get(op)
        if compare_func is None:
            logger.warning(f"StringMatchEvaluator: unsupported operator '{op}'")
            return False
        return compare_func(str(actual), str(expected))


class CompositeEvaluator:
    rule_type = "composite"
    schema = {
        "required": {"conditions": list, "operator": str},
        "operators": ["AND", "OR"],
    }

    @staticmethod
    def evaluate(
        condition: dict,
        context: EvaluationContext,
        **kwargs
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
            result = ConditionEvaluator.evaluate(subcondition, context)
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
        "boolean": BooleanEvaluator.evaluate,
        "string_match": StringMatchEvaluator.evaluate
    }

    @staticmethod
    def register(rule_type: str, evaluator_callable: Callable):
        """Register a new evaluator for a custom rule type"""
        ConditionEvaluator._evaluators[rule_type] = evaluator_callable

    @staticmethod
    def evaluate(
        condition: dict,
        context: EvaluationContext
    ) -> bool:
        """Evaluate rule"""

        rule_type = condition.get("type")
        if not rule_type:
            raise ValueError(f"Missing 'type' in rule.condition: {condition}")

        evaluator = ConditionEvaluator._evaluators.get(rule_type)
        if evaluator is None:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False

        return evaluator(
            condition=condition,
            context=context
        )
