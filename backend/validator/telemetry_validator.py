from .base_validator import BaseValidator
from typing import Any
from apps.devices.models import Metric, Device, DeviceMetric


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

        for name, value in normalized_metrics.items():

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



    def _normalize_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Utility function to normalize metric-value dictionary keys."""
        normalized = {}
        for name, value in metrics.items():
            name = name.strip()
            if name:
                normalized[name] = value
        return normalized
    
    def _get_metrics_by_names(self, metrics_names: list[str]) -> dict[str, Metric]:
        """
        Utility function to retrieve Metric
        objects by provided metrics names.
        """
        return {m.metric_type: m for m in Metric.objects.filter(metric_type__in=metrics_names)}
    
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