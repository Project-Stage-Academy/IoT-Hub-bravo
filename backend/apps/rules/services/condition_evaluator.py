import logging
import operator
from datetime import timedelta

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

DEFAULT_DURATION_MINUTES = 5


def _extract_telemetry_value(telemetry: Telemetry):
        """Extract value from telemetry regardless of type"""
        if telemetry.value_numeric is not None:
            return telemetry.value_numeric
        elif telemetry.value_bool is not None:
            return telemetry.value_bool
        elif telemetry.value_str is not None:
            return telemetry.value_str
        return None


class ThresholdEvaluator:
    @staticmethod
    def _evaluate_threshold(rule: Rule, telemetry: Telemetry):
        """eval rule for 'threshold' type"""
        condition = rule.condition
        condition_metric = (
            rule.device_metric.metric.metric_type
        )

        if condition_metric is None:
            logger.error("Rule must contain a 'metric' field")
            raise ValueError("Rule must contain a 'metric' field")
        if condition_metric != telemetry.device_metric.metric.metric_type:
            logger.debug(
                "rule metric does not match telemetry metric",
                extra={
                    "condition_metric": condition_metric,
                    "telemetry_metric": telemetry.device_metric.metric.metric_type,
                },
            )
            return False

        condition_value = condition.get(
            "value", None
        )
        if condition_value is None:
            logger.error("Rule condition does not contain a value")
            raise ValueError("Rule condition does not contain a value")

        condition_operator = condition.get(
            "operator", None
        ) 

        if condition_operator is None:
            logger.error("No operator is defined in rule.condition")
            raise ValueError("No operator is defined in rule.condition")

        comparator = COMPARISON_OPERATORS.get(
            condition_operator, None
        )  # get operator from comparison operators / None is default in get()
        if comparator is None:
            logger.error("No valid comparison operator specified")
            raise ValueError("No valid comparison operator specified")

        # if telemetry doesnt has a value but we have window sooo what - ?????????
        telemetry_value = _extract_telemetry_value(telemetry)
        if telemetry_value is None:
            logger.warning("No value present in telemetry")
            return False
        
        # time window
        duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)
        reference_time = telemetry.created_at
        window_start = reference_time - timedelta(minutes=duration_minutes)

        # all telemetries in window
        telemetries_in_window = Telemetry.objects.filter(
            device_metric=telemetry.device_metric,
            created_at__gte=window_start,
            created_at__lte=reference_time,
        )

        total_count = telemetries_in_window.count()
        if total_count == 0:
            logger.info("No telemetries in window")
            return False

        # Count how many meet threshold
        matching_count = 0
        for t in telemetries_in_window:
            telemetry_value = _extract_telemetry_value(t)
            if telemetry_value is None:
                logger.warning(f"No value present in telemetry telemtry_id: {t.id}")
                continue

            try:
                if comparator(telemetry_value, condition_value):
                    matching_count += 1
            except TypeError:
                logger.warning(
                    "type mismatch",
                    extra={
                        "condition_value": condition_value,
                        "telemetry_value": telemetry_value,
                    },
                )
                continue

        logger.info(
            f"Threshold check: {matching_count} out of {telemetries_in_window.count()} events meet {condition_operator} {condition_value}"
        )

        return matching_count == total_count  # True if eq to total count # ADD SOME THRESHOLD NOT ONE FOR ALL


class RateEvaluator:
    @staticmethod
    def _evaluate_rate(rule: Rule, telemetry: Telemetry) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events for the same device_metric
        in the past `duration_minutes` meets or exceeds `count`.
        """
        condition = rule.condition
        count_required = condition.get("count") # is there should be a default count???
        duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

        if count_required is None or duration_minutes is None:
            logger.error("Rate rule missing 'count' or 'duration_minutes'")
            return False

        now = telemetry.created_at
        window_start = now - timedelta(minutes=duration_minutes)

        # Count telemetry for the same device_metric in the time window
        event_count = Telemetry.objects.filter(
            device_metric=telemetry.device_metric, created_at__gte=window_start
        ).count()

        logger.info(
            f"Rate rule check: {event_count} events in last {duration_minutes} min, need {count_required}"
        )

        return event_count >= count_required


class CompositeEvaluator:
    @staticmethod
    def _evaluate_composite(rule: Rule, telemetry: Telemetry) -> bool:
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
            # Create temp rule for subcondition
            temp_rule = Rule(device_metric=rule.device_metric, condition=subcondition)

            # Use evaluate_condition for recursion (handles all types)
            result = ConditionEvaluator.evaluate_condition(temp_rule, telemetry)
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
    @staticmethod
    def evaluate_condition(rule: Rule, telemetry: Telemetry) -> bool:
        """
        simple evaluator for rule
        return true if telemetry.value satifies rule.condition (?)
        condition = {"metric": "temperature", "operator": ">", "value": 100}
        """
        # add time
        condition = rule.condition
        rule_type = condition.get('type')

        if rule_type == 'threshold':
            return ConditionEvaluator._evaluate_threshold(rule, telemetry)

        elif rule_type == 'rate':
            return ConditionEvaluator._evaluate_rate(rule, telemetry)

        elif rule_type == 'composite':
            return ConditionEvaluator._evaluate_composite(rule, telemetry)

        else:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False
