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

class RoomConsumer(AsyncWebsocketConsumer):
    redis: Redis = None

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group = f"room_{self.room_id}"
        self.user = getattr(self.scope, "user", None)

        # 인증 확인
        if not self.user or not getattr(self.user, "is_authenticated", False):
            await self.close(code=4401); return

        # Redis 연결(싱글턴)
        if not RoomConsumer.redis:
            url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
            RoomConsumer.redis = Redis.from_url(url, decode_responses=True)

        # 그룹 합류 & accept
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # 멀티탭 카운트 + SET 등록
        n = await RoomConsumer.redis.incr(k_conns(self.room_id, self.user.id))
        if n == 1:
            await RoomConsumer.redis.sadd(k_members(self.room_id), self.user.id)

        # 내게 초기 목록, 모두에 브로드캐스트
        await self._send_presence(to_self=True)
        await self._broadcast_presence()

    async def receive(self, text_data):
        # 필요시 수동 요청 지원
        try:
            data = json.loads(text_data or "{}")
        except Exception:
            data = {}
        if data.get("type") == "who":
            await self._send_presence(to_self=True)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)
        n = await RoomConsumer.redis.decr(k_conns(self.room_id, self.user.id))
        if n <= 0:
            pipe = RoomConsumer.redis.pipeline()
            pipe.delete(k_conns(self.room_id, self.user.id))
            pipe.srem(k_members(self.room_id), self.user.id)
            await pipe.execute()
        await self._broadcast_presence()

    # ---- presence helpers ----
    async def _broadcast_presence(self):
        payload = await self._presence_payload()
        await self.channel_layer.group_send(self.group, {
            "type": "room.presence_update",
            "payload": payload,
        })

    async def room_presence_update(self, event):
        await self.send(json.dumps({"type": "presence_update", **event["payload"]}))

    async def _send_presence(self, to_self=False):
        payload = await self._presence_payload()
        msg = {"type": "presence_update", **payload}
        if to_self:
            await self.send(json.dumps(msg))
        else:
            await self.channel_layer.group_send(self.group, {
                "type": "room.presence_update",
                "payload": payload,
            })

    async def _presence_payload(self):
        ids = await RoomConsumer.redis.smembers(k_members(self.room_id))  # set[str]
        name_map = await self._usernames_by_ids(ids) if ids else {}
        members = [{"userId": str(i), "name": name_map.get(str(i), f"u{i}")} for i in ids]
        members.sort(key=lambda x: x["name"].lower())
        return {"roomId": self.room_id, "count": len(members), "members": members}

    @database_sync_to_async
    def _usernames_by_ids(self, ids):
        qs = User.objects.filter(id__in=list(ids)).values("id", "name")
        return {str(x["id"]): x["name"] for x in qs}