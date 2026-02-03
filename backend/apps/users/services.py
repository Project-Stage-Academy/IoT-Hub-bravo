import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import authenticate
from .models import User

class UserService:
    @staticmethod
    def get_access_token(username: str, password: str) -> dict:
        if not isinstance(username, str) or not username:
            raise TypeError("Username must be a non-empty string")
        if not isinstance(password, str) or not password:
            raise TypeError("Password must be a non-empty string")

        user = authenticate(username=username, password=password)
        if not user:
            raise RuntimeError("Invalid credentials")

        exp = datetime.now(timezone.utc) + timedelta(hours=1)
        payload = {
            "sub": user.id,
            "role": user.role,
            "exp": int(exp.timestamp()),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": exp.isoformat() + "Z",
        }
