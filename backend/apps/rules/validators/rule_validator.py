from typing import Any
import json
from django.core.exceptions import ValidationError

from apps.rules.utils.rule_engine_utils import NotificationChannels, ActionTypes
from apps.rules.services.condition_evaluator import (
    ThresholdEvaluator,
    RateEvaluator,
    CompositeEvaluator,
    BooleanEvaluator,
    StringMatchEvaluator,
)

EVALUATOR_CLASSES = [
    ThresholdEvaluator,
    RateEvaluator,
    CompositeEvaluator,
    BooleanEvaluator,
    StringMatchEvaluator,
]

CONDITION_SCHEMAS = {cls.rule_type: cls.schema for cls in EVALUATOR_CLASSES}


def validate_condition(condition: dict[str, Any]) -> None:
    if isinstance(condition, str):
        try:
            condition = json.loads(condition)
        except (json.JSONDecodeError, TypeError):
            raise ValidationError("Condition must be valid JSON.")
    if not isinstance(condition, dict):
        raise ValidationError("Condition must be a dictionary")

    condition_type = condition.get("type")
    if condition_type not in CONDITION_SCHEMAS:
        raise ValidationError(f"Unsupported condition type: {condition_type}")

    schema = CONDITION_SCHEMAS[condition_type]

    for field, expected_type in schema.get("required", {}).items():
        if field not in condition:
            raise ValidationError(f"{condition_type} requires field '{field}'")
        if not isinstance(condition[field], expected_type):
            raise ValidationError(f"'{field}' must be {expected_type}")

    if "operators" in schema:
        if condition.get("operator") not in schema["operators"]:
            raise ValidationError(f"Invalid operator for {condition_type}")

    for field, validator in schema.get("validators", {}).items():
        if field in condition and not validator(condition[field]):
            raise ValidationError(f"Invalid value for {field}")

    if condition_type == "composite":
        for sub in condition["conditions"]:
            validate_condition(sub)


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
    if isinstance(action, str):
        try:
            action = json.loads(action)
        except (json.JSONDecodeError, TypeError):
            raise ValidationError("Action must be valid JSON.")

    if not isinstance(action, dict):
        raise ValidationError("Action must be a dictionary")

    if not action:
        raise ValidationError("Action cannot be empty")

    allowed = {a.value for a in ActionTypes}

    if not action.keys() & allowed:
        raise ValidationError(f"Action must contain at least one of: {', '.join(allowed)}")

    unknown = action.keys() - allowed
    if unknown:
        raise ValidationError(
            f"Unknown action type(s): {', '.join(unknown)}. " f"Allowed: {', '.join(allowed)}"
        )

    if ActionTypes.WEBHOOK.value in action:
        webhook = action.get(ActionTypes.WEBHOOK.value)
        if not isinstance(webhook, dict):
            raise ValidationError("Webhook must be object")
        if "url" not in webhook:
            raise ValidationError("Webhook requires 'url'")

        validate_action_enabled(webhook)

    if ActionTypes.NOTIFICATION.value in action:
        notification = action.get(ActionTypes.NOTIFICATION.value)
        if not isinstance(notification, dict):
            raise ValidationError("Notification must be object")
        if "channel" not in notification:
            raise ValidationError("Notification requires 'channel'")

        validate_action_enabled(notification)
        validate_action_notification_channel(notification)
