import json

import pytest
import websockets
from websockets.protocol import State


@pytest.mark.asyncio
async def test_connection(websocket_server):

    async with websockets.connect(
        "ws://localhost:8765"
    ) as ws:
        assert ws.state != State.CLOSED

        response = json.loads(
            await ws.recv()
        )

        assert response["type"] == "connected"
