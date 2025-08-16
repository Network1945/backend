# rooms/consumers.py
import json
import asyncio
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from redis.asyncio import Redis


# ---------- Redis 키 헬퍼 ----------
def k_members(room_id):      return f"room:{room_id}:members"          # SET of names
def k_conns(room_id, name):  return f"room:{room_id}:conns:{name}"     # INT connection count


class RoomConsumer(AsyncWebsocketConsumer):
    """
    이름 기반(비-JWT) WebSocket 컨슈머
    - 접속: ws://<host>/ws/rooms/<room_id>/?name=<username>
    - 프레즌스 저장: Redis SET(room:<room_id>:members) 에 이름 보관
    - 멀티탭: Redis INT(room:<room_id>:conns:<name>) 로 카운트
    - 이벤트:
        * 입/퇴장 시 presence_update 브로드캐스트
        * 2초마다 현재 목록 푸시 (기본: 자기 자신에게만 / 옵션: 모두에게)
    """

    # 주기 푸시 대상:
    # False => 자기 자신에게만 (권장: 불필요한 네트워크 트래픽 감소)
    # True  => 방 전체에 브로드캐스트 (모두 동시에 업데이트 받음)
    SEND_TO_ALL = False

    redis: Redis = None

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"].get("room_id")
        self.group = f"room_{self.room_id}"
        self.joined = False
        self.ticker = None

        # 1) 쿼리에서 name 읽기
        query = parse_qs((self.scope.get("query_string") or b"").decode())
        self.name = (query.get("name") or [None])[0]

        # 간단 검증: 비어있거나 너무 길면 거절
        if not self.name or len(self.name) > 32:
            await self.close(code=4400)  # Bad request
            return

        # 2) Redis 준비
        if not RoomConsumer.redis:
            url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
            RoomConsumer.redis = Redis.from_url(url, decode_responses=True)

        # 3) 그룹 합류 & accept
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # 4) 멀티탭 카운트/멤버셋 업데이트
        try:
            n = await RoomConsumer.redis.incr(k_conns(self.room_id, self.name))
            if n == 1:
                await RoomConsumer.redis.sadd(k_members(self.room_id), self.name)
        except Exception:
            await self.close(code=1011)
            return

        self.joined = True

        # 5) 입장 직후: 내게 초기 프레즌스 & 모두에게 브로드캐스트
        await self._send_presence(to_self=True)
        await self._broadcast_presence()

        # 6) 2초마다 현재 목록 푸시하는 ticker 시작
        self.ticker = asyncio.create_task(self._ticker())

    async def receive(self, text_data):
        # 클라가 수동으로 목록 요청하면 처리
        data = {}
        try:
            data = json.loads(text_data or "{}")
        except Exception:
            pass

        if data.get("type") == "who":
            await self._send_presence(to_self=True)

    async def disconnect(self, code):
        # 그룹 제거
        try:
            await self.channel_layer.group_discard(self.group, self.channel_name)
        except Exception:
            pass

        # ticker 정리
        if self.ticker:
            try:
                self.ticker.cancel()
                await self.ticker
            except Exception:
                pass

        # 정상 합류 전이거나 redis 없음이면 조용히 종료
        if not self.joined or RoomConsumer.redis is None:
            return

        # 멀티탭 카운트 감소/멤버셋 정리
        try:
            n = await RoomConsumer.redis.decr(k_conns(self.room_id, self.name))
            if n <= 0:
                pipe = RoomConsumer.redis.pipeline()
                pipe.delete(k_conns(self.room_id, self.name))
                pipe.srem(k_members(self.room_id), self.name)
                await pipe.execute()
        except Exception:
            return

        # 퇴장 브로드캐스트
        try:
            await self._broadcast_presence()
        except Exception:
            pass

    # ---------- presence helpers ----------
    async def _presence_payload(self):
        names = await RoomConsumer.redis.smembers(k_members(self.room_id))
        members = [{"name": nm} for nm in sorted(names, key=lambda s: s.lower())]
        return {"roomId": self.room_id, "count": len(members), "members": members}

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

    # ---------- 2초 ticker ----------
    async def _ticker(self):
        try:
            while self.joined:
                await asyncio.sleep(2)

                if self.SEND_TO_ALL:
                    # 모든 참가자에게 브로드캐스트
                    await self._broadcast_presence()
                else:
                    # 내게만 현재 목록 전송
                    await self._send_presence(to_self=True)

        except asyncio.CancelledError:
            # disconnect()에서 cancel되면 여기로 빠짐
            pass