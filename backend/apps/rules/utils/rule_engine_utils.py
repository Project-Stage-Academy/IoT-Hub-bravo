from dataclasses import dataclass
from datetime import timedelta, datetime
from abc import ABC, abstractmethod
from typing import Tuple, List
import logging

from apps.devices.models.telemetry import Telemetry
from apps.devices.models.device_metric import DeviceMetric

logger = logging.getLogger(__name__)


MAX_REDIS_MINUTES = 60
# Threshold (in minutes) to decide whether to fetch telemetry from:
# - Redis (short-term)
# - PostgreSQL (long-term)

DEFAULT_DURATION_MINUTES = 5
# Default time window (in minutes) for telemetry queries in the rule engine


@dataclass
class TelemetryEvent:
    device_serial_id: str
    value: float
    timestamp: datetime
    device_metric_id: int


def _get_value_field(telemetry: Telemetry) -> str:
    """Get name (type) of the value telemtry field"""
    if telemetry.value_numeric is not None:
        return "value_numeric"
    if telemetry.value_bool is not None:
        return "value_bool"
    if telemetry.value_str is not None:
        return "value_str"

    raise ValueError("Telemetry has no value set")


###===========
### Mapping
###===========


def map_telemetry_model_to_event(telemetry: Telemetry) -> TelemetryEvent: # what to do with it
    """
    Map Telemetry model instance to TelemetryEvent dataclass.
    Chooses the correct value field based on _get_value_field.
    """
    value_field = _get_value_field(telemetry)
    value = getattr(telemetry, value_field)

    return TelemetryEvent(
        device_serial_id=telemetry.device_metric.device.serial_id,
        value=value,
        timestamp=telemetry.ts,
        device_metric_id=telemetry.device_metric.metric.metric_type, # probably remove this mapping  
    )


def map_telemetry_json_to_event(telemetry: dict) -> TelemetryEvent:
    return TelemetryEvent(
        device_serial_id=telemetry.get("device_serial_id"),
        value=telemetry.get("value"),
        timestamp=datetime.fromisoformat(telemetry.get("ts")),
        device_metric_id=telemetry.get("device_metric_id"),
    )


###=========================
### TELEMETRY REPOSITORIES
###=========================


class TelemetryRepository(ABC):
    """
    Abstract repository for retrieving telemetry data within a time window.

    This abstraction decouples the rule engine from the underlying
    storage implementation (e.g., PostgreSQL, Redis).
    """

    @abstractmethod
    def get_in_window(self, telemetry: TelemetryEvent, minutes: int) -> List[TelemetryEvent]:
        """
        Retrieve telemetry records for the same metric and device
        within the specified time window.

        :param telemetry: Incoming telemetry event used as reference.
        :param minutes: Size of the sliding time window in minutes.
        :return: Collection of telemetry records or values.
        """
        raise NotImplementedError


class PostgresTelemetryRepository(TelemetryRepository):
    def _get_window(self, telemetry: TelemetryEvent, minutes: int) -> Tuple[datetime, datetime]:
        """Returns the start and end of the time window for the given telemetry"""
        end = telemetry.timestamp
        start = end - timedelta(minutes=minutes)
        return start, end

    def get_in_window(self, telemetry: TelemetryEvent, minutes: int):
        """
        Fetch telemetry records from PostgreSQL within the given time window.

        :param telemetry: Incoming telemetry event.
        :param minutes: Window size in minutes.
        :return: List of Telemetry objects.
        """
        start, end = self._get_window(telemetry, minutes)

        device_metrics = DeviceMetric.objects.filter(device__serial_id=telemetry.device_serial_id)

        queryset = Telemetry.objects.filter(
            device_metric__in=device_metrics,
            ts__gte=start,
            ts__lte=end,
        )
        mapped_telemetries = [map_telemetry_model_to_event(telemetry) for telemetry in queryset]

        return mapped_telemetries


class RedisTelemetryRepository(TelemetryRepository):
    """
    Redis-based implementation of TelemetryRepository

    Assumes telemetry data is stored in Redis Sorted Sets,
    where:
        - key = telemetry:{device_serial_id}:{device_metric_id}
        - score = Unix timestamp
        - value = metric value (stringified)
    """

    def __init__(self, redis_client):
        """
        :param redis_client: Initialized Redis client instance
        """
        self.redis = redis_client

    def get_in_window(self, telemetry: TelemetryEvent, minutes: int):
        """
        Retrieve metric values from Redis within the specified time window

        :param telemetry: Incoming telemetry event.
        :param minutes: Window size in minutes.
        :return: List of float metric values within the window.
        """
        key = f"telemetry:{telemetry.device_serial_id}:{telemetry.device_metric_id}"

        end_ts = int(telemetry.timestamp.timestamp())
        start_ts = end_ts - minutes * 60

        items = self.redis.zrangebyscore(key, start_ts, end_ts, withscores=True)

        return [
            TelemetryEvent(
                device_serial_id=telemetry.device_serial_id,
                value=float(
                    value.split(":", 1)[1]
                ),  # take second because member = {timestam:value}
                timestamp=datetime.fromtimestamp(float(score)),
                device_metric_id=telemetry.device_metric_id,
            )
            for value, score in items
        ]


def choose_repository(duration_minutes: int, redis_client) -> TelemetryRepository:
    """Returns the repository for receiving telemetry: Redis for short intervals, PostgreSQL for long intervals (1hour>)"""
    if duration_minutes > MAX_REDIS_MINUTES:
        return PostgresTelemetryRepository()
    return RedisTelemetryRepository(redis_client)
