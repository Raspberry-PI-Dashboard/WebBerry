import asyncio
import json

import websockets

from config import HOST, PORT
from events import EventManager
from gpio import GPIOManager
from i2c import I2CManager
from protocol import Protocol
from shell import ShellManager


events = EventManager()


def emit_event(event, data):
    asyncio.create_task(
        events.broadcast(event, data)
    )


gpio = GPIOManager(
    event_callback=emit_event
)

i2c = I2CManager(
    event_callback=emit_event
)

shell = ShellManager()

protocol = Protocol(
    gpio=gpio,
    i2c=i2c,
    shell=shell,
)


async def client_handler(websocket):

    client = websocket.remote_address

    events.add(websocket)

    print(
        f"[WS] Client connected: {client}"
    )

    try:

        async for raw_message in websocket:

            try:

                message = json.loads(
                    raw_message
                )

                response = await protocol.handle(
                    message
                )

            except json.JSONDecodeError:

                response = {
                    "ok": False,
                    "error": "Invalid JSON",
                }

            except Exception as exc:

                response = {
                    "ok": False,
                    "error": str(exc),
                }

            await websocket.send(
                json.dumps(response)
            )

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:

        events.remove(websocket)

        print(
            f"[WS] Client disconnected: {client}"
        )


async def main():

    print("=" * 50)
    print("Raspberry Pi Control Server")
    print("=" * 50)
    print(f"WebSocket : {HOST}:{PORT}")
    print(
        f"GPIO      : "
        f"{'MOCK' if gpio.backend.is_mock else 'REAL'}"
    )
    print(
        f"I2C       : "
        f"{'MOCK' if i2c.backend.is_mock else 'REAL'} "
        f"(bus {i2c.bus_number})"
    )
    print("=" * 50)

    try:

        async with websockets.serve(
            client_handler,
            HOST,
            PORT,
        ):

            print("[WS] Server ready")

            await asyncio.Future()

    finally:

        gpio.close()
        i2c.close()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nServer stopped")