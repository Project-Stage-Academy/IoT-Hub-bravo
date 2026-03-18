from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.common.serializers.json_serializer import JSONSerializer


class RuleEngineSerializer(JSONSerializer):
    """"""
    REQUIRED_FIELDS = {
        'value_jsonb': dict,
        'ts': str,
        'device_metric_id': int,
        'device_serial_id': str,
    }

    def _validate_fields(self, data):
        validated = {}

        # ts
        ts_raw = data.get("ts")
        if ts_raw is None:
            self._errors["ts"] = "'ts' is None"
        else:
            ts = parse_datetime(ts_raw)
            if ts is None:
                self._errors["ts"] = "Invalid datetime format"
            else:
                if timezone.is_naive(ts):
                    ts = timezone.make_aware(ts)
                validated["ts"] = ts

        # value_jsonb
        value = None
        value_type = None

        value_jsonb = data.get("value_jsonb")
        if value_jsonb is None:
            self._errors["value_jsonb"] = "'value_jsonb' is None"
        elif not isinstance(value_jsonb, dict):
            self._errors["value_jsonb"] = "'value_jsonb' must be a dict"
        else:
            value = value_jsonb.get("v")
            value_type = value_jsonb.get("t")

            if value is None or value_type is None:
                self._errors["value_jsonb"] = "'value_jsonb' missing 'v' or 't'"

        if value is not None and value_type is not None:
            validated["value"] = value
            validated["value_type"] = value_type

        # device_metric_id
        device_metric_id = data.get("device_metric_id")
        if device_metric_id is None:
            self._errors["device_metric_id"] = "'device_metric_id' is None"
        elif not isinstance(device_metric_id, int):
            self._errors["device_metric_id"] = "'device_metric_id' must be int"
        else:
            validated["device_metric_id"] = device_metric_id

        # device_serial_id
        device_serial_id = data.get("device_serial_id")
        if device_serial_id is None:
            self._errors["device_serial_id"] = "'device_serial_id' is None"
        elif not isinstance(device_serial_id, str):
            self._errors["device_serial_id"] = "'device_serial_id' must be str"
        else:
            validated["device_serial_id"] = device_serial_id

        if self._errors:
            return None

        return validated