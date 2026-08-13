# Raspberry Pi Control Server

A lightweight, modular Python WebSocket server for controlling Raspberry Pi hardware from a React dashboard.

The server provides a single WebSocket API for:

- Digital GPIO
- PWM
- I²C
- Server-sent hardware events
- Device capability discovery
- Restricted remote shell
- Mock hardware backends for development and testing

The project is designed to run on a Raspberry Pi connected to a LAN and communicate with a React dashboard over WebSocket.

---

# Modules

The project is organized into independent modules so hardware implementations can be replaced or extended without changing the WebSocket API.

```text
raspi-control/
├── server.py
├── config.py
├── protocol.py
├── events.py
├── shell.py
│
├── gpio/
│   ├── __init__.py
│   ├── manager.py
│   ├── real.py
│   └── mock.py
│
└── i2c/
    ├── __init__.py
    ├── manager.py
    ├── real.py
    └── mock.py
```

## Module Responsibilities

### `server.py`

Main application entry point.

Responsible for:

- Starting the WebSocket server
- Accepting client connections
- Initializing hardware managers
- Managing connected clients

Start the server with:

```bash
python server.py
```

### `config.py`

Contains application configuration.

Typical configuration includes:

```text
HOST
PORT
I2C_BUS
PWM_FREQUENCY
MOCK_GPIO
I2C_MOCK
ALLOWED_SHELL_COMMANDS
```

Configuration can be provided through environment variables.

### `protocol.py`

Handles the WebSocket protocol.

It receives JSON requests such as:

```json
{
  "type": "pin",
  "action": "set",
  "pin": 18,
  "value": true
}
```

and dispatches them to the appropriate hardware module.

### `events.py`

Provides server-side event broadcasting.

For example, when a GPIO changes:

```json
{
  "type": "event",
  "event": "pin_changed",
  "data": {
    "pin": 18,
    "value": true
  }
}
```

All connected dashboard clients can receive the event.

### `shell.py`

Provides a restricted remote shell interface.

Only explicitly allowed commands should be executable.

Example configuration:

```python
ALLOWED_SHELL_COMMANDS = {
    "hostname",
    "uptime",
    "date",
    "uname",
}
```

Arbitrary shell execution should not be enabled on an unauthenticated WebSocket connection.

---

# GPIO Module

The GPIO module is divided into three layers:

```text
gpio/
├── manager.py
├── real.py
└── mock.py
```

### `gpio/manager.py`

Provides the common high-level GPIO API.

It handles:

- Digital output
- Digital input
- Toggle
- PWM
- PWM frequency
- PWM duty cycle

### `gpio/real.py`

Contains the actual Raspberry Pi GPIO implementation.

It is used when running on the Raspberry Pi.

### `gpio/mock.py`

Contains the development implementation.

It does not access physical GPIO hardware.

This allows the complete application to run on:

- Linux
- macOS
- Windows
- CI environments
- Developer machines

without a Raspberry Pi.

---

# I²C Module

The I²C module follows the same architecture:

```text
i2c/
├── manager.py
├── real.py
└── mock.py
```

### `i2c/manager.py`

Provides the common I²C API:

- Bus scanning
- Read byte
- Write byte
- Read register
- Write register
- Read block
- Write block

### `i2c/real.py`

Provides the physical I²C implementation using the Raspberry Pi I²C interface.

### `i2c/mock.py`

Provides an in-memory I²C implementation for development and testing.

The mock backend can simulate devices such as:

```text
0x48
0x50
```

Example initial registers:

```text
0x48 / 0x00 = 0x42
0x48 / 0x01 = 0x12
0x50 / 0x00 = 0xAA
```

---

# Requirements

## Development

For development without Raspberry Pi hardware:

- Python 3.10+
- pip
- WebSocket support

Install:

```bash
pip install websockets
```

Mock GPIO and I²C backends can then be used.

## Raspberry Pi

For real hardware:

- Raspberry Pi
- Raspberry Pi OS
- Python 3.10+
- GPIO access
- I²C enabled if I²C functionality is required

Install the Python dependencies:

```bash
pip install websockets gpiozero smbus2
```

For I²C diagnostics:

```bash
sudo apt install i2c-tools
```

---

# Install

## Clone the Repository

```bash
git clone <repository-url>
cd raspi-control
```

## Create a Virtual Environment

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

## Install Development Dependencies

```bash
pip install websockets
```

## Install Raspberry Pi Dependencies

On the Raspberry Pi:

