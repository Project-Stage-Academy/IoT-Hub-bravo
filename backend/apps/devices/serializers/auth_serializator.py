# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from datetime import datetime, timezone

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Формуємо схему відповіді як у OpenAPI
        data = {
            "access_token": data["access"],
            "token_type": "bearer",
            "expires_in": (datetime.fromtimestamp(self.access_token["exp"], tz=timezone.utc)).isoformat(),
        }
        return data
