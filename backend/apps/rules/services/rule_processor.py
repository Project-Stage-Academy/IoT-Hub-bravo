import logging
import time
from django.core.cache import caches
from django.conf import settings

from apps.rules.models.rule import Rule
from apps.devices.models.telemetry import Telemetry
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


class TelemetryMapper:
    """"""
    def __init__(self, telemetry: Telemetry | dict | TelemetryEvent):
        self.telemetry = telemetry

    def map(self) -> TelemetryEvent:
        if isinstance(self.telemetry, Telemetry):
            return map_telemetry_model_to_event(self.telemetry)
        elif isinstance(self.telemetry, dict):
            return map_telemetry_json_to_event(self.telemetry)
        elif isinstance(self.telemetry, TelemetryEvent):
            return self.telemetry
        raise TypeError(f"Unsupported telemetry type: {type(self.telemetry)}")


class RuleCache:
    """"""
    def __init__(self, telemetry: TelemetryEvent):
        self.telemetry = telemetry

    def get_rules(self) -> list[Rule]:
        cache = caches["rules"]
        cache_key = f"{self.telemetry.device_serial_id}:{self.telemetry.device_metric_id}"
        
        rules = cache.get(cache_key)
        if rules is None:
            rules = list(
                Rule.objects.filter(
                    is_active=True,
                    device_metric_id=self.telemetry.device_metric_id,
                )
            )
            cache.set(cache_key, rules, timeout=settings.RULES_CACHE_TTL)
        return rules


class WindowCache:
    """"""
    def __init__(self):
        self._cache = {}

    def get(self, telemetry: TelemetryEvent, duration_minutes: int):
        if duration_minutes not in self._cache:
            repository = choose_repository(duration_minutes, redis_client)
            self._cache[duration_minutes] = repository.get_in_window(telemetry, duration_minutes)
        return self._cache[duration_minutes]



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

        mapped_telemetry = TelemetryMapper(telemetry=telemetry).map()

        rules = RuleCache(telemetry=mapped_telemetry).get_rules() # get rules from cache

        for rule in rules:
            condition = rule.condition
            rule_type = condition.get('type', 'unknown')

            rules_evaluated_total.labels(rule_type=rule_type).inc()
            duration_minutes = condition.get("duration_minutes", DEFAULT_DURATION_MINUTES)

            if duration_minutes not in window_cache:
                repository = choose_repository(duration_minutes, redis_client)
                window_cache[duration_minutes] = repository.get_in_window(
                    mapped_telemetry, duration_minutes
                )

            cached_window = window_cache[duration_minutes]

            if ConditionEvaluator.evaluate(condition, mapped_telemetry, cached_window):
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
