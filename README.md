# Raspberry Pi WebSocket Gateway

A lightweight Python WebSocket gateway for communicating with a Raspberry Pi and controlling a persistent Bash shell over a WebSocket connection.

The gateway uses **JSON messages over WebSocket**. It provides connection status, health checks, connection information, and an interactive shell channel.

For UI, see [Vigilant Carnival](https://github.com/Raspberry-PI-Dashboard/vigilant-carnival)

## Features

* Persistent WebSocket connections
* JSON-based application protocol
* Automatic WebSocket ping/pong keepalive
* Connection status messages
* Connection information
* Persistent Bash shell per connected client
* Real-time shell output
* Graceful server shutdown
* Async implementation using `asyncio`

## Architecture

```text
WebSocket Client
       │
       │ ws://<raspberry-pi-ip>:8765
       ▼
┌──────────────────────┐
│   WebSocket Gateway  │
│                      │
│  JSON Application    │
│       Protocol       │
│          │           │
│          ▼           │
│     ShellSession     │
│          │           │
│          ▼           │
│        /bin/bash     │
└──────────────────────┘
```

Each WebSocket client receives its own `ClientSession` and, when requested, its own Bash process.

## Requirements

* Python 3.10 or newer
* Linux/Raspberry Pi environment
* Network access between the client and Raspberry Pi
* Python package:

```bash
pip install websockets
```

## Running the Gateway

Start the server with:

```bash
python server.py
```

or, depending on the project entry point:

```bash
python gateway.py
```

The gateway listens on:

```text
ws://0.0.0.0:8765
```

A client should connect using the Raspberry Pi's actual IP address:

```text
ws://192.168.1.100:8765
```

Replace the address with the Raspberry Pi's address on your network.

## Protocol

The application protocol consists of JSON messages sent through the WebSocket connection.

### Connection

Immediately after connecting, the server sends:

```json
{
  "type": "connected",
  "timestamp": "2026-08-24T16:46:00+02:00",
  "message": "Raspberry Pi Gateway ready"
}
```

### Ping

The client can send:

```json
{
  "type": "ping"
}
```

The server responds with:

```json
{
  "type": "pong",
  "timestamp": "2026-08-24T16:46:00+02:00"
}
```

This is an **application-level ping**. The WebSocket library also has its own protocol-level keepalive configured with a 20-second ping interval and 30-second timeout.

### Connection Information

Send:

```json
{
  "type": "info"
}
```

The server responds with:

```json
{
  "type": "info",
  "connected_at": "2026-08-24T16:40:00+00:00"
}
```

## Interactive Shell

### Start a Shell

Send:

```json
{
  "type": "shell_start"
}
```

The gateway starts:

```text
/bin/bash
```

and responds:

```json
{
  "type": "shell_started"
}
```

Only one shell is created per WebSocket session.

### Send Shell Input

After the shell has started:

```json
{
  "type": "shell_input",
  "data": "uname -a"
}
```

The command is written to Bash's standard input.

The server forwards Bash output as:

```json
{
  "type": "shell_output",
  "data": "Linux raspberrypi 6.x.x ...\n"
}
```

Output is sent line-by-line.

Standard error is redirected to standard output, so command errors are also delivered as `shell_output` messages.

For example:

```json
{
  "type": "shell_input",
  "data": "ls /does-not-exist"
}
```

may produce:

```json
{
  "type": "shell_output",
  "data": "ls: cannot access '/does-not-exist': No such file or directory\n"
}
```

## Message Reference

### Client → Server

| Message       | Description                    |
| ------------- | ------------------------------ |
| `ping`        | Application-level health check |
| `info`        | Request connection information |
| `shell_start` | Start the Bash session         |
| `shell_input` | Send input to Bash             |

### Server → Client

| Message           | Description                         |
| ----------------- | ----------------------------------- |
| `connected`       | WebSocket session initialized       |
| `pong`            | Response to `ping`                  |
| `info`            | Connection information              |
| `shell_started`   | Bash session successfully started   |
| `shell_output`    | Output produced by Bash             |
| `error`           | Invalid request or processing error |
| `server_shutdown` | Gateway is shutting down            |

## Error Handling

Unknown message types produce:

```json
{
  "type": "error",
  "message": "Unknown command example"
}
```

Attempting to send shell input before starting a shell produces:

```json
{
  "type": "error",
  "message": "Shell not started"
}
```

Attempting to start a second shell for the same connection produces:

```json
{
  "type": "error",
  "message": "Shell already running"
}
```

## Connection Lifecycle

```text
Client
  │
  │ WebSocket connection
  ▼
Gateway
  │
  │ connected
  ▼
Client
  │
  ├── ping ────────────────► Gateway
  │◄──────────── pong ──────┤
  │
  ├── info ────────────────► Gateway
  │◄──────────── info ──────┤
  │
  ├── shell_start ─────────► Gateway
  │◄──── shell_started ─────┤
  │
  ├── shell_input ─────────► Bash
  │◄──── shell_output ──────┤
  │
  │
  └── disconnect
           │
           ▼
      Bash terminated
```

## Configuration

The gateway currently uses these settings:

```python
HOST = "0.0.0.0"
PORT = 8765
PING_INTERVAL = 20
PING_TIMEOUT = 30
```

### Host

`0.0.0.0` makes the server listen on all available network interfaces.

### Port

The default WebSocket port is `8765`.

### Keepalive

The WebSocket library sends protocol-level pings every 20 seconds and considers a connection unhealthy if the expected response is not received within 30 seconds.

## Graceful Shutdown

The gateway handles:

* `SIGINT`
* `SIGTERM`

When shutdown begins, connected clients receive:

```json
{
  "type": "server_shutdown"
}
```

The WebSocket server then stops accepting connections and waits for the server to close.

## Security Warning

**Do not expose this gateway directly to the public Internet.**

The current implementation provides no authentication or authorization. Any client capable of connecting to the WebSocket endpoint can request a Bash shell and execute commands with the privileges of the gateway process.

For a real deployment, consider adding:

* Authentication
* Authorization
* TLS (`wss://`)
* Network/firewall restrictions
* Command restrictions or sandboxing
* Connection limits
* Audit logging
* Per-user permissions
* Session timeouts

The safest deployment is generally to keep the gateway on a trusted/private network and restrict access with a firewall or VPN.

## Project Structure

A typical project structure is:

```text
project/
├── gateway.py
├── client.py
├── shell.py
└── server.py
```

The responsibilities are separated as follows:

### `gateway.py`

WebSocket server, client management, lifecycle, and shutdown handling.

### `client.py`

Represents an individual WebSocket client and dispatches application messages.

### `shell.py`

Manages the Bash subprocess and streams its output back through WebSocket.

### `server.py`

Project-level server entry point, if used by the application.

## Example Client

A minimal Python client can use the `websockets` package:

```python
import asyncio
import json
import websockets


async def main():
    uri = "ws://192.168.1.100:8765"

    async with websockets.connect(uri) as websocket:
        message = await websocket.recv()
        print(message)

        await websocket.send(json.dumps({
            "type": "shell_start"
        }))

        print(await websocket.recv())

        await websocket.send(json.dumps({
            "type": "shell_input",
            "data": "uname -a"
        }))

        while True:
            message = json.loads(await websocket.recv())

            if message["type"] == "shell_output":
                print(message["data"], end="")


asyncio.run(main())
```

Replace `192.168.1.100` with the Raspberry Pi's address.

## License

Add the project's license information here.

## Status

This project is a lightweight prototype/gateway implementation. Before using it in a production or Internet-facing environment, authentication, encryption, access control, and shell isolation should be implemented.

