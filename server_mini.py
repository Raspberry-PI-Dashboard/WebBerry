"""
install deps:
python3 -m pip install websockets gpiozero


api examples:
Digital ON
{
  "type": "pin",
  "action": "set",
  "pin": 17,
  "value": true
}

Digital OFF
{
  "type": "pin",
  "action": "set",
  "pin": 17,
  "value": false
}

Toggle
{
  "type": "pin",
  "action": "toggle",
  "pin": 17
}

Read
{
  "type": "pin",
  "action": "read",
  "pin": 17
}

PWM 50%
{
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.5
}

PWM 25% at 2 kHz
{
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.25,
  "frequency": 2000
}

Stop PWM
{
  "type": "pin",
  "action": "pwm_stop",
  "pin": 18
}

Shell
{
  "type": "shell",
  "command": "uptime",
  "args": []
}
"""

import asyncio
import json
import subprocess

import websockets
from gpiozero import (
    DigitalInputDevice,
    DigitalOutputDevice,
    PWMOutputDevice,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST = "0.0.0.0"
PORT = 8765

# BCM GPIO numbering.
# Only these pins can be accessed through the API.
ALLOWED_PINS = {
    17,
    18,
    22,
    23,
    24,
    25,
}

DEFAULT_PWM_FREQUENCY = 1000


# ---------------------------------------------------------------------------
# GPIO state
# ---------------------------------------------------------------------------

outputs = {}
inputs = {}
pwm_outputs = {}


def validate_pin(pin):
    pin = int(pin)

    if pin not in ALLOWED_PINS:
        raise ValueError(f"GPIO {pin} is not allowed")

    return pin


def get_output(pin):
    pin = validate_pin(pin)

    if pin not in outputs:
        outputs[pin] = DigitalOutputDevice(
            pin,
            initial_value=False,
        )

    return outputs[pin]


def get_input(pin):
    pin = validate_pin(pin)

    if pin not in inputs:
        inputs[pin] = DigitalInputDevice(pin)

    return inputs[pin]


def get_pwm(pin):
    pin = validate_pin(pin)

    if pin not in pwm_outputs:
        pwm_outputs[pin] = PWMOutputDevice(
            pin,
            initial_value=0,
            frequency=DEFAULT_PWM_FREQUENCY,
        )

    return pwm_outputs[pin]


# ---------------------------------------------------------------------------
# GPIO API
# ---------------------------------------------------------------------------

def handle_pin(message):
    action = message.get("action")

    if "pin" not in message:
        raise ValueError("Missing pin")

    pin = validate_pin(message["pin"])

    # -----------------------------------------------------------------------
    # Digital output
    # -----------------------------------------------------------------------

    if action == "set":
        if "value" not in message:
            raise ValueError("Missing value")

        value = bool(message["value"])

        output = get_output(pin)
        output.value = value

        return {
            "ok": True,
            "type": "pin",
            "action": "set",
            "pin": pin,
            "value": bool(output.value),
        }

    # -----------------------------------------------------------------------
    # Toggle digital output
    # -----------------------------------------------------------------------

    if action == "toggle":
        output = get_output(pin)
        output.toggle()

        return {
            "ok": True,
            "type": "pin",
            "action": "toggle",
            "pin": pin,
            "value": bool(output.value),
        }

    # -----------------------------------------------------------------------
    # Read digital input
    # -----------------------------------------------------------------------

    if action == "read":
        input_pin = get_input(pin)

        return {
            "ok": True,
            "type": "pin",
            "action": "read",
            "pin": pin,
            "value": bool(input_pin.value),
        }

    # -----------------------------------------------------------------------
    # PWM
    # -----------------------------------------------------------------------

    if action == "pwm_set":
        if "duty_cycle" not in message:
            raise ValueError("Missing duty_cycle")

        duty_cycle = float(message["duty_cycle"])

        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError(
                "duty_cycle must be between 0.0 and 1.0"
            )

        frequency = int(
            message.get(
                "frequency",
                DEFAULT_PWM_FREQUENCY,
            )
        )

        if frequency <= 0:
            raise ValueError("frequency must be positive")

        pwm = get_pwm(pin)

        pwm.frequency = frequency
        pwm.value = duty_cycle

        return {
            "ok": True,
            "type": "pwm",
            "action": "pwm_set",
            "pin": pin,
            "duty_cycle": float(pwm.value),
            "frequency": int(pwm.frequency),
        }

    # -----------------------------------------------------------------------
    # Stop PWM
    # -----------------------------------------------------------------------

    if action == "pwm_stop":
        pwm = get_pwm(pin)
        pwm.value = 0

        return {
            "ok": True,
            "type": "pwm",
            "action": "pwm_stop",
            "pin": pin,
            "duty_cycle": 0.0,
            "frequency": int(pwm.frequency),
        }

    raise ValueError(f"Unknown pin action: {action}")


# ---------------------------------------------------------------------------
# Restricted shell API
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS = {
    "hostname",
    "uptime",
    "date",
    "uname",
    "vcgencmd",
}


async def handle_shell(message):
    command = message.get("command")

    if not command:
        raise ValueError("Missing command")

    if command not in ALLOWED_COMMANDS:
        raise ValueError(
            f"Command not allowed: {command}"
        )

    args = message.get("args", [])

    if not isinstance(args, list):
        raise ValueError("args must be a list")

    argv = [command] + [str(arg) for arg in args]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("Command timed out")

    return {
        "ok": result.returncode == 0,
        "type": "shell",
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

async def client_handler(websocket):
    client = websocket.remote_address

    print(f"Client connected: {client}")

    try:
        async for raw_message in websocket:

            try:
                message = json.loads(raw_message)

                if not isinstance(message, dict):
                    raise ValueError(
                        "Message must be a JSON object"
                    )

                message_type = message.get("type")

                # -----------------------------------------------------------
                # Ping
                # -----------------------------------------------------------

                if message_type == "ping":
                    response = {
                        "ok": True,
                        "type": "pong",
                    }

                # -----------------------------------------------------------
                # GPIO
                # -----------------------------------------------------------

                elif message_type == "pin":
                    response = handle_pin(message)

                # -----------------------------------------------------------
                # Shell
                # -----------------------------------------------------------

                elif message_type == "shell":
                    response = await handle_shell(message)

                else:
                    raise ValueError(
                        f"Unknown message type: {message_type}"
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
        print(f"Client disconnected: {client}")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup():
    for device in outputs.values():
        device.close()

    for device in inputs.values():
        device.close()

    for device in pwm_outputs.values():
        device.close()


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

async def main():
    print(
        f"Starting Raspberry Pi WebSocket server "
        f"on {HOST}:{PORT}"
    )

    try:
        async with websockets.serve(
            client_handler,
            HOST,
            PORT,
        ):
            print("Server ready")
            await asyncio.Future()

    finally:
        cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")