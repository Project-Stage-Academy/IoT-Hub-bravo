import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from apps.devices.routing import websocket_urlpatterns  # noqa: E402
from apps.users.middleware.channels_jwt import JWTAuthMiddleware  # noqa: E402



application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns),
        ),
    }
)
