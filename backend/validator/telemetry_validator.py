from collections import defaultdict
from django.conf import settings
from apps.common.base_validator import BaseValidator
from typing import Any
import logging
from apps.devices.models import Device, DeviceMetric
from apps.common.checker.redis_checker import build_redis_checker
from utils.unit_aliases import REVERSE_UNIT_ALIASES
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class TelemetryBatchValidator(BaseValidator):
    def __init__(self, payload: list[dict[str, Any]]):
        super().__init__()
        self._validated_rows: list[dict[str, Any]] = []
        self._initial_data: list[dict[str, Any]] = payload
        self._validated_devices: set[str] = set()
        self._initial_device_metrics: dict[str, dict[str, dict[str, Any]]] = {}
        self._invalid_rows: list[dict[str, Any]] = []
        self._expired_rows: list[dict[str, Any]] = []

    @property
    def validated_rows(self):
        return self._validated_rows

    @property
    def invalid_rows(self):
        return self._invalid_rows

    @property
    def has_errors(self) -> bool:
        return bool(self._invalid_rows)

    @property
    def has_valid_data(self) -> bool:
        return bool(self._validated_rows)

    @property
    def expired_rows(self):
        return self._expired_rows

    def validate(self) -> None:
        """
        Validates payload and populates:
        - self._validated_rows
        - self._invalid_rows
        """
        self._validated_rows.clear()
        self._invalid_rows.clear()

        logger.info(
            "Starting telemetry payload validation for %d items",
            len(self._initial_data),
        )

        self._collect_devices_and_metrics()

        self._validate_payload()

        logger.info(
            "Validation completed. Valid: %d, Invalid: %d",
            len(self._validated_rows),
            len(self._invalid_rows),
        )

        logger.info("Starting expired data check")

        self._split_expired()

        logger.info(
            "Expired data checking completed. Valid after validation: %d, Expired: %d",
            len(self._validated_rows),
            len(self.expired_rows),
        )

        logger.info("Starting duplicate checking using Redis")

        self._validate_duplicates()

        logger.info(
            "Duplicate checking completed. Valid after deduplication: %d, Invalid due to duplicates: %d",
            len(self._validated_rows),
            len(self._invalid_rows),
        )

    def _collect_devices(self) -> None:
        """Fetch all devices from payload and populate _validated_devices"""
        device_serials = {
            item.get('device_serial_id')
            for item in self._initial_data
            if item.get("device_serial_id")
        }
        logger.debug("Collected %d device serials from payload", len(device_serials))

        self._validated_devices = set(
            Device.objects.filter(
                serial_id__in=device_serials,
                is_active=True,
            ).values_list("serial_id", flat=True)
        )

        logger.debug(
            "Collected %d active devices from DB",
            len(self._validated_devices),
        )

    def _collect_device_metrics(self) -> None:
        """Fetch all DeviceMetrics and Metrics in one query and build map"""
        if not self._validated_devices:
            logger.info("No validated devices found, skipping device metrics collection")
            return

        qs = DeviceMetric.objects.select_related("metric", "device").filter(
            device__serial_id__in=self._validated_devices
        )

        qs = list(qs)
        logger.debug("Fetched %d DeviceMetric records from DB", len(qs))

        device_metric_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for dm in qs:
            serial = dm.device.serial_id
            device_metric_map[serial][dm.metric.metric_type] = {
                "device_metric_id": dm.id,
                "data_type": dm.metric.data_type,
                "unit": dm.metric.unit,
            }

        self._initial_device_metrics = device_metric_map

        logger.debug(
            "Collected metrics for %d devices",
            len(self._initial_device_metrics),
        )

    def _collect_devices_and_metrics(self) -> None:
        """Wrapper: fetch devices + their metrics"""
        logger.info("Starting collection of devices and their metrics")
        self._collect_devices()
        self._collect_device_metrics()
        logger.info("Completed collection of devices and metrics")

    def _validate_payload(self) -> None:
        for index, item in enumerate(self._initial_data):
            serial = item.get("device_serial_id")
            metrics = item.get("metrics") or {}
            ts = item.get("ts")

            if serial not in self._validated_devices:
                self._add_invalid_record(
                    index=index,
                    serial=serial,
                    ts=ts,
                    metric=None,
                    value=None,
                    unit=None,
                    error="device_not_found",
                )
                continue

            device_metrics_map = self._initial_device_metrics.get(serial, {})

            for metric_name, payload in metrics.items():
                value = payload.get("value")
                unit = payload.get("unit")

                device_metric_data = device_metrics_map.get(metric_name)

                if not device_metric_data:
                    self._add_invalid_record(
                        index=index,
                        serial=serial,
                        ts=ts,
                        metric=metric_name,
                        value=value,
                        unit=unit,
                        error="metric_not_configured",
                    )
                    continue

                normalized_payload_unit = self._normalize_unit(unit)
                normalized_db_unit = self._normalize_unit(device_metric_data["unit"])

                if normalized_payload_unit != normalized_db_unit:
                    self._add_invalid_record(
                        index=index,
                        serial=serial,
                        ts=ts,
                        metric=metric_name,
                        value=value,
                        unit=unit,
                        error="unit_mismatch",
                    )
                    continue

                if not self._value_matches_data_type(value, device_metric_data["data_type"]):
                    self._add_invalid_record(
                        index=index,
                        serial=serial,
                        ts=ts,
                        metric=metric_name,
                        value=value,
                        unit=unit,
                        error="type_mismatch",
                    )

                    continue

                data_type = device_metric_data["data_type"]
                device_metric_id = device_metric_data["device_metric_id"]

                self._validated_rows.append(
                    {
                        "device_serial_id": serial,
                        "device_metric_id": device_metric_id,
                        "ts": ts,
                        "value_jsonb": {
                            't': data_type,
                            'v': value,
                        },
                    }
                )
                logger.debug(
                    "[%d] Validated metric: device=%s metric=%s value=%s unit=%s",
                    index,
                    serial,
                    metric_name,
                    value,
                    unit,
                )

    def _validate_duplicates(self) -> None:
        """
        Check for duplicate telemetry entries using Redis-based DuplicateChecker.
        Moves duplicates to _invalid_rows and keeps only unique validated rows.
        """
        checker = build_redis_checker()
        unique_valid_items = []

        for index, item in enumerate(self._validated_rows):
            dm_id = item.get("device_metric_id")
            ts = item.get("ts")
            serial = item.get("device_serial_id")
            value = item.get("value_jsonb", {}).get("v")

            result = checker.process(f"{dm_id},{ts}")
            if not result:
                self._add_invalid_record(
                    index=index,
                    serial=serial,
                    ts=ts,
                    metric=None,
                    value=value,
                    unit=None,
                    error="duplicate",
                )
                continue

            unique_valid_items.append(item)

        self._validated_rows = unique_valid_items

    def _value_matches_data_type(self, value: Any, data_type: str) -> bool:
        type_checkers = {
            "numeric": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "bool": lambda v: isinstance(v, bool),
            "str": lambda v: isinstance(v, str) and bool(v.strip()),
        }
        return type_checkers.get(data_type, lambda v: False)(value)

    def _normalize_unit(self, unit: str | None) -> str | None:
        if not unit:
            return None
        return REVERSE_UNIT_ALIASES.get(
            unit.strip().lower().replace("°", ""), unit.strip().lower()
        )

    def _split_expired(self) -> None:
        window_seconds = settings.TELEMETRY_MAX_AGE_SECONDS
        now = timezone.now()
        threshold = now - timedelta(seconds=window_seconds)

        fresh = []
        expired = []

        for item in self._validated_rows:
            ts = item.get("ts")

            if ts is None:
                fresh.append(item)
                continue

            if ts < threshold:
                expired.append(item)
            else:
                fresh.append(item)

        self._validated_rows = fresh
        self._expired_rows = expired

        logger.info(
            "Expiration check completed: fresh=%d, expired=%d",
            len(fresh),
            len(expired),
        )

    def _add_invalid_record(
        self,
        *,
        index: int | None,
        serial: str | None,
        ts: Any,
        metric: str | None,
        value: Any,
        unit: Any,
        error: str,
    ):
        self._invalid_rows.append(
            {
                "index": index,
                "device_serial_id": serial,
                "ts": ts,
                "metric": metric,
                "value": value,
                "unit": unit,
                "error": error,
            }
        )

        logger.warning(
            "[%d] Validation error device=%s metric=%s error=%s",
            index,
            serial,
            metric,
            error,
        )
