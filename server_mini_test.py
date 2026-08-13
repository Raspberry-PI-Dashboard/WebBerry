"""
__________________________________________
how to run:
pip install websockets
python server_mini_test.py
__________________________________________


__________________________________________
force mock mode:
MOCK_GPIO=1 python server_mini_test.py
__________________________________________


__________________________________________
on rasberry:
pip install websockets gpiozero
python server.py
__________________________________________


__________________________________________
on dashboard:

const ws = new WebSocket("ws://raspberrypi.local:8765");

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "startup"
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "startup") {
    console.log("Device:", message.device);
    console.log("Pins:", message.pins);

    // Initialize your React state here.
  }
};
__________________________________________
"""

import asyncio
import json
import os
import platform
import subprocess

import websockets


# ============================================================================
# Configuration
# ============================================================================

HOST = "0.0.0.0"
PORT = 8765

PROTOCOL_VERSION = 1
DEFAULT_PWM_FREQUENCY = 1000

# BCM GPIO numbering.
ALLOWED_PINS = {
    17,
    18,
    22,
    23,
    24,
    25,
}


# ============================================================================
# GPIO backend selection
# ============================================================================

FORCE_MOCK = os.getenv("MOCK_GPIO", "").lower() in {
    "1",
    "true",
    "yes",
}

try:
    if FORCE_MOCK:
        raise ImportError("Mock GPIO requested")

    from gpiozero import (
        DigitalInputDevice,
        DigitalOutputDevice,
        PWMOutputDevice,
    )

    MOCK_GPIO = False

except ImportError:
    MOCK_GPIO = True


# ============================================================================
# Mock GPIO implementation
# ============================================================================

class MockOutput:
    def __init__(self, pin, initial_value=False):
        self.pin = pin
        self.value = bool(initial_value)

        print(
            f"[MOCK] GPIO {pin} output initialized "
            f"value={self.value}"
        )

    def toggle(self):
        self.value = not self.value

        print(
            f"[MOCK] GPIO {self.pin} toggled "
            f"value={self.value}"
        )

    def close(self):
        pass


class MockInput:
    def __init__(self, pin):
        self.pin = pin
        self.value = False

        print(
            f"[MOCK] GPIO {pin} input initialized"
        )

    def close(self):
        pass


class MockPWM:
    def __init__(
        self,
        pin,
        initial_value=0,
        frequency=DEFAULT_PWM_FREQUENCY,
    ):
        self.pin = pin
        self.value = float(initial_value)
        self.frequency = int(frequency)

        print(
            f"[MOCK] PWM GPIO {pin} initialized "
            f"duty={self.value} "
            f"frequency={self.frequency}"
        )

    def close(self):
        pass


# ============================================================================
# GPIO state
# ============================================================================

outputs = {}
inputs = {}
pwm_outputs = {}


def validate_pin(pin):
    try:
        pin = int(pin)
    except (TypeError, ValueError):
        raise ValueError("Invalid GPIO pin")

    if pin not in ALLOWED_PINS:
        raise ValueError(
            f"GPIO {pin} is not allowed"
        )

    return pin


def get_output(pin):
    pin = validate_pin(pin)

    if pin not in outputs:
        if MOCK_GPIO:
            outputs[pin] = MockOutput(
                pin,
                initial_value=False,
            )
        else:
            outputs[pin] = DigitalOutputDevice(
                pin,
                initial_value=False,
            )

    return outputs[pin]


def get_input(pin):
    pin = validate_pin(pin)

    if pin not in inputs:
        if MOCK_GPIO:
            inputs[pin] = MockInput(pin)
        else:
            inputs[pin] = DigitalInputDevice(pin)

    return inputs[pin]


def get_pwm(pin):
    pin = validate_pin(pin)

    if pin not in pwm_outputs:
        if MOCK_GPIO:
            pwm_outputs[pin] = MockPWM(
                pin,
                initial_value=0,
                frequency=DEFAULT_PWM_FREQUENCY,
            )
        else:
            pwm_outputs[pin] = PWMOutputDevice(
                pin,
                initial_value=0,
                frequency=DEFAULT_PWM_FREQUENCY,
            )

    return pwm_outputs[pin]


# ============================================================================
# Startup state
# ============================================================================

def get_startup_state():
    pins = []

    for pin in sorted(ALLOWED_PINS):
        digital_value = False

        pwm_value = 0.0
        pwm_frequency = DEFAULT_PWM_FREQUENCY
        pwm_active = False

        # Existing digital output state
        if pin in outputs:
            digital_value = bool(
                outputs[pin].value
            )

        # Existing PWM state
        if pin in pwm_outputs:
            pwm = pwm_outputs[pin]

            pwm_value = float(
                pwm.value
            )

            pwm_frequency = int(
                pwm.frequency
            )

            pwm_active = pwm_value > 0

        pins.append({
            "pin": pin,

            "digital": {
                "value": digital_value,
            },

            "pwm": {
                "active": pwm_active,
                "duty_cycle": pwm_value,
                "frequency": pwm_frequency,
            },
        })

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
            "shell",
        ],

        "pwm": {
            "default_frequency": DEFAULT_PWM_FREQUENCY,
            "duty_cycle_min": 0.0,
            "duty_cycle_max": 1.0,
        },

        "pins": pins,
    }


# ============================================================================
# Pin API
# ============================================================================

