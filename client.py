import json
from datetime import datetime, timezone

from config import ALLOWED_PINS, MOCK_GPIO
from shell import ShellSession

try:
    from gpiozero import DigitalInputDevice
except ImportError:
    DigitalInputDevice = None


class MockInput:
    def __init__(self, pin):
        self.pin = pin
        self.value = False

    def close(self):
        pass


class ClientSession:

    def __init__(self, websocket):

        self.websocket = websocket

        self.shell = None
        self.inputs = {}

        self.authenticated = False

        self.connected_at = datetime.now(timezone.utc)


    async def send(self, payload):

        await self.websocket.send(
            json.dumps(payload)
        )


    async def start(self):

        await self.send(
            {
                "type": "connected",
                "timestamp": self.timestamp(),
                "message": "Raspberry Pi Gateway ready"
            }
        )


    def timestamp(self):

        return datetime.now(timezone.utc).isoformat()


    def read_gpio(self, pin):

        try:
            pin = int(pin)
        except (TypeError, ValueError):
            raise ValueError("Invalid GPIO pin")

        if pin not in ALLOWED_PINS:
            raise ValueError(f"GPIO {pin} is not allowed")

        if pin not in self.inputs:
            if MOCK_GPIO or DigitalInputDevice is None:
                self.inputs[pin] = MockInput(pin)
            else:
                self.inputs[pin] = DigitalInputDevice(pin)

        return {
            "type": "pin",
            "action": "read",
            "pin": pin,
            "value": bool(self.inputs[pin].value),
        }


    async def handle_message(self, message):

        msg_type = message.get(
            "type"
        )


        if msg_type == "ping":

            await self.send(
                {
                    "type": "pong",
                    "timestamp": self.timestamp()
                }
            )


        elif msg_type == "info":

            await self.send(
                {
                    "type": "info",
                    "connected_at": self.connected_at.isoformat()
                }
            )


        elif msg_type == "pin" and message.get("action") == "read":

            await self.send(
                self.read_gpio(message.get("pin"))
            )


        elif msg_type == "shell_start":

            if self.shell is None:

                self.shell = ShellSession(
                    self.websocket
                )

                await self.shell.start()

            else:

                await self.send(
                    {
                        "type":"error",
                        "message":"Shell already running"
                    }
                )


        elif msg_type == "shell_input":

            if self.shell:

                await self.shell.execute(
                    message.get("data","")
                )

            else:

                await self.send(
                    {
                        "type":"error",
                        "message":"Shell not started"
                    }
                )


        else:

            await self.send(
                {
                    "type":"error",
                    "message":
                    f"Unknown command {msg_type}"
                }
            )


    async def close(self):

        if self.shell:

            await self.shell.stop()

        for input_device in self.inputs.values():
            input_device.close()
