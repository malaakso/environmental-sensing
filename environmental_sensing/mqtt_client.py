import json

from asyncio_mqtt import Client

class MqttClient:
    
    def __init__(self, address, queue):
        self.client = Client(address)
        self.queue = queue

    async def disconnect(self):
        await self.client.disconnect()

    async def connect(self):
        await self.client.connect()

    async def run(self):
        await self.connect()
        print("Connected to broker")
        while True:
            # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
            timestamp, address, key, value = await self.queue.get()
            state = {}
            state["time"] = timestamp.isoformat()
            state[key.lower()] = value
            await self.client.publish(
                    f"bt2mqtt/{address}",
                    json.dumps(state)
                )
            self.queue.task_done()