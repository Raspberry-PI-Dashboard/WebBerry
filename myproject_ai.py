# ============================================================
# AI-FLATTENED PYTHON PROJECT
# Generated automatically by flatten.py
# ============================================================

# ============================================================
# MODULE: config.py
# ============================================================

import os
HOST = '0.0.0.0'
PORT = 8765
ALLOWED_PINS = {17, 18, 22, 23, 24, 25}
MOCK_GPIO = os.getenv('MOCK_GPIO', '').lower() in {'1', 'true', 'yes'}
BASE_DIR = '/opt/rpi-dashboard'
RELEASES_DIR = f'{BASE_DIR}/releases'
CURRENT_LINK = f'{BASE_DIR}/current'
SERVICE_NAME = 'berryboard.service'
UPDATE_BRANCH = 'main'
REPO_URL = 'git@github.com:your-user/your-project.git'

# ============================================================
# MODULE: shell.py
# ============================================================

import asyncio
import json

class ShellSession:

    def __init__(self, websocket):
        self.websocket = websocket
        self.process = None
        self.reader_task = None

    async def send(self, payload):
        await self.websocket.send(json.dumps(payload))

    async def start(self):
        self.process = await asyncio.create_subprocess_exec('/bin/bash', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        await self.send({'type': 'shell_started'})
        self.reader_task = asyncio.create_task(self.read_output())

    async def read_output(self):
        while True:
            data = await self.process.stdout.readline()
            if not data:
                break
            await self.send({'type': 'shell_output', 'data': data.decode(errors='ignore')})

    async def execute(self, command):
        if not self.process:
            return
        self.process.stdin.write((command + '\n').encode())
        await self.process.stdin.drain()

    async def stop(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
        if self.reader_task:
            self.reader_task.cancel()

# ============================================================
# MODULE: client.py
# ============================================================

import json
from datetime import datetime, timezone
try:
    from gpiozero import DigitalInputDevice
except ImportError:
    DigitalInputDevice = None

class MockInput:

    def __init__(self, pin):
        self.pin = pin
        self.value = False

    def close(self):
        pass

class ClientSession:

    def __init__(self, websocket):
        self.websocket = websocket
        self.shell = None
        self.inputs = {}
        self.authenticated = False
        self.connected_at = datetime.now(timezone.utc)

    async def send(self, payload):
        await self.websocket.send(json.dumps(payload))

    async def start(self):
        await self.send({'type': 'connected', 'timestamp': self.timestamp(), 'message': 'Raspberry Pi Gateway ready'})

    def timestamp(self):
        return datetime.now(timezone.utc).isoformat()

    def read_gpio(self, pin):
        try:
            pin = int(pin)
        except (TypeError, ValueError):
            raise ValueError('Invalid GPIO pin')
        if pin not in ALLOWED_PINS:
            raise ValueError(f'GPIO {pin} is not allowed')
        if pin not in self.inputs:
            if MOCK_GPIO or DigitalInputDevice is None:
                self.inputs[pin] = MockInput(pin)
            else:
                self.inputs[pin] = DigitalInputDevice(pin)
        return {'type': 'pin', 'action': 'read', 'pin': pin, 'value': bool(self.inputs[pin].value)}

    async def handle_message(self, message):
        msg_type = message.get('type')
        if msg_type == 'ping':
            await self.send({'type': 'pong', 'timestamp': self.timestamp()})
        elif msg_type == 'info':
            await self.send({'type': 'info', 'connected_at': self.connected_at.isoformat()})
        elif msg_type == 'pin' and message.get('action') == 'read':
            await self.send(self.read_gpio(message.get('pin')))
        elif msg_type == 'shell_start':
            if self.shell is None:
                self.shell = ShellSession(self.websocket)
                await self.shell.start()
            else:
                await self.send({'type': 'error', 'message': 'Shell already running'})
        elif msg_type == 'shell_input':
            if self.shell:
                await self.shell.execute(message.get('data', ''))
            else:
                await self.send({'type': 'error', 'message': 'Shell not started'})
        else:
            await self.send({'type': 'error', 'message': f'Unknown command {msg_type}'})

    async def close(self):
        if self.shell:
            await self.shell.stop()
        for input_device in self.inputs.values():
            input_device.close()

# ============================================================
# MODULE: gateway.py
# ============================================================

import asyncio
import json
import signal
import websockets
HOST = '0.0.0.0'
PORT = 8765
PING_INTERVAL = 20
PING_TIMEOUT = 30
clients = set()
shutdown_event = asyncio.Event()

async def client_handler(websocket):
    session = ClientSession(websocket)
    clients.add(session)
    print('Client connected', websocket.remote_address)
    await session.start()
    try:
        async for raw in websocket:
            try:
                message = json.loads(raw)
                await session.handle_message(message)
            except Exception as e:
                await session.send({'type': 'error', 'message': str(e)})
    except websockets.ConnectionClosed:
        pass
    finally:
        await session.close()
        clients.remove(session)
        print('Client disconnected', websocket.remote_address)

async def broadcast(message):
    await asyncio.gather(*[client.send(message) for client in clients], return_exceptions=True)

async def shutdown():
    await broadcast({'type': 'server_shutdown'})
    shutdown_event.set()

def setup_signals():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

async def create_server():
    server = await websockets.serve(client_handler, HOST, PORT, ping_interval=PING_INTERVAL, ping_timeout=PING_TIMEOUT)
    await server.start_serving()
    return server

async def run():
    setup_signals()
    server = await create_server()
    print(f'Gateway running ws://{HOST}:{PORT}')
    try:
        await shutdown_event.wait()
    finally:
        server.close()
        await server.wait_closed()
