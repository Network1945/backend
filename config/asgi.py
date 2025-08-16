import os, django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from game import routing as game_routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(game_routing.websocket_urlpatterns)),
})