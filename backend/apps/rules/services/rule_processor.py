import logging
import time
from django.core.cache import caches
from django.conf import settings
from django.db.models.signals import post_save, post_delete

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device_metric import DeviceMetric
from apps.rules.services.action import Action
from apps.rules.services.condition_evaluator import ConditionEvaluator
from apps.rules.utils.rule_engine_utils import (
    map_telemetry_json_to_event,
    map_telemetry_model_to_event,
    choose_repository,
    DEFAULT_DURATION_MINUTES,
    TelemetryEvent,
)
from apps.common.redis_client import get_redis_client
from apps.common.metrics import (
    rules_evaluated_total,
    rules_triggered_total,
    rule_processing_seconds,
)

logger = logging.getLogger(__name__)
redis_client = get_redis_client()


class RuleProcessor:
    """
    Processes active rules for a given telemetry and triggers actions if conditions match.
    Collects Prometheus metrics for monitoring rule evaluation performance.
    """

    @staticmethod
    def run(telemetry: Telemetry | dict) -> dict:
        """
        Returns a dict with triggered rules for this telemetry.
        Tracks: rules evaluated, rules triggered, processing time.
        """
        start_time = time.perf_counter()
        results = []
        window_cache = {}
        cache_rule = caches["rules"]

        if isinstance(telemetry, Telemetry):
            mapped_telemetry = map_telemetry_model_to_event(telemetry)
        elif isinstance(telemetry, dict):
            mapped_telemetry = map_telemetry_json_to_event(telemetry)
        elif isinstance(telemetry, TelemetryEvent):
            mapped_telemetry = telemetry
        else:
            raise TypeError(f"Unsupported telemetry type: {type(telemetry)}")    

        cache_key = f"{mapped_telemetry.device_serial_id}:{mapped_telemetry.metric_type}"

        rules = cache_rule.get_or_set(
            cache_key,
            lambda: list(
                Rule.objects.filter(
                    is_active=True, device_metric__in=DeviceMetric.objects.filter(
                        device__serial_id=mapped_telemetry.device_serial_id,
                        metric__metric_type=mapped_telemetry.metric_type,
                    )
                ).select_related('device_metric__metric')
            ),
            timeout=settings.RULES_CACHE_TTL
        )

        for rule in rules:
            condition = rule.condition
            device_metric = rule.device_metric
            rule_type = condition.get('type', 'unknown')

            rules_evaluated_total.labels(rule_type=rule_type).inc()
            duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

            if duration_minutes not in window_cache:
                repository = choose_repository(duration_minutes, redis_client)
                window_cache[duration_minutes] = repository.get_in_window(
                    mapped_telemetry, duration_minutes
                )

            cached_window = window_cache[duration_minutes]

            if ConditionEvaluator.evaluate(
                condition, device_metric, mapped_telemetry, cached_window
            ):
                rules_triggered_total.labels(rule_type=rule_type).inc()
                Action.dispatch_action(rule, mapped_telemetry)
                results.append({"rule_id": rule.id, "triggered": True})
            else:
                results.append({"rule_id": rule.id, "triggered": False})

        rule_processing_seconds.observe(time.perf_counter() - start_time)

        return {
            "telemetry": {
                "device_serial_id": mapped_telemetry.device_serial_id,
                "value": mapped_telemetry.value,
                "timestamp": mapped_telemetry.timestamp,
            },
            "results": results,
        }
