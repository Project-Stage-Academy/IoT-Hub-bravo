import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.devices.routing import websocket_urlpatterns
from apps.users.middleware.channels_jwt import JWTAuthMiddleware
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns),
        ),
    }
)