import json
from datetime import datetime, timezone

from modular.gpio.manager import GPIOManager
from shell import ShellSession
from update_manager import deploy


class ClientSession:

    def __init__(self, websocket, gpio=None):

        self.websocket = websocket

        self.shell = None

        self.authenticated = False

        self.connected_at = datetime.now(timezone.utc)

        self.gpio = gpio or GPIOManager()
        self.owns_gpio = gpio is None


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
                    "connected_at":
                    self.connected_at.isoformat()
                }
            )


        elif msg_type == "pin":

            await self.handle_pin(
                message
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
                        "type": "error",
                        "message": "Shell already running"
                    }
                )


        elif msg_type == "shell_input":

            if self.shell:

                await self.shell.execute(
                    message.get("data", "")
                )

            else:

                await self.send(
                    {
                        "type": "error",
                        "message": "Shell not started"
                    }
                )


        elif msg_type == "update":

            await self.handle_update()


        else:

            await self.send(
                {
                    "type": "error",
                    "message":
                    f"Unknown command {msg_type}"
                }
            )


    async def handle_update(self):

        async for progress in deploy():

            await self.send(
                {
                    "type": "update",
                    **progress,
                }
            )


    async def handle_pin(self, message):

        action = message.get("action")
        pin = message.get("pin")


        if action == "mode":

            result = self.gpio.mode(
                pin,
                message.get("mode")
            )


        elif action == "set":

            result = self.gpio.set(
                pin,
                message.get("value")
            )


        elif action == "toggle":

            result = self.gpio.toggle(
                pin
            )


        elif action == "read":

            result = self.gpio.read(
                pin
            )


        elif action == "pwm_set":

            result = self.gpio.pwm_set(
                pin,
                message.get("duty_cycle"),
                message.get("frequency")
            )


        elif action == "pwm_stop":

            result = self.gpio.pwm_stop(
                pin
            )


        else:

            raise ValueError(
                f"Unknown pin action: {action}"
            )


        await self.send(
            {
                "type": "pin",
                "action": action,
                **result,
            }
        )


    async def close(self):

        if self.shell:

            await self.shell.stop()

        if self.owns_gpio:
            self.gpio.close()

