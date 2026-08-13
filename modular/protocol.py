import platform

from config import (
    ALLOWED_PINS,
    ALLOWED_SHELL_COMMANDS,
    DEFAULT_PWM_FREQUENCY,
    I2C_BUS,
    MOCK_GPIO,
    PROTOCOL_VERSION,
)


class Protocol:

    def __init__(self, gpio, shell, i2c):
        self.gpio = gpio
        self.shell = shell
        self.i2c = i2c

    async def handle(self, message):

        if not isinstance(message, dict):
            raise ValueError(
                "Message must be a JSON object"
            )

        message_type = message.get("type")

        if message_type == "startup":
            return self.startup()

        if message_type == "ping":
            return {
                "ok": True,
                "type": "pong",
            }

        if message_type == "pin":
            return self.pin(message)

        if message_type == "i2c":
            return self.i2c_command(message)

        if message_type == "shell":
            return await self.shell_command(message)

        raise ValueError(
            f"Unknown message type: {message_type}"
        )

    def startup(self):
        return {
            "ok": True,
            "type": "startup",

            "protocol": {
                "version": PROTOCOL_VERSION,
            },

            "device": {
                "name": platform.node(),
                "platform": platform.system(),
                "release": platform.release(),
                "mock_gpio": MOCK_GPIO,
            },

            "capabilities": [
                "digital",
                "pwm",
                "read",
                "i2c",
                "shell",
            ],

            "pins": sorted(ALLOWED_PINS),

            "pwm": {
                "default_frequency": (
                    DEFAULT_PWM_FREQUENCY
                ),
                "duty_cycle_min": 0.0,
                "duty_cycle_max": 1.0,
            },

            "i2c": {
                "bus": I2C_BUS,
                "mock": self.i2c.backend.is_mock,
                "operations": [
                    "scan",
                    "read_byte",
                    "write_byte",
                    "read_register",
                    "write_register",
                    "read_block",
                    "write_block",
                ],
            },

            "shell": {
                "commands": sorted(
                    ALLOWED_SHELL_COMMANDS
                ),
            },

            "state": {
                "gpio": self.gpio.state(),
                "i2c": self.i2c.state(),
            },
        }

    # ------------------------------------------------------------------
    # GPIO
    # ------------------------------------------------------------------

    def pin(self, message):

        action = message.get("action")
        pin = message.get("pin")

        if pin is None:
            raise ValueError("Missing pin")

        if action == "set":

            result = self.gpio.set(
                pin,
                message.get("value"),
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
                message.get("frequency"),
            )

        elif action == "pwm_stop":

            result = self.gpio.pwm_stop(
                pin
            )

        else:
            raise ValueError(
                f"Unknown pin action: {action}"
            )

        return {
            "ok": True,
            "type": "pin",
            "action": action,
            **result,
        }

    # ------------------------------------------------------------------
    # I2C
    # ------------------------------------------------------------------

    def i2c_command(self, message):

        action = message.get("action")

        if action == "scan":

            result = self.i2c.scan()

        elif action == "read_byte":

            result = self.i2c.read_byte(
                message.get("address")
            )

        elif action == "write_byte":

            result = self.i2c.write_byte(
                message.get("address"),
                message.get("value"),
            )

        elif action == "read_register":

            result = self.i2c.read_register(
                message.get("address"),
                message.get("register"),
            )

        elif action == "write_register":

            result = self.i2c.write_register(
                message.get("address"),
                message.get("register"),
                message.get("value"),
            )

        elif action == "read_block":

            result = self.i2c.read_block(
                message.get("address"),
                message.get("register"),
                message.get("length"),
            )

        elif action == "write_block":

            result = self.i2c.write_block(
                message.get("address"),
                message.get("register"),
                message.get("data"),
            )

        else:
            raise ValueError(
                f"Unknown I2C action: {action}"
            )

        return {
            "ok": True,
            "type": "i2c",
            "action": action,
            **result,
        }

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    async def shell_command(self, message):
        return await self.shell.execute(
            message
        )