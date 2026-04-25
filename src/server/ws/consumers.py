import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "dashboard"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from group
    async def device_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'device_update',
            'data': event['data']
        }))

    async def command_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'command_update',
            'data': event['data']
        }))
