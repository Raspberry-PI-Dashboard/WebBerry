#!/usr/bin/env python3

import asyncio
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

    session = ClientSession(
        websocket
    )

    clients.add(
        session
    )


    print(
        "Client connected",
        websocket.remote_address
    )


    await session.start()


    try:

        async for raw in websocket:

            try:

                import json

                message = json.loads(
                    raw
                )


                await session.handle_message(
                    message
                )


            except Exception as e:

                await session.send(
                    {
                        "type":"error",
                        "message":str(e)
                    }
                )


    except websockets.ConnectionClosed:

        pass


    finally:

        await session.close()

        clients.remove(
            session
        )


        print(
            "Client disconnected",
            websocket.remote_address
        )



async def broadcast(message):

    for client in clients:

        await client.send(
            message
        )



async def shutdown():

    print(
        "Stopping gateway"
    )


    await broadcast(
        {
            "type":"server_shutdown"
        }
    )


    shutdown_event.set()



def setup_signals():

    loop = asyncio.get_running_loop()

    for sig in (
        signal.SIGTERM,
        signal.SIGINT
    ):

        loop.add_signal_handler(
            sig,
            lambda:
            asyncio.create_task(
                shutdown()
            )
        )



async def main():

    setup_signals()


    async with websockets.serve(
        client_handler,
        HOST,
        PORT,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT
    ):

        print(
            f"Gateway running ws://{HOST}:{PORT}"
        )


        await shutdown_event.wait()



if __name__ == "__main__":

    asyncio.run(
        main()
    )
