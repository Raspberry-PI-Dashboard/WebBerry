import os


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8765"))

PROTOCOL_VERSION = 1

DEFAULT_PWM_FREQUENCY = int(
    os.getenv("PWM_FREQUENCY", "1000")
)

ALLOWED_PINS = {
    17,
    18,
    22,
    23,
    24,
    25,
}

MOCK_GPIO = os.getenv("MOCK_GPIO", "").lower() in {
    "1",
    "true",
    "yes",
}

ALLOWED_SHELL_COMMANDS = {
    "hostname",
    "uptime",
    "date",
    "uname",
}