from rest_framework import serializers
from ..models import Device
from apps.users.models import User 

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('id', 'serial_id', 'name', 'description', 'user', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_serial_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("serial_id cannot be empty")
        return value

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("name cannot be empty")
        return value

    def validate_user(self, value):
        if value is None:
            raise serializers.ValidationError("user must be provided")
        if not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("user does not exist")
        return value
