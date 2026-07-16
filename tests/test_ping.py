import json

import pytest
import websockets

@pytest.mark.asyncio
async def test_ping(websocket_server):

    async with websockets.connect(
        "ws://localhost:8765"
    ) as ws:

        await ws.recv()

        await ws.send(json.dumps({
            "type":"ping"
        }))

        response = json.loads(
            await ws.recv()
        )

        assert response["type"] == "pong"
