from .base_validator import BaseValidator
from typing import Any
import logging
from apps.devices.models import Device, DeviceMetric
from utils.unit_aliases import REVERSE_UNIT_ALIASES

logger = logging.getLogger(__name__)


class TelemetryBatchValidator(BaseValidator):
    def __init__(self, payload: list[dict[str, Any]]):
        super().__init__()
        self._validated_rows: list[dict[str, Any]] = []
        self._initial_data: list[dict[str, Any]] = payload
        self._validated_devices: set[str] = set()
        self._initial_device_metrics: dict[str, dict[str, dict[str, Any]]] = {}

    @property
    def validated_devices(self):
        return self._validated_devices

    @property
    def initial_device_metrics(self):
        return self._initial_device_metrics

    @property
    def validated_rows(self):
        return self._validated_rows

    def is_valid(self) -> bool:
        self._errors.clear()
        self._validated_rows = []

        logger.info("Starting telemetry payload validation for %d items", len(self._initial_data))
        self._collect_devices_and_metrics()
        self._validate()

        logger.info("Validation completed successfully for %d items", len(self._validated_rows))

        return not self._errors

    def _collect_devices(self) -> None:
        """Fetch all devices from payload and populate _validated_devices"""
        device_serials = {
            item['device_serial_id'] for item in self._initial_data if item.get("device_serial_id")
        }

        logger.debug("Collected %d device serials from payload", len(device_serials))

        active_serials = set(
            Device.objects.filter(serial_id__in=device_serials, is_active=True).values_list(
                "serial_id", flat=True
            )
        )

        logger.debug("Found %d active devices in DB", len(active_serials))

        missing = device_serials - active_serials
        if missing:
            self._errors.append(
                {"index": None, "field": "device", "error": f"Missing serials: {missing}"}
            )
            logger.warning("Missing devices in DB: %s", missing)

        self._validated_devices = active_serials
        logger.info("Validated devices set updated with %d devices", len(self._validated_devices))

    def _collect_device_metrics(self) -> None:
        """Fetch all DeviceMetrics and Metrics in one query and build map"""
        if not self._validated_devices:
            logger.info("No validated devices found, skipping device metrics collection")
            return

        device_metrics_qs = DeviceMetric.objects.select_related('metric', 'device').filter(
            device__serial_id__in=list(self._validated_devices)
        )
        logger.debug("Fetched %d DeviceMetric records from DB", device_metrics_qs.count())

        device_metric_map = {}
        for dm in device_metrics_qs:
            serial = dm.device.serial_id
            if serial not in device_metric_map:
                device_metric_map[serial] = {}
            device_metric_map[serial][dm.metric.metric_type] = {
                "device_metric_id": dm.id,
                "data_type": dm.metric.data_type,
                "unit": dm.metric.unit,
            }

        self._initial_device_metrics = device_metric_map
        logger.info("Device metrics map built for %d devices", len(device_metric_map))

    def _collect_devices_and_metrics(self) -> None:
        """Wrapper: fetch devices + their metrics"""
        logger.info("Starting collection of devices and their metrics")
        self._collect_devices()
        self._collect_device_metrics()
        logger.info("Completed collection of devices and metrics")

    def _validate(self) -> None:
        for index, item in enumerate(self._initial_data):
            serial = item.get("device_serial_id")
            metrics = item.get("metrics", {})
            ts = item.get("ts")

            if serial not in self._validated_devices:
                self._errors.append(
                    {"index": index, "field": "device", "error": "Device not found"}
                )
                logger.warning("[%d] Device not found: %s", index, serial)
                continue

            device_metrics_map = self._initial_device_metrics.get(serial, {})
            for metric_name, payload in metrics.items():
                value = payload.get("value")
                unit = payload.get("unit")

                device_metric_data = device_metrics_map.get(metric_name)

                if not device_metric_data:
                    self._errors.append(
                        {"index": index, "field": metric_name, "error": "Metric not configured"}
                    )
                    logger.warning(
                        "[%d] Metric not configured for device %s: %s", index, serial, metric_name
                    )
                    continue

                normalized_payload_unit = self._normalize_unit(unit)
                normalized_db_unit = self._normalize_unit(device_metric_data["unit"])

                if normalized_payload_unit != normalized_db_unit:
                    self._errors.append(
                        {"index": index, "field": metric_name, "error": "Unit mismatch"}
                    )

                    logger.warning(
                        "[%d] Unit mismatch for device %s metric %s: payload=%s, db=%s",
                        index,
                        serial,
                        metric_name,
                        normalized_payload_unit,
                        normalized_db_unit,
                    )
                    continue

                if not self._value_matches_data_type(value, device_metric_data["data_type"]):
                    self._errors.append(
                        {"index": index, "field": metric_name, "error": "Type mismatch"}
                    )

                    logger.warning(
                        "[%d] Type mismatch for device %s metric %s: value=%s, expected=%s",
                        index,
                        serial,
                        metric_name,
                        value,
                        device_metric_data["data_type"],
                    )
                    continue

                data_type = device_metric_data["data_type"]
                device_metric_id = device_metric_data["device_metric_id"]

                self._validated_rows.append(
                    {
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