def handle_pin(message):
    action = message.get("action")

    if "pin" not in message:
        raise ValueError("Missing pin")

    pin = validate_pin(
        message["pin"]
    )

    # ------------------------------------------------------------------------
    # Digital output
    # ------------------------------------------------------------------------

    if action == "set":

        if "value" not in message:
            raise ValueError("Missing value")

        value = bool(
            message["value"]
        )

        output = get_output(pin)
        output.value = value

        if MOCK_GPIO:
            print(
                f"[MOCK] GPIO {pin} -> "
                f"{'HIGH' if value else 'LOW'}"
            )

        return {
            "ok": True,
            "type": "pin",
            "action": "set",
            "pin": pin,
            "value": bool(
                output.value
            ),
        }

    # ------------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------------

    if action == "toggle":

        output = get_output(pin)
        output.toggle()

        return {
            "ok": True,
            "type": "pin",
            "action": "toggle",
            "pin": pin,
            "value": bool(
                output.value
            ),
        }

    # ------------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------------

    if action == "read":

        input_pin = get_input(pin)

        return {
            "ok": True,
            "type": "pin",
            "action": "read",
            "pin": pin,
            "value": bool(
                input_pin.value
            ),
        }

    # ------------------------------------------------------------------------
    # PWM set
    # ------------------------------------------------------------------------

    if action == "pwm_set":

        if "duty_cycle" not in message:
            raise ValueError(
                "Missing duty_cycle"
            )

        duty_cycle = float(
            message["duty_cycle"]
        )

        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError(
                "duty_cycle must be between "
                "0.0 and 1.0"
            )

        frequency = int(
            message.get(
                "frequency",
                DEFAULT_PWM_FREQUENCY,
            )
        )

        if frequency <= 0:
            raise ValueError(
                "frequency must be positive"
            )

        pwm = get_pwm(pin)

        pwm.frequency = frequency
        pwm.value = duty_cycle

        if MOCK_GPIO:
            print(
                f"[MOCK] PWM GPIO {pin} -> "
                f"duty={duty_cycle:.3f} "
                f"frequency={frequency}Hz"
            )

        return {
            "ok": True,
            "type": "pwm",
            "action": "pwm_set",
            "pin": pin,
            "duty_cycle": float(
                pwm.value
            ),
            "frequency": int(
                pwm.frequency
            ),
        }

    # ------------------------------------------------------------------------
    # PWM stop
    # ------------------------------------------------------------------------

    if action == "pwm_stop":

        pwm = get_pwm(pin)
        pwm.value = 0

        if MOCK_GPIO:
            print(
                f"[MOCK] PWM GPIO {pin} stopped"
            )

        return {
            "ok": True,
            "type": "pwm",
            "action": "pwm_stop",
            "pin": pin,
            "duty_cycle": 0.0,
            "frequency": int(
                pwm.frequency
            ),
        }

    raise ValueError(
        f"Unknown pin action: {action}"
    )


# ============================================================================
# Restricted shell
# ============================================================================

ALLOWED_COMMANDS = {
    "hostname",
    "uptime",
    "date",
    "uname",
}


async def handle_shell(message):
    command = message.get("command")

    if not command:
        raise ValueError(
            "Missing command"
        )

    if command not in ALLOWED_COMMANDS:
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
        result = subprocess.run(
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


# ============================================================================
# WebSocket handler
# ============================================================================

async def client_handler(websocket):
    client = websocket.remote_address

    print(
        f"Client connected: {client}"
    )

    try:
        async for raw_message in websocket:

            try:
                message = json.loads(
                    raw_message
                )

                if not isinstance(message, dict):
                    raise ValueError(
                        "Message must be a JSON object"
                    )

                message_type = message.get(
                    "type"
                )

                # ------------------------------------------------------------
                # Startup
                # ------------------------------------------------------------

                if message_type == "startup":

                    response = (
                        get_startup_state()
                    )

                # ------------------------------------------------------------
                # Ping
                # ------------------------------------------------------------

                elif message_type == "ping":

                    response = {
                        "ok": True,
                        "type": "pong",
                    }

                # ------------------------------------------------------------
                # GPIO
                # ------------------------------------------------------------

                elif message_type == "pin":

                    response = handle_pin(
                        message
                    )

                # ------------------------------------------------------------
                # Shell
                # ------------------------------------------------------------

                elif message_type == "shell":

                    response = await handle_shell(
                        message
                    )

                else:

                    raise ValueError(
                        f"Unknown message type: "
                        f"{message_type}"
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

        print(
            f"Client disconnected: {client}"
        )


# ============================================================================
# Cleanup
# ============================================================================

def cleanup():

    for device in outputs.values():
        device.close()

    for device in inputs.values():
        device.close()

    for device in pwm_outputs.values():
        device.close()


# ============================================================================
# Server
# ============================================================================

async def main():

    mode = (
        "MOCK GPIO"
        if MOCK_GPIO
        else "RASPBERRY PI GPIO"
    )

    print("=" * 60)
    print("Raspberry Pi WebSocket GPIO Server")
    print("=" * 60)
    print(f"Protocol : {PROTOCOL_VERSION}")
    print(f"Mode     : {mode}")
    print(f"Host     : {HOST}")
    print(f"Port     : {PORT}")
    print(f"Pins     : {sorted(ALLOWED_PINS)}")
    print("=" * 60)

    try:

        async with websockets.serve(
            client_handler,
            HOST,
            PORT,
        ):

            print(
                "WebSocket server ready"
            )

            await asyncio.Future()

    finally:

        cleanup()


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\nServer stopped"
        )