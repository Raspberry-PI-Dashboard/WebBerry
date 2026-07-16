# Raspberry Pi WebSocket Gateway

A lightweight and extensible WebSocket gateway for Raspberry Pi devices.

The project provides a persistent WebSocket connection between a web dashboard and a Raspberry Pi, enabling remote communication, command execution, and future hardware integrations.

The architecture is designed for edge devices where reliability, remote updates, and modular expansion are important.

---

## Features

✅ **Stable WebSocket Server**

* Async Python WebSocket server
* Multiple simultaneous clients
* Automatic connection handling
* Ping/pong keep-alive mechanism

✅ **Remote Shell Access**

* Open a terminal session through WebSocket
* Execute Linux commands remotely
* Stream command output back to the client

✅ **Modular Architecture**

* WebSocket transport separated from features
* Client session management
* Ready for future plugins

✅ **Deployment Ready**

* Designed to run as a systemd service
* Supports remote update workflows
* Suitable for headless Raspberry Pi deployments

---

# Architecture

```
                 Browser Dashboard
                        |
                        |
                   WebSocket
                        |
                        |
              Raspberry Pi Gateway
              ┌─────────────────┐
              │   server.py     │
              │                 │
              │ Client Manager  │
              │ Session Router  │
              └─────────────────┘
                        |
        ┌───────────────┼───────────────┐
        |
   client.py
        |
   shell.py
        |
   Future modules
        |
   ├── gpio_manager.py
   ├── serial_manager.py
   ├── update_manager.py
   └── plugins
```

---

# Project Structure

```
server/
│
├── server.py              # WebSocket server
├── client.py              # Client session management
├── shell.py               # Remote shell implementation
├── config.py              # Configuration
└── requirements.txt       # Python dependencies
```

---

# Requirements

## Raspberry Pi

Tested with:

* Raspberry Pi OS
* Python 3.10+

Install dependencies:

```bash
cd server

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt
```

---

# Running the Server

Start manually:

```bash
python server.py
```

Expected output:

```
Gateway running ws://0.0.0.0:8765
```

The server is now available at:

```
ws://<raspberry-pi-ip>:8765
```

Example:

```
ws://192.168.1.50:8765
```

---

# WebSocket Protocol

Communication uses JSON messages.

## Connection

Server response:

```json
{
  "type": "connected",
  "message": "Raspberry Pi Gateway ready"
}
```

---

# Keep Alive

Client:

```json
{
  "type": "ping"
}
```

Server:

```json
{
  "type": "pong"
}
```

---

# Device Information

Client:

```json
{
  "type": "info"
}
```

Server:

```json
{
  "type": "info",
  "connected_at": "2026-07-16T14:00:00"
}
```

---

# Remote Shell

## Start shell

Client:

```json
{
  "type": "shell_start"
}
```

Server:

```json
{
  "type": "shell_started"
}
```

---

## Execute command

Client:

```json
{
  "type": "shell_input",
  "data": "ls -la"
}
```

Server:

```json
{
  "type": "shell_output",
  "data": "server.py\nclient.py\n"
}
```

---

# Running as a System Service

Create:

```
/etc/systemd/system/rpi-gateway.service
```

Example:

```ini
[Unit]
Description=Raspberry Pi WebSocket Gateway
After=network.target


[Service]
Type=simple

User=pi

WorkingDirectory=/opt/rpi-gateway/server

ExecStart=/opt/rpi-gateway/server/venv/bin/python server.py

Restart=always
RestartSec=5


[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload

sudo systemctl enable rpi-gateway

sudo systemctl start rpi-gateway
```

Check:

```bash
systemctl status rpi-gateway
```

Logs:

```bash
journalctl -u rpi-gateway -f
```

---

# Security Notes

The shell feature provides remote command execution.

Before exposing this outside a trusted network:

* add authentication
* use TLS (`wss://`)
* restrict network access
* implement user permissions

Recommended deployment:

```
Internet
   |
 VPN / Zero Trust Network
   |
 Raspberry Pi Gateway
```

---

# Roadmap

## Phase 1 - Core Gateway

✅ WebSocket server
✅ Client sessions
✅ Remote shell

---

## Phase 2 - Remote Management

⬜ Authentication
⬜ Command router
⬜ Remote deployment
⬜ Version management
⬜ Automatic updates

---

## Phase 3 - Hardware Integration

⬜ GPIO manager
⬜ Serial devices
⬜ Sensors
⬜ PWM control
⬜ Plugin system

---

# Development Philosophy

The project follows these principles:

* Keep the WebSocket layer stable
* Add features as independent modules
* Avoid coupling hardware logic with communication logic
* Design for unattended Raspberry Pi deployments

---

# License

MIT License

```
```
