from typing import Any
from enum import Enum

from django.core.exceptions import ValidationError


class NotificationChannels(str, Enum):
    """Enumeration of available notification delivery channels"""

    EMAIL = "email"
    SMS = "sms"


def validate_condition(condition: dict[str, Any]) -> None:
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

    condition_type = condition.get("type")
    if not isinstance(condition_type, str):
        raise ValidationError("Condition 'type' must be string")

    if condition_type == "threshold":
        if "operator" not in condition:
            raise ValidationError("Threshold condition requires 'operator'")
        if condition.get("operator") not in [">", "<", ">=", "<=", "==", "!="]:  # change?
            raise ValidationError("Invalid threshold operator")
        if "value" not in condition:
            raise ValidationError("Threshold condition requires 'value'")
        if not isinstance(condition.get("value"), (int, float)):
            raise ValidationError("Condition 'value' must be number")

    elif condition_type == "rate":
        if "duration_minutes" not in condition:
            raise ValidationError("Rate condition requires 'duration_minutes'")
        if "count" not in condition:
            raise ValidationError("Rate condition requires 'count'")

        if condition.get("duration_minutes") <= 0:
            raise ValidationError("duration_minutes must be positive")
        if condition.get("count") <= 0:
            raise ValidationError("count must be positive")

        if not isinstance(condition.get("duration_minutes"), int):
            raise ValidationError("duration_minutes must be int")
        if not isinstance(condition.get("count"), int):
            raise ValidationError("count must be int")

    elif condition_type == "composite":
        if "conditions" not in condition:
            raise ValidationError("Composite condition requires 'conditions'")
        if "operator" not in condition:
            raise ValidationError("Composite condition requires 'operator'")
        if condition.get("operator") not in ["AND", "OR"]:
            raise ValidationError("Composite operator must be AND or OR")

        conds_to_val = condition["conditions"]
        if not isinstance(conds_to_val, list):
            raise ValidationError("'conditions' must be a list")
        if not conds_to_val:
            raise ValidationError("'conditions' must not be empty")
        for cond_to_val in conds_to_val:
            if not isinstance(cond_to_val, dict):
                raise ValidationError("Each composite condition must be a dictionary")
            validate_condition(cond_to_val)

    else:
        raise ValidationError(f"Unsupported condition type: {condition_type}")


def validate_action_enabled(action_type: dict) -> None:
    """Validation for field 'enabled' in action"""
    if not isinstance(action_type.get("enabled"), bool):
        raise ValidationError("Action 'enabled' must be bool")


def validate_action_notification_channel(notification: dict) -> None:
    try:
        NotificationChannels(notification.get("channel"))
    except ValueError:
        raise ValidationError("Unsupported notification channel")


def validate_action(action: dict[str, Any]) -> None:
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

    if "webhook" in action:  # maybe better remade to models
        webhook = action.get("webhook")

        if not isinstance(webhook, dict):
            raise ValidationError("Webhook must be object")

        if "url" not in webhook:
            raise ValidationError("Webhook requires 'url'")

        validate_action_enabled(webhook)

    if "notification" in action:
        notification = action.get("notification")

        if not isinstance(notification, dict):
            raise ValidationError("Notification must be object")

        if "channel" not in notification:
            raise ValidationError("Notification requires 'channel'")

        validate_action_enabled(notification)
        validate_action_notification_channel(notification)
