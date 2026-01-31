import json
import jwt
from django.contrib.auth import authenticate
from datetime import datetime, timedelta, timezone
from django.conf import settings


class UserService:
    @staticmethod
    def get_access_token(username: str, password: str) -> dict:
        if username in ("", None):
            raise TypeError("Must be string")
        if password in ("", None):
            raise TypeError("Must be string")
        user = authenticate(username=username, password=password)

        if user is None:
            raise RuntimeError("Invalid credentials")
        payload = {
        "sub": user.id,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat() + "Z"
        }