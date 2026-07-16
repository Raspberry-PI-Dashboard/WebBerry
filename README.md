# WebBerry Gateway

WebBerry is a lightweight asynchronous WebSocket gateway designed for remote communication and control of embedded devices such as Raspberry Pi.

The gateway provides a persistent WebSocket connection where clients can send commands, receive responses, and interact with remote services.

## Features

- Async WebSocket server powered by `websockets`
- Multiple simultaneous client connections
- Client session management
- Connection welcome handshake
- Ping/Pong health checks
- Server information requests
- Remote shell sessions
- Graceful shutdown handling
- Async test suite with `pytest`

## Requirements

- Python >= 3.12
- websockets
- pytest
- pytest-asyncio

Install dependencies:

```bash
pip install -r requirements.txt
```

## Project Structure

```
WebBerry/
│
├── gateway.py
├── client.py
├── shell.py
├── requirements.txt
├── README.md
│
└── tests/
    ├── test_connection.py
    ├── test_ping.py
    └── test_shell.py
```

## Running the Gateway

Start the server:

```bash
python gateway.py
```

The WebSocket server listens on:

```
ws://0.0.0.0:8765
```

Example output:

```
Gateway running ws://0.0.0.0:8765
```

## WebSocket Protocol

After a client connects, the gateway sends:

```json
{
  "type": "connected",
  "timestamp": "2026-07-16T15:00:00",
  "message": "Raspberry Pi Gateway ready"
}
```

## Commands

### Ping

Check connection status.

Request:

```json
{
  "type": "ping"
}
```

Response:

```json
{
  "type": "pong",
  "timestamp": "2026-07-16T15:00:00"
}
```

---

### Server Information

Request:

```json
{
  "type": "info"
}
```

Response:

```json
{
  "type": "info",
  "connected_at": "2026-07-16T15:00:00"
}
```

Returns session information for the connected client.

---

### Start Remote Shell

Request:

```json
{
  "type": "shell_start"
}
```

Starts an interactive shell session.

---

### Send Shell Command

Request:

```json
{
  "type": "shell_input",
  "data": "ls -la"
}
```

The command is executed remotely and the output is returned through the WebSocket channel.

---

## Client Lifecycle

When a client connects:

1. A new `ClientSession` is created.
2. The gateway sends a connection message.
3. Incoming JSON messages are processed asynchronously.
4. Commands are routed to the correct handler.

When a client disconnects:

- The shell session is closed.
- Resources are released.
- The client is removed from the active sessions list.

## Shutdown Handling

The gateway supports clean shutdown through:

- `SIGINT`
- `SIGTERM`

Shutdown sequence:

1. Notify connected clients.
2. Stop accepting new connections.
3. Close the WebSocket server.
4. Release resources.

## Running Tests

Run:

```bash
pytest -v
```

Tests include:

- WebSocket connection test
- Ping/Pong communication test
- Remote shell test

Expected result:

```
tests/test_connection.py::test_connection PASSED
tests/test_ping.py::test_ping PASSED
tests/test_shell.py::test_shell PASSED
```

## Roadmap

Future improvements:

- Device identification
- Remote telemetry
- Web dashboard

Nice to have:

- Authentication system
- Device Identification

## License

MIT License