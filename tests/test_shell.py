import json

import pytest
import websockets

@pytest.mark.asyncio
async def test_shell(websocket_server):

    async with websockets.connect(
        "ws://localhost:8765"
    ) as ws:

        await ws.recv()

        await ws.send(json.dumps({
            "type":"shell_start"
        }))

        response = json.loads(
            await ws.recv()
        )

        assert response["type"] == "shell_started"


        await ws.send(json.dumps({
            "type":"shell_input",
            "data":"echo pytest"
        }))

        output = json.loads(
            await ws.recv()
        )

        assert output["type"] == "shell_output"
        assert "pytest" in output["data"]
