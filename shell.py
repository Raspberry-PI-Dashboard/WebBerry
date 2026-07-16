import asyncio
import json


class ShellSession:

    def __init__(self, websocket):
        self.websocket = websocket
        self.process = None
        self.reader_task = None


    async def send(self, payload):

        await self.websocket.send(
            json.dumps(payload)
        )


    async def start(self):

        self.process = await asyncio.create_subprocess_exec(
            "/bin/bash",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )


        await self.send(
            {
                "type": "shell_started"
            }
        )


        self.reader_task = asyncio.create_task(
            self.read_output()
        )


    async def read_output(self):

        while True:

            data = await self.process.stdout.readline()

            if not data:
                break


            await self.send(
                {
                    "type": "shell_output",
                    "data": data.decode(
                        errors="ignore"
                    )
                }
            )


    async def execute(self, command):

        if not self.process:
            return


        self.process.stdin.write(
            (command + "\n").encode()
        )

        await self.process.stdin.drain()


    async def stop(self):

        if self.process:

            self.process.terminate()

            await self.process.wait()


        if self.reader_task:

            self.reader_task.cancel()
