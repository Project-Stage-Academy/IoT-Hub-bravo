import logging
import operator
from datetime import timedelta

from apps.devices.models.telemetry import Telemetry
from apps.rules.models.rule import Rule

logger = logging.getLogger(__name__)

COMPARISON_OPERATORS = {
    "==": operator.eq, # or '=' for non tech user (?)
    "!=": operator.ne,
    ">":  operator.gt,
    "<":  operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}


class ConditionEvaluator:
    def __init__(self):
        pass
    
    @staticmethod
    def _evaluate_threshold(rule: Rule, telemetry: Telemetry):
        """eval rule for 'threshold' type"""
        condition = rule.condition
        condition_metric = rule.device_metric.metric.metric_type # condition.get("metric", None) # get metric from "condition" / None is default in get()
        duration_minutes = condition.get("duration_minutes")

        if condition_metric is None:
            logger.error("there is no metric in rule.condition")
            raise ValueError
        if condition_metric != telemetry.device_metric.metric.metric_type:
            logger.debug("rule metric does not match telemetry metric", extra={"condition_metric": condition_metric,
                                                                               "telemetry_metric": telemetry.device_metric.metric.metric_type,
                                                                               })
            return False  

        condition_value = condition.get("value", None) # get condition value / None is default in get() 
        if condition_value is None:
            logger.error("no value in condition")
            raise ValueError

        condition_operator = condition.get("operator", None) # get  operator from rule.condition / None is default in get()
        if condition_operator is None:
            logger.error("there is no operator in rule.condition")
            raise ValueError

        comparator = COMPARISON_OPERATORS.get(condition_operator, None) # get operator from comparison operators / None is default in get()
        if comparator is None:
            logger.error("there is no operator in comparison operators")
            raise ValueError

        # determine actual value
        if telemetry.value_numeric is not None:
            telemetry_value = telemetry.value_numeric
        elif telemetry.value_bool is not None:
            telemetry_value = telemetry.value_bool
        elif telemetry.value_str is not None:
            telemetry_value = telemetry.value_str
        else:
            logger.warning("no value in telemetry")
            return False  # telemetry without value 
        
        # time window
        duration_minutes = condition.get("duration_minutes", 5)  # default 5 min
        reference_time = telemetry.created_at
        window_start = reference_time - timedelta(minutes=duration_minutes)
    
        # all telemetries in window
        telemetries_in_window = Telemetry.objects.filter(
            device_metric=telemetry.device_metric,
            created_at__gte=window_start,
            created_at__lte=reference_time
        )

        total_count = telemetries_in_window.count()
        if total_count == 0:
            logger.info("No telemetries in window")
            return False

        # Count how many meet threshold
        matching_count = 0
        for t in telemetries_in_window:
            if t.value_numeric is not None:
                telemetry_value = t.value_numeric
            elif t.value_bool is not None:
                telemetry_value = t.value_bool
            elif t.value_str is not None:
                telemetry_value = t.value_str
            else:
                continue
        
            try:
                if comparator(telemetry_value, condition_value):
                    matching_count += 1
            except TypeError:
                logger.warning("type mismatch", extra={
                "condition_value": condition_value,
                "telemetry_value": telemetry_value,
                })
                continue
    
        logger.info(f"Threshold check: {matching_count} out of {telemetries_in_window.count()} events meet {condition_operator} {condition_value}")
    
        return matching_count == total_count  # True if eq to total count


    @staticmethod
    def _evaluate_rate(rule: Rule, telemetry: Telemetry) -> bool:
        """
        Rate evaluator:
        Checks if the count of Telemetry events for the same device_metric
        in the past `duration_minutes` meets or exceeds `count`.
        """
        condition = rule.condition
        count_required = condition.get("count")
        duration_minutes = condition.get("duration_minutes")

        if count_required is None or duration_minutes is None:
            logger.error("Rate rule missing 'count' or 'duration_minutes'")
            return False

        now = telemetry.created_at
        window_start = now - timedelta(minutes=duration_minutes)

        # Count telemetry for the same device_metric in the time window
        event_count = Telemetry.objects.filter(
            device_metric=telemetry.device_metric,
            created_at__gte=window_start
        ).count()

        logger.info(
            f"Rate rule check: {event_count} events in last {duration_minutes} min, need {count_required}"
        )

        return event_count >= count_required



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
            temp_rule = Rule(
                device_metric=rule.device_metric,
                condition=subcondition
            )
        
            # Use evaluate_condition for recursion (handles all types)
            result = ConditionEvaluator.evaluate_condition(temp_rule, telemetry)
            logger.info(f"Subcondition {i} (type={subcondition.get('type')}): {result}")
            results.append(result)

        logger.info(f"Composite {operator_type} evaluation: {results} -> {all(results) if operator_type == 'AND' else any(results)}")

        if operator_type == "AND":
            return all(results)
        elif operator_type == "OR":
            return any(results)
        else:
            logger.warning(f"Unknown operator in composite rule: {operator_type}")
            return False


    
    @staticmethod   
    def evaluate_condition(rule: Rule, telemetry: Telemetry) -> bool:
        """
        simple evaluator for rule
        return true if telemetry.value satifies rule.condition (?)
        condition = {"metric": "temperature", "operator": ">", "value": 100}
        """
        # add time
        condition = rule.condition
        rule_type = condition['type']

        if rule_type == 'threshold':
            return ConditionEvaluator._evaluate_threshold(rule, telemetry)
        
        elif rule_type == 'rate':
            return ConditionEvaluator._evaluate_rate(rule, telemetry)
        
        elif rule_type == 'composite':
            return ConditionEvaluator._evaluate_composite(rule, telemetry)
        
        else:
            logger.warning(f"Unknown condition type: {rule_type}")
            return False
            

        