```bash
pip install websockets gpiozero smbus2
```

---

# Setup

## Raspberry Pi I²C Setup

Enable I²C:

```bash
sudo raspi-config
```

Select:

```text
Interface Options
→ I2C
→ Enable
```

Reboot if required:

```bash
sudo reboot
```

Verify the I²C interface:

```bash
ls /dev/i2c*
```

Normally:

```text
/dev/i2c-1
```

Verify connected devices:

```bash
sudo apt install i2c-tools
i2cdetect -y 1
```

A device at address `0x48` should appear as:

```text
48
```

---

## Server Configuration

The server can be configured using environment variables.

| Variable | Default | Description |
|---|---:|---|
| `HOST` | `0.0.0.0` | WebSocket bind address |
| `PORT` | `8765` | WebSocket port |
| `I2C_BUS` | `1` | I²C bus number |
| `PWM_FREQUENCY` | `1000` | Default PWM frequency |
| `MOCK_GPIO` | disabled | Enable GPIO mock backend |
| `I2C_MOCK` | disabled | Enable I²C mock backend |

Example:

```bash
export HOST=0.0.0.0
export PORT=8765
export I2C_BUS=1
export PWM_FREQUENCY=1000
```

Start the server:

```bash
python server.py
```

---

# Development Setup

To run the server without Raspberry Pi hardware:

```bash
MOCK_GPIO=1 I2C_MOCK=1 python server.py
```

Example output:

```text
==================================================
Raspberry Pi Control Server
==================================================
WebSocket : 0.0.0.0:8765
GPIO      : MOCK
I2C       : MOCK (bus 1)
==================================================
[WS] Server ready
```

The dashboard can connect to:

```text
ws://localhost:8765
```

---

# Raspberry Pi Setup

On the Raspberry Pi:

```bash
source .venv/bin/activate
```

Start the server:

```bash
python server.py
```

Example:

```text
==================================================
Raspberry Pi Control Server
==================================================
WebSocket : 0.0.0.0:8765
GPIO      : REAL
I2C       : REAL (bus 1)
==================================================
[WS] Server ready
```

Find the Raspberry Pi IP:

```bash
hostname -I
```

For example:

```text
192.168.1.100
```

The React dashboard can connect to:

```text
ws://192.168.1.100:8765
```

---

# WebSocket API

All communication uses JSON messages.

General request:

```json
{
  "type": "...",
  "action": "..."
}
```

Successful response:

```json
{
  "ok": true
}
```

Error response:

```json
{
  "ok": false,
  "error": "Description of the error"
}
```

---

# Startup Request

After connecting, the dashboard should request the server configuration and capabilities.

```json
{
  "type": "startup"
}
```

Example response:

```json
{
  "ok": true,
  "type": "startup",
  "protocol": {
    "version": 1
  },
  "device": {
    "name": "raspberrypi",
    "platform": "Linux",
    "release": "6.x"
  },
  "capabilities": [
    "digital",
    "pwm",
    "read",
    "i2c",
    "shell"
  ],
  "pins": [
    17,
    18,
    22,
    23,
    24,
    25
  ],
  "pwm": {
    "default_frequency": 1000,
    "duty_cycle_min": 0.0,
    "duty_cycle_max": 1.0
  },
  "i2c": {
    "bus": 1,
    "mock": false
  }
}
```

The React application can use this information to build its interface dynamically.

---

# GPIO Examples

## Set GPIO

Turn GPIO 18 on:

```json
{
  "type": "pin",
  "action": "set",
  "pin": 18,
  "value": true
}
```

Turn it off:

```json
{
  "type": "pin",
  "action": "set",
  "pin": 18,
  "value": false
}
```

## Toggle GPIO

```json
{
  "type": "pin",
  "action": "toggle",
  "pin": 18
}
```

## Read GPIO

```json
{
  "type": "pin",
  "action": "read",
  "pin": 18
}
```

---

# PWM Examples

PWM uses a duty cycle between `0.0` and `1.0`.

```text
0.0  = 0%
0.25 = 25%
0.5  = 50%
0.75 = 75%
1.0  = 100%
```

## Set PWM

Set GPIO 18 to 50%:

```json
{
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.5
}
```

Set 75% at 1 kHz:

```json
{
  "type": "pin",
  "action": "pwm_set",
  "pin": 18,
  "duty_cycle": 0.75,
  "frequency": 1000
}
```

## Stop PWM

