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
    DEFAULT_DURATION_MINUTES,
    MAX_REDIS_MINUTES,
    TelemetryEvent,
    RedisTelemetryRepository,
    PostgresTelemetryRepository,
    TelemetryRepository,
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
    """Maps raw telemetry input (Telemetry model, dict, or TelemetryEvent) to TelemetryEvent"""

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
    """Fetches and caches active rules for a given telemetry device and metric"""

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
    """Fetches and caches telemetry window data, routing to Redis or PostgreSQL based on duration"""
    def __init__(self):
        self._cache = {}
        self._redis_repo = RedisTelemetryRepository(redis_client)
        self._pg_repo = PostgresTelemetryRepository()

    def choose_repository(self, duration_minutes: int) -> TelemetryRepository:
        if duration_minutes > MAX_REDIS_MINUTES:
            logger.debug("Using PostgreSQL repository", extra={"duration_minutes": duration_minutes})
            return self._pg_repo
        logger.debug("Using Redis repository", extra={"duration_minutes": duration_minutes})
        return self._redis_repo

    def get(self, telemetry: TelemetryEvent, duration_minutes: int):
        if duration_minutes not in self._cache:
            repository = self.choose_repository(duration_minutes)
            self._cache[duration_minutes] = repository.get_in_window(telemetry, duration_minutes)
            logger.debug("Window fetched", extra={"duration_minutes": duration_minutes, "records_count": len(self._cache[duration_minutes])})
        else:
            logger.debug("Window cache hit", extra={"duration_minutes": duration_minutes})    
        return self._cache[duration_minutes]

    def get(self, telemetry: TelemetryEvent, duration_minutes: int):
        if duration_minutes not in self._cache:
            repository = self.choose_repository(duration_minutes)
            self._cache[duration_minutes] = repository.get_in_window(
                telemetry, duration_minutes
            )
            logger.debug(
                "Window fetched",
                extra={
                    "duration_minutes": duration_minutes,
                    "records_count": len(self._cache[duration_minutes]),
                },
            )
        else:
            logger.debug(
                "Window cache hit", extra={"duration_minutes": duration_minutes}
            )
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

        mapped_telemetry = TelemetryMapper(telemetry=telemetry).map()
        logger.debug(
            "Telemetry mapped",
            extra={
                "device_serial_id": mapped_telemetry.device_serial_id,
                "device_metric_id": mapped_telemetry.device_metric_id,
            },
        )

        window_cache = WindowCache()

        rules = RuleCache(
            telemetry=mapped_telemetry
        ).get_rules()  # get rules from cache

        for rule in rules:
            condition = rule.condition
            rule_type = condition.get("type", "unknown")
            logger.debug(
                "Evaluating rule", extra={"rule_id": rule.id, "rule_type": rule_type}
            )

            rules_evaluated_total.labels(rule_type=rule_type).inc()
            duration_minutes = condition.get(
                "duration_minutes", DEFAULT_DURATION_MINUTES
            )

            cached_window = window_cache.get(mapped_telemetry, duration_minutes)

            if ConditionEvaluator.evaluate(condition, mapped_telemetry, cached_window):
                rules_triggered_total.labels(rule_type=rule_type).inc()
                logger.debug(
                    "Rule triggered - dispatching action",
                    extra={"rule_id": rule.id, "rule_type": rule_type},
                )
                Action.dispatch_action(rule, mapped_telemetry)
                results.append({"rule_id": rule.id, "triggered": True})
            else:
                logger.debug(
                    "Rule not triggered",
                    extra={"rule_id": rule.id, "rule_type": rule_type},
                )
                results.append({"rule_id": rule.id, "triggered": False})

        duration = time.perf_counter() - start_time
        rule_processing_seconds.observe(duration)
        logger.debug(
            "RuleProcessor finished",
            extra={
                "device_serial_id": mapped_telemetry.device_serial_id,
                "rules_count": len(rules),
                "duration_seconds": round(duration, 4),
            },
        )

        return {
            "telemetry": {
                "device_serial_id": mapped_telemetry.device_serial_id,
                "value": mapped_telemetry.value,
                "timestamp": mapped_telemetry.timestamp,
            },
            "results": results,
        }
