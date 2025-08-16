# rooms/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from redis.asyncio import Redis
from django.contrib.auth import get_user_model

User = get_user_model()

def k_members(room_id):       return f"room:{room_id}:members"          # SET of user_id
def k_conns(room_id, uid):    return f"room:{room_id}:conns:{uid}"      # INT connection count

# rooms/consumers.py (핵심 변경만 발췌)
class RoomConsumer(AsyncWebsocketConsumer):
    redis: Redis = None

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"].get("room_id")
        self.group = f"room_{self.room_id}"
        self.user = getattr(self.scope, "user", None)
        self.joined = False  # ✅ 정상 합류 여부 플래그

        # 인증 실패 시 즉시 종료
        if not self.user or not getattr(self.user, "is_authenticated", False):
            await self.close(code=4401)
            return

        # ✅ redis 보장: connect 단계에서 먼저 초기화
        if not RoomConsumer.redis:
            url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
            RoomConsumer.redis = Redis.from_url(url, decode_responses=True)

        # 그룹 등록 & accept
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # 멀티탭 카운트/SET 등록
        try:
            n = await RoomConsumer.redis.incr(k_conns(self.room_id, self.user.id))
            if n == 1:
                await RoomConsumer.redis.sadd(k_members(self.room_id), self.user.id)
        except Exception:
            # Redis 장애 시에도 세션만 유지하게 하고, joined는 False로 둠
            await self.close(code=1011)  # Internal error
            return

        self.joined = True  # ✅ 여기서만 True

        # 초기 프레즌스
        await self._send_presence(to_self=True)
        await self._broadcast_presence()

    async def disconnect(self, code):
        # 그룹 제거는 시도 (채널 레이어는 존재)
        try:
            await self.channel_layer.group_discard(self.group, self.channel_name)
        except Exception:
            pass

        # ✅ 정상 합류 전/Redis 미초기화면 조용히 종료
        if not self.joined or RoomConsumer.redis is None or not self.user:
            return

        try:
            n = await RoomConsumer.redis.decr(k_conns(self.room_id, self.user.id))
            if n <= 0:
                pipe = RoomConsumer.redis.pipeline()
                pipe.delete(k_conns(self.room_id, self.user.id))
                pipe.srem(k_members(self.room_id), self.user.id)
                await pipe.execute()
        except Exception:
            # Redis 일시 장애일 수 있으니 무시하고 마무리
            return

        # 프레즌스 갱신 브로드캐스트
        try:
            await self._broadcast_presence()
        except Exception:
            pass