```json
{
  "type": "pin",
  "action": "pwm_stop",
  "pin": 18
}
```

---

# I²C Examples

I²C addresses are represented as decimal integers in JSON.

For example:

```text
0x48 = 72
0x50 = 80
```

## Scan the Bus

```json
{
  "type": "i2c",
  "action": "scan"
}
```

Example response:

```json
{
  "ok": true,
  "type": "i2c",
  "action": "scan",
  "bus": 1,
  "addresses": [
    72,
    80
  ]
}
```

## Read a Byte

```json
{
  "type": "i2c",
  "action": "read_byte",
  "address": 72
}
```

## Write a Byte

```json
{
  "type": "i2c",
  "action": "write_byte",
  "address": 72,
  "value": 255
}
```

## Read a Register

Read register `0x00` from device `0x48`:

```json
{
  "type": "i2c",
  "action": "read_register",
  "address": 72,
  "register": 0
}
```

Example response:

```json
{
  "ok": true,
  "type": "i2c",
  "action": "read_register",
  "bus": 1,
  "address": 72,
  "register": 0,
  "value": 66
}
```

`66` is hexadecimal `0x42`.

## Write a Register

```json
{
  "type": "i2c",
  "action": "write_register",
  "address": 72,
  "register": 16,
  "value": 255
}
```

## Read a Block

```json
{
  "type": "i2c",
  "action": "read_block",
  "address": 80,
  "register": 0,
  "length": 8
}
```

## Write a Block

```json
{
  "type": "i2c",
  "action": "write_block",
  "address": 80,
  "register": 16,
  "data": [
    1,
    2,
    3,
    4
  ]
}
```

---

# Events

The server can send asynchronous events to connected clients.

Event format:

```json
{
  "type": "event",
  "event": "...",
  "data": {}
}
```

## GPIO Event

```json
{
  "type": "event",
  "event": "pin_changed",
  "data": {
    "pin": 18,
    "value": true
  }
}
```

## PWM Event

```json
{
  "type": "event",
  "event": "pwm_changed",
  "data": {
    "pin": 18,
    "duty_cycle": 0.5,
    "frequency": 1000
  }
}
```

## I²C Register Event

```json
{
  "type": "event",
  "event": "i2c_register_changed",
  "data": {
    "bus": 1,
    "address": 72,
    "register": 16,
    "value": 255
  }
}
```

## I²C Block Event

```json
{
  "type": "event",
  "event": "i2c_block_changed",
  "data": {
    "bus": 1,
    "address": 80,
    "register": 16,
    "data": [
      1,
      2,
      3,
      4
    ]
  }
}
```

---

# React Example

A minimal client can be implemented with the browser WebSocket API.

```javascript
const ws = new WebSocket(
    "ws://192.168.1.100:8765"
);

ws.onopen = () => {
    console.log("Connected");

    ws.send(JSON.stringify({
        type: "startup"
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(
        event.data
    );

    if (message.type === "event") {
        handleEvent(
            message.event,
            message.data
        );

        return;
    }

    console.log(
        "Server response:",
        message
    );
};

ws.onclose = () => {
    console.log("Disconnected");
};

ws.onerror = (error) => {
    console.error(
        "WebSocket error:",
        error
    );
};

function setPin(pin, value) {
    ws.send(JSON.stringify({
        type: "pin",
        action: "set",
        pin,
        value
    }));
}

function togglePin(pin) {
    ws.send(JSON.stringify({
        type: "pin",
        action: "toggle",
        pin
    }));
}

function setPwm(
    pin,
    dutyCycle,
    frequency = 1000
) {
    ws.send(JSON.stringify({
        type: "pin",
        action: "pwm_set",
        pin,
        duty_cycle: dutyCycle,
        frequency
    }));
}

function stopPwm(pin) {
    ws.send(JSON.stringify({
        type: "pin",
        action: "pwm_stop",
        pin
    }));
}

function scanI2C() {
    ws.send(JSON.stringify({
        type: "i2c",
        action: "scan"
    }));
}

function readI2CRegister(
    address,
    register
) {
    ws.send(JSON.stringify({
        type: "i2c",
        action: "read_register",
        address,
        register
    }));
}

function writeI2CRegister(
    address,
    register,
    value
) {
    ws.send(JSON.stringify({
        type: "i2c",
        action: "write_register",
        address,
        register,
        value
    }));
}

function handleEvent(event, data) {
    switch (event) {
        case "pin_changed":
            console.log(
                "GPIO changed:",
                data
            );
            break;

        case "pwm_changed":
            console.log(
                "PWM changed:",
                data
            );
            break;

        case "i2c_register_changed":
            console.log(
                "I2C register changed:",
                data
            );
            break;

        case "i2c_block_changed":
            console.log(
                "I2C block changed:",
                data
            );
            break;

        default:
            console.log(
                "Unknown event:",
                event,
                data
            );
    }
}
```

