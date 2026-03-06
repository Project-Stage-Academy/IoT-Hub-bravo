import logging

from apps.common.serializers import JSONSerializer

logger = logging.getLogger(__name__)


class RuleCreateSerializer(JSONSerializer):
    SCHEMA_VERSION = 1
    REQUIRED_FIELDS = {
        'schema_version': int,
        'name': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric_id': int,
    }
    OPTIONAL_FIELDS = {
        'description': str,
    }


class RulePatchSerializer(JSONSerializer):
    """Serializer for patch"""

    SCHEMA_VERSION = 1
    REQUIRED_FIELDS = {
        'schema_version': int,
    }
    OPTIONAL_FIELDS = {
        'name': str,
        'description': str,
        'condition': dict,
        'action': dict,
        'is_active': bool,
        'device_metric_id': int,
    }
