# config/asgi.py
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import rooms.routing
from rooms.jwt_ws_middleware import JWTQueryAuthMiddleware

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTQueryAuthMiddleware(
        URLRouter(rooms.routing.websocket_urlpatterns)
    ),
})