---

# Complete Example

Assume:

- Raspberry Pi IP: `192.168.1.100`
- WebSocket port: `8765`
- LED connected to GPIO 18
- I²C device connected at `0x48`

## 1. Start the server

On the Raspberry Pi:

```bash
source .venv/bin/activate
python server.py
```

## 2. Connect from React

```javascript
const ws = new WebSocket(
    "ws://192.168.1.100:8765"
);
```

## 3. Request capabilities

```javascript
ws.send(JSON.stringify({
    type: "startup"
}));
```

## 4. Turn on the LED

```javascript
ws.send(JSON.stringify({
    type: "pin",
    action: "set",
    pin: 18,
    value: true
}));
```

## 5. Set LED brightness to 50%

```javascript
ws.send(JSON.stringify({
    type: "pin",
    action: "pwm_set",
    pin: 18,
    duty_cycle: 0.5,
    frequency: 1000
}));
```

## 6. Scan the I²C bus

```javascript
ws.send(JSON.stringify({
    type: "i2c",
    action: "scan"
}));
```

## 7. Read register `0x00`

```javascript
ws.send(JSON.stringify({
    type: "i2c",
    action: "read_register",
    address: 0x48,
    register: 0x00
}));
```

## 8. Write register `0x10`

```javascript
ws.send(JSON.stringify({
    type: "i2c",
    action: "write_register",
    address: 0x48,
    register: 0x10,
    value: 255
}));
```

---

# Remote Shell

The server supports a restricted shell interface.

Example configuration:

```python
ALLOWED_SHELL_COMMANDS = {
    "hostname",
    "uptime",
    "date",
    "uname",
}
```

Example request:

```json
{
  "type": "shell",
  "command": "hostname"
}
```

With arguments:

```json
{
  "type": "shell",
  "command": "uname",
  "args": [
    "-a"
  ]
}
```

The shell implementation should:

- Validate commands against an allowlist
- Use `shell=False`
- Avoid arbitrary command strings
- Never expose unrestricted shell access without authentication

---

# Security

The server is intended primarily for use on a trusted LAN.

Do not expose the WebSocket endpoint directly to the public Internet.

The remote shell functionality makes this especially important.

Recommended architecture:

```text
                 Internet
                    │
                    X
                    │
                Firewall
                    │
                    ▼
                   LAN
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
   React Dashboard      Raspberry Pi
                              │
                              │
                         WebSocket
                           :8765
```

If remote Internet access is required, add:

- Authentication
- Authorization
- TLS/WSS
- Command restrictions
- Rate limiting
- Network-level access controls

before exposing the service externally.

---

# Troubleshooting

## WebSocket Connection Refused

Check that the server is running:

```bash
python server.py
```

Check port `8765`:

```bash
ss -ltnp | grep 8765
```

Find the Raspberry Pi IP:

```bash
hostname -I
```

Connect using:

```text
ws://<raspberry-pi-ip>:8765
```

---

## I²C Bus Not Found

Check:

```bash
ls /dev/i2c*
```

If `/dev/i2c-1` does not exist, enable I²C:

```bash
sudo raspi-config
```

Then:

```bash
i2cdetect -y 1
```

---

## Test Without Hardware

Run:

```bash
MOCK_GPIO=1 I2C_MOCK=1 python server.py
```

Connect the React dashboard to:

```text
ws://localhost:8765
```

---

# Extending the Server

New hardware modules should follow the same pattern:

```text
device/
├── __init__.py
├── manager.py
├── real.py
└── mock.py
```

For example, an SPI module could be added as:

```text
spi/
├── __init__.py
├── manager.py
├── real.py
└── mock.py
```

The WebSocket protocol should communicate with the manager rather than directly with hardware libraries.

This keeps the architecture modular and makes testing easier.

---

# Protocol Version

Current protocol version:

```text
1
```

The version is returned by the startup request:

```json
{
  "protocol": {
    "version": 1
  }
}
```

Increment the protocol version when making breaking changes to the WebSocket API.

---

# License

Add the appropriate project license here.