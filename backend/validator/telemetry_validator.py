from .base_validator import BaseValidator
from typing import Any, Iterable
from apps.devices.models import Metric, Device, DeviceMetric
from django.db.models import Q, Prefetch
from functools import reduce
import operator




class TelemetryValidator(BaseValidator):
    def __init__(self, *, device_serial_id: str, metrics: dict, ts):
        super().__init__()
        self._device_serial_id = device_serial_id
        self._metrics = metrics
        self._ts = ts

        self._device = None
        self._validated_metrics: dict[str, dict] = {}

    def is_valid(self) -> bool:
        self._reset_state()
        self._validate()
        return not self._errors    
    
    def _validate(self):
        if not self._validate_device():
            return

        self._validate_metrics()

    def _reset_state(self):
        self._device = None
        self._validated_metrics.clear()
        self._errors.clear() 

    @property
    def validated_metrics(self) -> dict[str, dict]:
        return dict(self._validated_metrics)

    def _validate_device(self):
        try:
            self._device = Device.objects.get(serial_id=self._device_serial_id)
        except Device.DoesNotExist:
            self.errors['device'] = 'Device not found.'
            return False

        if not self._device.is_active:
            self.errors['device'] = 'Device is not active.'
            return False
        
        return True
    
    def _validate_metrics(self):
        if not isinstance(self._metrics, dict):
            self.errors['metrics'] = 'Metrics must be a dictionary.'
            return

        if not self._metrics:
            self.errors['metrics'] = 'No valid metric names.'
            return

        normalized_metrics = self._normalize_metrics(self._metrics)
        if not normalized_metrics:
            self.errors['metrics'] = 'No valid metric names.'
            return False

        metric_names = list(normalized_metrics.keys())

        metrics_by_name = self._get_metrics_by_names(metric_names)
        device_metrics = self._get_device_metrics_by_names(self._device, metric_names)

        for name, payload in normalized_metrics.items():
            value = payload['value']
            unit = payload['unit']
            metric = metrics_by_name.get(name)
            if not metric:
                self.errors[name] = 'metric does not exist.'
                continue

            device_metric = device_metrics.get(name)
            if not device_metric:
                self.errors[name] = 'metric not configured for device.'
                continue

            if not self._value_matches_data_type(value, metric.data_type):
                self.errors[name] = f'Type mismatch (expected {metric.data_type})'
                continue

            self._validated_metrics[name] = {
                "metric": metric,
                "device_metric": device_metric,
                "value": value,
            }

        return not self._errors



    def _normalize_metrics(self, metrics: dict[str, Any]) -> dict[str, dict[Any, str]]:
        """Utility function to normalize metric-{value,unit} dictionary keys."""
        normalized = {}
        for name, payload in metrics.items():
            name = name.strip()
            value = payload.get("value")
            unit = payload.get("unit")

            if name:
                normalized[name] = {
                    "value": value,
                    "unit": unit,
                }
        return normalized
    
    def aboba(self, metric_keys):
        return self._get_metrics_by_names(metric_keys=metric_keys)

    def _get_metrics_by_names(self, metric_keys: Iterable[tuple[str,str]]) -> dict[tuple[str, str], Metric]:
        """
        Utility function to retrieve Metric
        objects by provided metrics names.
        """
        query = reduce(
            operator.or_,
            (Q(metric_type=name, unit=unit) for name, unit in metric_keys),
            )

        qs = Metric.objects.filter(query)

        return {(m.metric_type, m.unit): m for m in qs}
    
    def _get_device_metrics_by_names(self,
    device: Device,
    metrics_names: list[str],
) -> dict[str, DeviceMetric]:
        qs = DeviceMetric.objects.select_related('metric').filter(
            device=device, metric__metric_type__in=metrics_names
        )
        return {dm.metric.metric_type: dm for dm in qs}


    def _value_matches_data_type(self, value: Any, data_type: str) -> bool:
        if data_type == 'numeric':
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if data_type == 'bool':
            return isinstance(value, bool)
        if data_type == 'str':
            return isinstance(value, str)
        return False






class TelemetryBatchValidator(BaseValidator):
    def __init__(self, payload):
        super().__init__()
        self._validated_rows = []
        self._initial_data = payload
        self._validated_devices = {}
        self._initial_device_metrics = {}

    @property
    def validated_devices(self):
        return self._validated_devices
    
    @property
    def initial_device_metrics(self):
        return self._initial_device_metrics

    @property
    def validate_rows(self):
        return self._validated_rows
        
    def _collect_devices(self):
        """Fetch all devices from payload and populate _validated_devices"""
        device_serials = {item['device'] for item in self._initial_data}

        devices = Device.objects.filter(serial_id__in=device_serials)
        device_map = {d.serial_id: d for d in devices.id}

        found_serials = set(device_map.keys())
        missing_serials = device_serials - found_serials
        if missing_serials:
            self._errors['device'] = f"Missing serials: {missing_serials}"

        self._validated_devices = device_map


    def _collect_device_metrics(self):
        """Fetch all DeviceMetrics and Metrics in one query and build map"""
        if not self._validated_devices:
            return

        device_metrics_qs = (
            DeviceMetric.objects
            .select_related('metric', 'device')
            .filter(device__serial_id__in=self._validated_devices.keys())
        )

        # device -> metric_type -> {"device_metric", "unit"}
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


    def _collect_devices_and_metrics(self):
        """Wrapper: fetch devices + their metrics"""
        self._collect_devices()
        self._collect_device_metrics()
    

    def is_valid(self):
        self._errors.clear()
        self._validated_rows = []

        self._collect_devices_and_metrics()

        if self._errors:
            return False

        self._validate()

        return not self._errors


    def _validate(self):
        for index, item in enumerate(self._initial_data):
            serial = item.get("device")
            metrics = item.get("metrics", {})
            ts = item.get("ts")

            device = self._validated_devices.get(serial)
            if not device:
                self._errors[index] = {"device": "Device not found"}
                continue

            device_metrics_map = self._initial_device_metrics.get(serial, {})

            for metric_name, payload in metrics.items():
                value = payload.get("value")
                unit = payload.get("unit")

                device_metric_data = device_metrics_map.get(metric_name)

                if not device_metric_data:
                    self._errors.setdefault(index, {})[metric_name] = "Metric not configured"
                    continue

                if unit != device_metric_data["unit"]:
                    self._errors.setdefault(index, {})[metric_name] = "Unit mismatch"
                    continue

                if not self._value_matches_data_type(value, device_metric_data["data_type"]):
                    self._errors.setdefault(index, {})[metric_name] = "Type mismatch"
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
                        }
                    }
                )
                # device_metric=dm,
                # ts=ts,
                # value_jsonb={
                #     't': data_type,
                #     'v': value,
                # }
    #dm -> id