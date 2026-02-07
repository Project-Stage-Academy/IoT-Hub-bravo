import datetime
from typing import Optional, Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime


class BaseSerializer:
    def __init__(self, data: Any):
        self.initial_data = data
        self._validated_data: Optional[Any] = None
        self._errors: dict[str, Any] = {}

    @property
    def validated_data(self):
        if self._validated_data is None:
            raise AssertionError('Call is_valid() first.')
        return self._validated_data

    @property
    def errors(self) -> dict[str, Any]:
        return self._errors

    def is_valid(self) -> bool:
        self._errors = {}
        self._validated_data = self._validate(self.initial_data)
        return not self._errors

    def _validate(self, data: Any):
        raise NotImplementedError


class TelemetryCreateSerializer(BaseSerializer):
    SCHEMA_VERSION = 1
    FIELDS_TYPE_MAP = {
        'schema_version': int,
        'device': str,
        'metrics': dict,
        'ts': str,
    }
    REQUIRED_FIELDS = tuple(FIELDS_TYPE_MAP.keys())
    METRICS_TYPES = (bool, int, float, str)

    def __init__(self, data: Any):
        super().__init__(data)
        self._validated_data: Optional[dict[str, Any]] = None

    def _validate(self, data: Any) -> Optional[dict[str, Any]]:
        if not isinstance(data, dict):
            self._errors['non_field_errors'] = 'Payload must be a JSON object.'
            return None

        # check types of required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                self._errors[field] = f'{field} field is required.'
            elif not isinstance(data[field], self.FIELDS_TYPE_MAP[field]):
                self._errors[field] = (
                    f'{field} must be of type {self.FIELDS_TYPE_MAP[field].__name__}.'
                )

        if self._errors:
            return None

        if not self._schema_version_valid(data['schema_version']):
            return None

        device = self._validate_device(data['device'])
        metrics = self._validate_metrics(data['metrics'])
        ts = self._validate_ts(data['ts'])

        if self._errors:
            return None

        return {
            'device_serial_id': device,
            'metrics': metrics,
            'ts': ts,
        }

    def _schema_version_valid(self, schema_version: int) -> bool:
        if schema_version != self.SCHEMA_VERSION:
            self._errors['schema_version'] = (
                f'Unsupported schema_version: {schema_version}. '
                f'Supported: {self.SCHEMA_VERSION}.'
            )
            return False
        return True

    def _validate_device(self, device_raw: str) -> Optional[str]:
        device = device_raw.strip()
        if not device:
            self._errors['device'] = 'device must be a non-empty string.'
            return None
        return device

    def _validate_metrics(self, metrics_raw: dict) -> Optional[dict[str, Any]]:
        metrics = {}
        metrics_errors = {}

        for name, value in metrics_raw.items():
            if not isinstance(name, str) or not name.strip():
                metrics_errors[str(name)] = 'metric name must be a non-empty string.'
                continue

            name = name.strip()
            if not isinstance(value, self.METRICS_TYPES):
                metrics_errors[name] = 'metric value must be of type bool/int/float/str.'
                continue

            metrics[name] = value

        if metrics_errors:
            self._errors['metrics'] = metrics_errors
            return None
        return metrics

    def _validate_ts(self, ts_raw: str) -> Optional[datetime.datetime]:
        ts = ts_raw.strip()
        if not ts:
            self._errors['ts'] = 'ts must be a non-empty ISO-8601 datetime string.'
            return None

        ts = parse_datetime(ts)
        if ts is None:
            self._errors['ts'] = 'ts must be a valid ISO-8601 datetime.'
            return None

        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts)

        return ts


class TelemetryBatchCreateSerializer(BaseSerializer):
    def __init__(self, data: Any):
        super().__init__(data)
        self._validated_data: Optional[list[dict[str, Any]]] = None
        self._item_errors: dict[int, Any] = {}

    @property
    def item_errors(self) -> dict[int, Any]:
        return self._item_errors

    def _validate(self, data: Any) -> Optional[list[dict[str, Any]]]:
        if not isinstance(data, list):
            self._errors['non_field_errors'] = 'Payload must be a JSON array.'
            return None

        self._item_errors: dict[int, Any] = {}
        items: list[dict[str, Any]] = []

        for index, raw_item in enumerate(data):
            serializer = TelemetryCreateSerializer(raw_item)
            if not serializer.is_valid():
                self.item_errors[index] = serializer.errors
                continue
            items.append(serializer.validated_data)

        # if any valid items -> is_valid() == True
        if items:
            return items

        # if no valid items -> is_valid() == False
        self._errors['items'] = self._item_errors or {'non_field_errors': 'Empty batch.'}
        return None
