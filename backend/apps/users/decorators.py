import jwt
from django.http import JsonResponse
from functools import wraps
from django.conf import settings
from .models import User


def jwt_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization header required"}, status=401)

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            request.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"error": "Invalid token"}, status=401)
        try:
            request.user = User.objects.get(id=payload["sub"])
            request.role = payload.get("role")
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=401)
        return func(request, *args, **kwargs)

    return wrapper


def role_required(rules: dict):
    # "GET" : ["client", "admin"]
    # "POST", "PUT", "PATCH", "DELETE" : ["admin"]
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            allowed_roles = rules.get(request.method)
            if allowed_roles is None:
                return JsonResponse({"error": "Forbidden"}, status=403)
            if isinstance(allowed_roles, str):
                allowed_roles = [allowed_roles]
            if request.role not in allowed_roles:
                return JsonResponse({"error": "Permission denied"}, status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
