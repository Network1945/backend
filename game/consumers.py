# myapp/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("✅ 클라이언트 연결됨")
        await self.channel_layer.group_add("stream_group", self.channel_name)  # 그룹 등록
        await self.send(text_data=json.dumps({"message": "스트림 연결 OK"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("stream_group", self.channel_name)
        print("❌ 연결 끊김")

    async def receive(self, text_data):
        data = json.loads(text_data)   # dict 형태
        payload = data.get("payload")  # base64 이미지
        frame_no = data.get("frame_no")

        if payload:
            # group_send로 payload와 frame_no 전달
            await self.channel_layer.group_send(
                "stream_group",
                {
                    "type": "send_frame",
                    "payload": payload,
                    "frame_no": frame_no,
                }
            )

    async def send_frame(self, event):
        await self.send(text_data=json.dumps({
            "frame_no": event["frame_no"],
            "payload": event["payload"]
        }))
