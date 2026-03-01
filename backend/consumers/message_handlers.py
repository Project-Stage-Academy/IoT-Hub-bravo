from typing import Any, Protocol
import logging
from django.conf import settings
import redis
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.rules.services.rule_processor import RuleProcessor


logger = logging.getLogger(__name__)
redis_client = redis.Redis(**settings.REDIS_CONFIG) #### CHANGE


class KafkaPayloadHandler(Protocol):
    def handle(self, payload: Any) -> None: ...


class CeleryPayloadHandler:
    def __init__(self, task):
        self._task = task

    def handle(self, payload: Any) -> None:
        self._task.delay(payload)


class RuleEvalHandler:
    def handle(self, payload):
        if isinstance(payload, list):
            for item in payload:
                self._handle_single(item)
        else:
            self._handle_single(payload)

    def _handle_single(self, item):
        telemetries = []
        ts_raw = item.get("ts") ### CHANGE
        ts = parse_datetime(ts_raw) ### CHANGE
        if timezone.is_naive(ts): ### CHANGE
            ts = timezone.make_aware(ts) ### CHANGE

        ### THATS PROBABLY BAD BUT SHOULD TEST
        for metric_type, value in item.get("metrics", {}).items():
            telemetries.append({
                "device_serial_id": item.get("device"),
                "metric_type": metric_type,
                "value": value,
                "ts": ts.isoformat() ### CHANGE
            })

        for telemetry in telemetries:
            key = f"telemetry:{telemetry['device_serial_id']}:{telemetry['metric_type']}"
            redis_client.zadd(key, {str(telemetry['value']): ts.timestamp()})

            RuleProcessor.run(telemetry)