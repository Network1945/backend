# rooms/jwt_ws_middleware.py
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

User = get_user_model()

class JWTQueryAuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.auth = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        try:
            query = parse_qs(scope.get("query_string", b"").decode())
            token = (query.get("token") or [None])[0]
            if token:
                validated = self.auth.get_validated_token(token)
                scope["user"] = self.auth.get_user(validated)
            else:
                scope["user"] = AnonymousUser()
        except Exception:
            scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)