# rooms/consumers.py (발췌)
import asyncio
import json
from redis.asyncio import Redis
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs

def k_members(room_id):      return f"room:{room_id}:members"
def k_conns(room_id, name):  return f"room:{room_id}:conns:{name}"

class RoomConsumer(AsyncWebsocketConsumer):
    redis: Redis = None
    TICK_SEC = 2

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group = f"room_{self.room_id}"
        self.joined = False
        self.ticker = None

        # name 쿼리
        query = parse_qs((self.scope.get("query_string") or b"").decode())
        self.name = (query.get("name") or [None])[0]
        if not self.name:
            await self.close(code=4400); return

        # Redis 준비
        if not RoomConsumer.redis:
            from django.conf import settings
            url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
            RoomConsumer.redis = Redis.from_url(url, decode_responses=True)

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # 멀티탭 카운트 관리
        n = await RoomConsumer.redis.incr(k_conns(self.room_id, self.name))
        if n == 1:
            await RoomConsumer.redis.sadd(k_members(self.room_id), self.name)

        self.joined = True

        # ✅ 입장 즉시 현재 카운트 브로드캐스트
        await self._broadcast_count()

        # ✅ 2초마다 카운트만 브로드캐스트
        self.ticker = asyncio.create_task(self._count_ticker())

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.group, self.channel_name)
        except Exception:
            pass

        if self.ticker:
            try:
                self.ticker.cancel()
                await self.ticker
            except Exception:
                pass

        if not self.joined or RoomConsumer.redis is None:
            return

        # 멀티탭 감소 & 필요 시 멤버 제거
        n = await RoomConsumer.redis.decr(k_conns(self.room_id, self.name))
        if n <= 0:
            pipe = RoomConsumer.redis.pipeline()
            pipe.delete(k_conns(self.room_id, self.name))
            pipe.srem(k_members(self.room_id), self.name)
            await pipe.execute()

        # ✅ 퇴장 즉시 카운트 브로드캐스트
        await self._broadcast_count()

    # ---------- broadcast helpers ----------
    async def _get_count(self) -> int:
        return await RoomConsumer.redis.scard(k_members(self.room_id))

    async def _broadcast_count(self):
        # 현재 접속자 수 + 사용자 목록 가져오기
        names = await RoomConsumer.redis.smembers(k_members(self.room_id))
        members = sorted(names, key=lambda s: s.lower())  # 보기 좋게 정렬
        cnt = len(members)

        await self.channel_layer.group_send(self.group, {
            "type": "room.presence_count",
            "payload": {
                "type": "presence_count",
                "roomId": self.room_id,
                "count": cnt,
                "members": members,  # ✅ 사용자 이름들 같이 전송
            },
        })

    async def room_presence_count(self, event):
        await self.send(json.dumps(event["payload"]))
    async def room_presence_count(self, event):
        await self.send(json.dumps(event["payload"]))

    async def _count_ticker(self):
        try:
            while self.joined:
                await asyncio.sleep(self.TICK_SEC)
                await self._broadcast_count()
        except asyncio.CancelledError:
            pass

    # 선택: 클라가 "who" 보내면 즉시 count만 응답
    async def receive(self, text_data=None, bytes_data=None):
        txt = (text_data or "").strip().lower()
        if txt == "who" or '"type":"who"' in txt:
            await self._broadcast_count()