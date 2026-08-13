import asyncio
import json


class EventManager:

    def __init__(self):
        self.clients = set()

    def add(self, websocket):
        self.clients.add(websocket)

    def remove(self, websocket):
        self.clients.discard(websocket)

    async def broadcast(self, event, data=None):
        message = {
            "type": "event",
            "event": event,
            "data": data or {},
        }

        payload = json.dumps(message)

        if not self.clients:
            return

        clients = list(self.clients)

        results = await asyncio.gather(
            *[
                client.send(payload)
                for client in clients
            ],
            return_exceptions=True,
        )

        for client, result in zip(
            clients,
            results,
        ):
            if isinstance(result, Exception):
                self.remove(client)