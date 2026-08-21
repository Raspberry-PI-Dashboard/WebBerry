import sys
import subprocess
from pathlib import Path

import pytest_asyncio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gateway import create_server


SERVICE_NAME = "mio-python.service"


@pytest_asyncio.fixture(scope="session")
async def websocket_server():

    # Stop the production server so pytest can use port 8765.
    subprocess.run(
        ["sudo", "systemctl", "stop", SERVICE_NAME],
        check=True,
    )

    server = None

    try:
        server = await create_server()

        yield server

    finally:
        # Always close the test server and release port 8765.
        if server is not None:
            server.close()
            await server.wait_closed()

        # Start the production server again.
        subprocess.run(
            ["sudo", "systemctl", "start", SERVICE_NAME],
            check=True,
        )