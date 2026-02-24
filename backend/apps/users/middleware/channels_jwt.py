from urllib.parse import parse_qs

import jwt
from asgiref.sync import sync_to_async
from django.conf import settings

from apps.users.models import User


@sync_to_async
def get_user_from_token(token: str):
    from django.contrib.auth.models import AnonymousUser

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            return AnonymousUser(), None

        user = User.objects.get(id=user_id, is_active=True)
        return user, payload.get("role")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist, Exception):
        return AnonymousUser(), None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        params = parse_qs(scope.get("query_string", b"").decode())
        token = params.get("token", [None])[0]

        if token:
            user, role = await get_user_from_token(token)
            scope["user"] = user
            scope["role"] = role
        else:
            scope["user"] = AnonymousUser()
            scope["role"] = None

        return await self.inner(scope, receive, send)
