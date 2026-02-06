import logging
import operator
# add time for eval

from apps.devices.models.telemetry import Telemetry

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
    def evaluate_condition(condition: dict, telemetry: Telemetry) -> bool:
        """
        simple evaluator for rule
        return true if telemetry.value satifies rule.condition (?)
        condition = {"metric": "temperature", "operator": ">", "value": 100}
        """
        # add time

        condition_metric = condition.get("metric", None) # get metric from "condition" / None is default in get()
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
        
        #evaluation on condition
        try:
            return comparator(telemetry_value, condition_value)
        except TypeError:
            logger.warning("there is something not right....", extra = {"condition_value": condition_value, 
                                                                      "condition_operator": condition_operator, 
                                                                      "condition_metric": condition_metric,
                                                                      "telemetry_value": telemetry_value,
                                                                      "telemetry_metric": telemetry.device_metric.metric.metric_type,
                                                                     })
            return False