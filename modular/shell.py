import asyncio
import subprocess

from config import ALLOWED_SHELL_COMMANDS


class ShellManager:

    async def execute(self, message):
        command = message.get("command")

        if not command:
            raise ValueError(
                "Missing command"
            )

        if command not in ALLOWED_SHELL_COMMANDS:
            raise ValueError(
                f"Command not allowed: {command}"
            )

        args = message.get("args", [])

        if not isinstance(args, list):
            raise ValueError(
                "args must be a list"
            )

        argv = [
            command,
            *[str(arg) for arg in args],
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                argv,
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )

        except subprocess.TimeoutExpired:
            raise ValueError(
                "Command timed out"
            )

        return {
            "ok": result.returncode == 0,
            "type": "shell",
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }