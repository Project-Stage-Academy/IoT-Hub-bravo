import logging
from typing import Any
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.rules.models.rule import Rule
from apps.rules.validators.rule_validator import validate_condition, validate_action


logger = logging.getLogger(__name__)


@transaction.atomic
def rule_create(rule_data: dict[str, Any]) -> Rule:
    logger.debug("Creating rule with data: %s", rule_data)

    validate_condition(rule_data.get("condition"))
    validate_action(rule_data.get("action"))

    rule = Rule.objects.create(
        name=rule_data.get("name"),
        device_metric_id=rule_data.get("device_metric_id"),
        condition=rule_data.get("condition"),
        action=rule_data.get("action"),
        is_active=rule_data.get("is_active", True),
    )

    return rule


def rule_put(rule_id: int, rule_data: dict[str, Any]) -> Rule:
    logger.debug("Full update rule id=%s", rule_id)
    # for field in required_fields:
    #     if field not in rule_data:
    #         raise ValidationError(f"{field} is required for PUT")

    rule = Rule.objects.get(id=rule_id)

    condition = rule_data.get("condition")
    validate_condition(condition)
    action = rule_data.get("action")
    validate_action(action)

    rule.name = rule_data.get("name")
    rule.device_metric_id = rule_data.get("device_metric_id")
    rule.condition = condition
    rule.action = action
    rule.is_active = rule_data.get("is_active", True)

    rule.save()

    return rule


def rule_patch(rule_id: int, rule_data: dict[str, Any]) -> Rule:
    logger.debug("Partial update rule id=%s", rule_id)

    rule = Rule.objects.get(id=rule_id)

    if "condition" in rule_data:
        validate_condition(rule_data.get("condition"))
        rule.condition = rule_data.get("condition")

    if "action" in rule_data:
        validate_action(rule_data.get("action"))
        rule.action = rule_data.get("action")

    if "name" in rule_data:
        rule.name = rule_data.get("name")

    if "device_metric_id" in rule_data:
        rule.device_metric_id = rule_data.get("device_metric_id")

    if "is_active" in rule_data:
        rule.is_active = rule_data.get("is_active")

    rule.save()

    return rule


def rule_delete(rule_id: int) -> None:
    logger.debug("Deleting rule id=%s", rule_id)

    try:
        rule = Rule.objects.get(id=rule_id)
        rule.delete()
    except ObjectDoesNotExist:
        logger.warning("Rule id=%s not found for deletion", rule_id)
