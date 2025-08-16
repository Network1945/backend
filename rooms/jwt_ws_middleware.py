# rooms/jwt_ws_middleware.py
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.settings import api_settings

User = get_user_model()

@database_sync_to_async
def get_user_async(uid):
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTQueryAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        try:
            query = parse_qs(scope.get("query_string", b"").decode() or "")
            token = (query.get("token") or [None])[0]
            print("[MW] query:", query)  # 🔎

            if token:
                ut = UntypedToken(token)  # 서명/만료 검증 (여기서 만료면 예외)
                payload = ut.payload
                print("[MW] payload keys:", list(payload.keys()))  # 🔎
                print("[MW] payload:", payload)                    # 🔎

                # 기본: SIMPLE_JWT.USER_ID_CLAIM (기본 'user_id')
                claim_key = api_settings.USER_ID_CLAIM
                uid = payload.get(claim_key)

                # 혹시 커스텀 발급 코드가 'id'나 'sub'로 넣었을 수 있으니 fallback
                if uid is None:
                    uid = payload.get("id") or payload.get("sub") or payload.get("userId")

                print("[MW] uid resolved:", uid)  # 🔎

                if uid is not None:
                    user = await get_user_async(uid)
                    scope["user"] = user
                else:
                    print("[MW] uid not found in payload")

        except Exception as e:
            print("[MW] auth error:", repr(e))

        return await self.app(scope, receive, send)