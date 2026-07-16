import json
from datetime import datetime

from shell import ShellSession


class ClientSession:

    def __init__(self, websocket):

        self.websocket = websocket

        self.shell = None

        self.authenticated = False

        self.connected_at = datetime.utcnow()


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

        return datetime.utcnow().isoformat()


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
