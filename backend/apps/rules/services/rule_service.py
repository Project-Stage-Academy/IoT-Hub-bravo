import logging
from typing import Dict, Any
from enum import Enum
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from apps.rules.models.rule import Rule


logger = logging.getLogger(__name__)


class ConditionTypes(str, Enum):
    """"""
    EMAIL = "email"
    SMS = "sms"
    # IN_APP = "in_app" # for future


def _validate_condition(condition: Dict[str, Any]) -> None:
    """
    Validate condition JSON.
    Example:
    {
        "type": "threshold",
        "operator": ">",
        "value": 50
    }
    """
    if not isinstance(condition, dict):
        raise ValidationError("Condition must be a dictionary")

    required_fields = ["type"]

    for field in required_fields:
        if field not in condition:
            raise ValidationError(f"Condition field '{field}' is required")

    condition_type = condition.get("type") # change with more validation i mean if there is wrong condition


    if condition_type == "threshold": # hardcoded ?
        if "operator" not in condition:
            raise ValidationError("Threshold condition requires 'operator'")
        if "value" not in condition:
            raise ValidationError("Threshold condition requires 'value'")
        if not isinstance(condition.get("value"), (int, float)):
            raise ValidationError("Condition 'value' must be number")

    elif condition_type == "rate": # hardcoded ?
        if "duration_minutes" not in condition:
            raise ValidationError("Rate condition requires 'duration_minutes'")
        if "count" not in condition:
            raise ValidationError("Rate condition requires 'count'")

        if not isinstance(condition.get("duration_minutes"), int):
            raise ValidationError("duration_minutes must be int")
        if not isinstance(condition.get("count"), int):
            raise ValidationError("count must be int")

    # add composite
    elif condition_type == "composite": # hardcoded ?
        if "duration_minutes" not in condition:
            raise ValidationError("Rate condition requires 'duration_minutes'")
        if "count" not in condition:
            raise ValidationError("Rate condition requires 'count'")

        if not isinstance(condition.get("duration_minutes"), int):
            raise ValidationError("duration_minutes must be int")
        if not isinstance(condition.get("count"), int):
            raise ValidationError("count must be int")

    else:
        raise ValidationError(f"Unsupported condition type: {condition_type}")

### ========
### action validation
### ========
class NotificationChannels(str, Enum):
    """Availeble channels for notification"""
    EMAIL = "email"
    SMS = "sms"
    # IN_APP = "in_app"


def _validate_action_enabled(action_type: dict) -> None:
    """Validation for field 'enabled' in action"""
    if not isinstance(action_type.get("enabled"), bool):
        raise ValidationError("Action 'enabled' must be bool")


def _validate_action_notification_channel(notification: dict) -> None:
    try:
        NotificationChannels(notification.get("channel"))
    except ValueError:
        raise ValidationError("Unsupported notification channel")


def _validate_action(action: dict[str, Any]) -> None:
    """
    Validate action JSON.
    Example:
    {'webhook': {
             'url': 'https://webhook.site/a6bf3275-595d-42fd-b759-c42d74ce8c9e',    
             'enabled': true # is there any purposes in it?
                }, 
    'notification': {
        'channel': 'email', # only one?
        'enabled': true,  # is there any purposes in it?
        'message': 'High temperature in {device_name}: {value}°C'
                }
    }   
    """
    if not isinstance(action, dict):
        raise ValidationError("Action must be a dictionary")

    if not action:
        raise ValidationError("Action cannot be empty")

    if "webhook" in action: # maybe better remade to models 
        webhook = action.get("webhook")
        
        if not isinstance(webhook, dict):
            raise ValidationError("Webhook must be object")
        
        if "url" not in webhook:
            raise ValidationError("Webhook requires 'url'")
        
        _validate_action_enabled(webhook)

    if "notification" in action:
        notification = action.get("notification")
        
        if not isinstance(notification, dict):
            raise ValidationError("Notification must be object")
        
        if "channel" not in notification:
            raise ValidationError("Notification requires 'channel'")

        _validate_action_enabled(notification)
        _validate_action_notification_channel(notification)


# ==============================
# CREATE
# ==============================

# @transaction.atomic
def rule_create(rule_data: dict[str, Any]) -> Rule:
    logger.debug("Creating rule with data: %s", rule_data)

    _validate_condition(rule_data.get("condition"))
    _validate_action(rule_data.get("action"))

    rule = Rule.objects.create(
        name=rule_data.get("name"),
        device_metric_id=rule_data.get("device_metric"),
        condition=rule_data.get("condition"),
        action=rule_data.get("action"),
        is_active=rule_data.get("is_active", True),
    )

    return rule


# ==============================
# PUT (FULL UPDATE)
# ==============================

# @transaction.atomic
def rule_put(rule_id: int, rule_data: dict[str, Any]) -> Rule:
    logger.debug("Full update rule id=%s", rule_id)

    rule = Rule.objects.get(id=rule_id)

    _validate_condition(rule_data["condition"])
    _validate_action(rule_data["action"])

    rule.name = rule_data.get("name")
    rule.device_metric_id = rule_data.get("device_metric")
    rule.condition = rule_data.get("condition")
    rule.action = rule_data.get("action")
    rule.is_active = rule_data.get("is_active", True)

    rule.save()

    return rule


# ==============================
# PATCH (PARTIAL UPDATE)
# ==============================

# @transaction.atomic
def rule_patch(rule_id: int, rule_data: dict[str, Any]) -> Rule:
    logger.debug("Partial update rule id=%s", rule_id)

    rule = Rule.objects.get(id=rule_id)

    if "condition" in rule_data:
        _validate_condition(rule_data.get("condition"))
        rule.condition = rule_data.get("condition")

    if "action" in rule_data:
        _validate_action(rule_data.get("action"))
        rule.action = rule_data.get("action")

    if "name" in rule_data:
        rule.name = rule_data.get("name")

    if "device_metric_id" in rule_data:
        rule.device_metric_id = rule_data.get("device_metric")

    if "is_active" in rule_data:
        rule.is_active = rule_data.get("is_active")

    rule.save()

    return rule


# ======
# DELETE
# ++++++

def rule_delete(rule_id: int) -> None:
    logger.debug("Deleting rule id=%s", rule_id)

    try:
        rule = Rule.objects.get(id=rule_id)
        rule.delete()
    except ObjectDoesNotExist:
        logger.warning("Rule id=%s not found for deletion", rule_id)    
