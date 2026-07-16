import sys
from pathlib import Path

import pytest_asyncio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gateway import create_server



@pytest_asyncio.fixture(scope="function")
async def websocket_server():

    server = await create_server()

    yield server

    server.close()
    await server.wait_closed()