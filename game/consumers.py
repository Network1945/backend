# game/consumers.py (최소 골격)
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        await self.channel_layer.group_add(self.room_id, self.channel_name)
        await self.accept()

    async def receive_json(self, content):
        pass

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_id, self.channel_name)