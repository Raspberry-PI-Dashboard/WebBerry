import asyncio
import json
import signal
import websockets

from client import ClientSession

HOST = "0.0.0.0"
PORT = 8765

PING_INTERVAL = 20
PING_TIMEOUT = 30

clients = set()
shutdown_event = asyncio.Event()


async def client_handler(websocket):

    session = ClientSession(websocket)

    clients.add(session)

    print(
        "Client connected",
        websocket.remote_address
    )

    await session.start()

    try:

        async for raw in websocket:

            try:

                message = json.loads(raw)

                await session.handle_message(message)

            except Exception as e:

                await session.send(
                    {
                        "type": "error",
                        "message": str(e)
                    }
                )

    except websockets.ConnectionClosed:
        pass

    finally:

        await session.close()

        clients.remove(session)

        print(
            "Client disconnected",
            websocket.remote_address
        )


async def broadcast(message):

    await asyncio.gather(
        *[
            client.send(message)
            for client in clients
        ],
        return_exceptions=True
    )


async def shutdown():

    await broadcast(
        {
            "type": "server_shutdown"
        }
    )

    shutdown_event.set()


def setup_signals():

    loop = asyncio.get_running_loop()

    for sig in (
        signal.SIGINT,
        signal.SIGTERM
    ):

        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(
                shutdown()
            )
        )


async def create_server():

    server = await websockets.serve(
        client_handler,
        HOST,
        PORT,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
    )

    await server.start_serving()

    return server


async def run():

    setup_signals()

    server = await create_server()

    print(
        f"Gateway running ws://{HOST}:{PORT}"
    )

    try:

        await shutdown_event.wait()

    finally:

        server.close()

        await server.wait_closed()