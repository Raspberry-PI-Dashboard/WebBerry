# ============================================================
# AI-FLATTENED PYTHON PROJECT
# Source: D:\raspberry\WebBerry-main
# Generated automatically by flatten.py
# ============================================================


# ============================================================
# MODULE: config.py
# ============================================================

HOST = '0.0.0.0'
PORT = 8765
BASE_DIR = '/opt/rpi-dashboard'
RELEASES_DIR = f'{BASE_DIR}/releases'
CURRENT_LINK = f'{BASE_DIR}/current'
SERVICE_NAME = 'rpi-dashboard'
UPDATE_BRANCH = 'main'
REPO_URL = 'git@github.com:your-user/your-project.git'

# ============================================================
# MODULE: flatten.py
# ============================================================

import ast
import argparse
import keyword
import tokenize
from pathlib import Path
from collections import defaultdict, deque

def is_python_file(path: Path) -> bool:
    return path.suffix == '.py' and path.name != '__pycache__'

def module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix('')
    parts = list(rel.parts)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(parts)

def collect_files(root: Path):
    return {module_name(path, root): path for path in root.rglob('*.py') if '__pycache__' not in path.parts}

def local_dependencies(tree, current_module, modules):
    deps = set()
    package = current_module.split('.')
    if current_module.endswith('.__init__'):
        package = package[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            level = node.level
            imported = node.module or ''
            if level:
                base = package[:len(package) - level + 1]
                if imported:
                    base += imported.split('.')
            else:
                base = imported.split('.') if imported else []
            if base:
                candidate = '.'.join(base)
                if candidate in modules:
                    deps.add(candidate)
                parts = candidate.split('.')
                for i in range(len(parts) - 1, 0, -1):
                    candidate2 = '.'.join(parts[:i])
                    if candidate2 in modules:
                        deps.add(candidate2)
                        break
        elif isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                if candidate in modules:
                    deps.add(candidate)
                    continue
                parts = candidate.split('.')
                for i in range(len(parts) - 1, 0, -1):
                    candidate2 = '.'.join(parts[:i])
                    if candidate2 in modules:
                        deps.add(candidate2)
                        break
    return deps

def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    node.body.pop(0)

def remove_comments_and_docstrings(source):
    lines = source.splitlines(keepends=True)
    try:
        tokens = list(tokenize.generate_tokens(iter(lines).__next__))
    except Exception:
        return source
    replacements = []
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            replacements.append((tok.start, tok.end, ''))
    for start, end, replacement in reversed(replacements):
        sl, sc = start
        el, ec = end
        if sl == el:
            line = lines[sl - 1]
            lines[sl - 1] = line[:sc] + replacement + line[ec:]
        else:
            lines[sl - 1] = lines[sl - 1][:sc] + replacement
            for i in range(sl, el - 1):
                lines[i] = ''
            lines[el - 1] = lines[el - 1][ec:]
    return ''.join(lines)

def clean_source(source):
    tree = ast.parse(source)
    strip_docstrings(tree)
    source = ast.unparse(tree)
    source = remove_comments_and_docstrings(source)
    output = []
    previous_blank = False
    for line in source.splitlines():
        line = line.rstrip()
        if not line:
            if previous_blank:
                continue
            previous_blank = True
            output.append('')
        else:
            previous_blank = False
            output.append(line)
    return '\n'.join(output).strip()

def topological_sort(modules, dependencies):
    indegree = {m: 0 for m in modules}
    reverse = defaultdict(set)
    for module, deps in dependencies.items():
        for dep in deps:
            if dep not in modules:
                continue
            indegree[module] += 1
            reverse[dep].add(module)
    queue = deque((m for m in modules if indegree[m] == 0))
    result = []
    while queue:
        module = queue.popleft()
        result.append(module)
        for dependent in reverse[module]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
    for module in modules:
        if module not in result:
            result.append(module)
    return result

def remove_local_imports(source, module, modules):
    tree = ast.parse(source)
    lines = source.splitlines()
    remove_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    for line in range(node.lineno, node.end_lineno + 1):
                        remove_lines.add(line)
        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ''
            if node.level:
                parts = module.split('.')
                base = parts[:-node.level]
                if imported:
                    base += imported.split('.')
                candidate = '.'.join(base)
                if candidate in modules:
                    for line in range(node.lineno, node.end_lineno + 1):
                        remove_lines.add(line)
            elif imported in modules:
                for line in range(node.lineno, node.end_lineno + 1):
                    remove_lines.add(line)
    return '\n'.join((line for i, line in enumerate(lines, 1) if i not in remove_lines))

def flatten(root: Path, output: Path):
    modules = collect_files(root)
    if not modules:
        raise RuntimeError('No Python files found.')
    trees = {}
    sources = {}
    for name, path in modules.items():
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
            trees[name] = tree
            sources[name] = source
        except SyntaxError as e:
            print(f'WARNING: skipping {path}: {e}')
    dependencies = {}
    for name, tree in trees.items():
        dependencies[name] = local_dependencies(tree, name, trees)
    order = topological_sort(list(trees), dependencies)
    output_parts = []
    output_parts.append(f'# ============================================================\n# AI-FLATTENED PYTHON PROJECT\n# Source: {root}\n# Generated automatically by flatten.py\n# ============================================================\n')
    for name in order:
        path = modules[name]
        try:
            cleaned = clean_source(sources[name])
            cleaned = remove_local_imports(cleaned, name, modules)
            if not cleaned.strip():
                continue
            output_parts.append(f'\n# ============================================================\n# MODULE: {path.relative_to(root)}\n# ============================================================\n')
            output_parts.append(cleaned)
        except Exception as e:
            print(f'WARNING: could not process {path}: {e}')
    output.write_text('\n'.join(output_parts).rstrip() + '\n', encoding='utf-8')
    print(f'Flattened {len(order)} modules')
    print(f'Output: {output}')

def main():
    parser = argparse.ArgumentParser(description='Flatten a Python project into one AI-friendly .py file.')
    parser.add_argument('project', type=Path, help='Project directory')
    parser.add_argument('-o', '--output', type=Path, default=Path('project_flat.py'), help='Output Python file')
    args = parser.parse_args()
    root = args.project.resolve()
    if not root.is_dir():
        raise SystemExit(f'Not a directory: {root}')
    flatten(root, args.output.resolve())
if __name__ == '__main__':
    main()

# ============================================================
# MODULE: server_mini.py
# ============================================================

import asyncio
import json
import subprocess
import websockets
from gpiozero import DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice
HOST = '0.0.0.0'
PORT = 8765
ALLOWED_PINS = {17, 18, 22, 23, 24, 25}
DEFAULT_PWM_FREQUENCY = 1000
outputs = {}
inputs = {}
pwm_outputs = {}

def validate_pin(pin):
    pin = int(pin)
    if pin not in ALLOWED_PINS:
        raise ValueError(f'GPIO {pin} is not allowed')
    return pin

def get_output(pin):
    pin = validate_pin(pin)
    if pin not in outputs:
        outputs[pin] = DigitalOutputDevice(pin, initial_value=False)
    return outputs[pin]

def get_input(pin):
    pin = validate_pin(pin)
    if pin not in inputs:
        inputs[pin] = DigitalInputDevice(pin)
    return inputs[pin]

def get_pwm(pin):
    pin = validate_pin(pin)
    if pin not in pwm_outputs:
        pwm_outputs[pin] = PWMOutputDevice(pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY)
    return pwm_outputs[pin]

def handle_pin(message):
    action = message.get('action')
    if 'pin' not in message:
        raise ValueError('Missing pin')
    pin = validate_pin(message['pin'])
    if action == 'set':
        if 'value' not in message:
            raise ValueError('Missing value')
        value = bool(message['value'])
        output = get_output(pin)
        output.value = value
        return {'ok': True, 'type': 'pin', 'action': 'set', 'pin': pin, 'value': bool(output.value)}
    if action == 'toggle':
        output = get_output(pin)
        output.toggle()
        return {'ok': True, 'type': 'pin', 'action': 'toggle', 'pin': pin, 'value': bool(output.value)}
    if action == 'read':
        input_pin = get_input(pin)
        return {'ok': True, 'type': 'pin', 'action': 'read', 'pin': pin, 'value': bool(input_pin.value)}
    if action == 'pwm_set':
        if 'duty_cycle' not in message:
            raise ValueError('Missing duty_cycle')
        duty_cycle = float(message['duty_cycle'])
        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError('duty_cycle must be between 0.0 and 1.0')
        frequency = int(message.get('frequency', DEFAULT_PWM_FREQUENCY))
        if frequency <= 0:
            raise ValueError('frequency must be positive')
        pwm = get_pwm(pin)
        pwm.frequency = frequency
        pwm.value = duty_cycle
        return {'ok': True, 'type': 'pwm', 'action': 'pwm_set', 'pin': pin, 'duty_cycle': float(pwm.value), 'frequency': int(pwm.frequency)}
    if action == 'pwm_stop':
        pwm = get_pwm(pin)
        pwm.value = 0
        return {'ok': True, 'type': 'pwm', 'action': 'pwm_stop', 'pin': pin, 'duty_cycle': 0.0, 'frequency': int(pwm.frequency)}
    raise ValueError(f'Unknown pin action: {action}')
ALLOWED_COMMANDS = {'hostname', 'uptime', 'date', 'uname', 'vcgencmd'}

async def handle_shell(message):
    command = message.get('command')
    if not command:
        raise ValueError('Missing command')
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f'Command not allowed: {command}')
    args = message.get('args', [])
    if not isinstance(args, list):
        raise ValueError('args must be a list')
    argv = [command] + [str(arg) for arg in args]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=5, shell=False)
    except subprocess.TimeoutExpired:
        raise ValueError('Command timed out')
    return {'ok': result.returncode == 0, 'type': 'shell', 'command': command, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

async def client_handler(websocket):
    client = websocket.remote_address
    print(f'Client connected: {client}')
    try:
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    raise ValueError('Message must be a JSON object')
                message_type = message.get('type')
                if message_type == 'ping':
                    response = {'ok': True, 'type': 'pong'}
                elif message_type == 'pin':
                    response = handle_pin(message)
                elif message_type == 'shell':
                    response = await handle_shell(message)
                else:
                    raise ValueError(f'Unknown message type: {message_type}')
            except json.JSONDecodeError:
                response = {'ok': False, 'error': 'Invalid JSON'}
            except Exception as exc:
                response = {'ok': False, 'error': str(exc)}
            await websocket.send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f'Client disconnected: {client}')

def cleanup():
    for device in outputs.values():
        device.close()
    for device in inputs.values():
        device.close()
    for device in pwm_outputs.values():
        device.close()

async def main():
    print(f'Starting Raspberry Pi WebSocket server on {HOST}:{PORT}')
    try:
        async with websockets.serve(client_handler, HOST, PORT):
            print('Server ready')
            await asyncio.Future()
    finally:
        cleanup()
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nServer stopped')

# ============================================================
# MODULE: server_mini_test.py
# ============================================================

import asyncio
import json
import os
import platform
import subprocess
import websockets
HOST = '0.0.0.0'
PORT = 8765
PROTOCOL_VERSION = 1
DEFAULT_PWM_FREQUENCY = 1000
ALLOWED_PINS = {17, 18, 22, 23, 24, 25}
FORCE_MOCK = os.getenv('MOCK_GPIO', '').lower() in {'1', 'true', 'yes'}
try:
    if FORCE_MOCK:
        raise ImportError('Mock GPIO requested')
    from gpiozero import DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice
    MOCK_GPIO = False
except ImportError:
    MOCK_GPIO = True

class MockOutput:

    def __init__(self, pin, initial_value=False):
        self.pin = pin
        self.value = bool(initial_value)
        print(f'[MOCK] GPIO {pin} output initialized value={self.value}')

    def toggle(self):
        self.value = not self.value
        print(f'[MOCK] GPIO {self.pin} toggled value={self.value}')

    def close(self):
        pass

class MockInput:

    def __init__(self, pin):
        self.pin = pin
        self.value = False
        print(f'[MOCK] GPIO {pin} input initialized')

    def close(self):
        pass

class MockPWM:

    def __init__(self, pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY):
        self.pin = pin
        self.value = float(initial_value)
        self.frequency = int(frequency)
        print(f'[MOCK] PWM GPIO {pin} initialized duty={self.value} frequency={self.frequency}')

    def close(self):
        pass
outputs = {}
inputs = {}
pwm_outputs = {}

def validate_pin(pin):
    try:
        pin = int(pin)
    except (TypeError, ValueError):
        raise ValueError('Invalid GPIO pin')
    if pin not in ALLOWED_PINS:
        raise ValueError(f'GPIO {pin} is not allowed')
    return pin

def get_output(pin):
    pin = validate_pin(pin)
    if pin not in outputs:
        if MOCK_GPIO:
            outputs[pin] = MockOutput(pin, initial_value=False)
        else:
            outputs[pin] = DigitalOutputDevice(pin, initial_value=False)
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
            pwm_outputs[pin] = MockPWM(pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY)
        else:
            pwm_outputs[pin] = PWMOutputDevice(pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY)
    return pwm_outputs[pin]

def get_startup_state():
    pins = []
    for pin in sorted(ALLOWED_PINS):
        digital_value = False
        pwm_value = 0.0
        pwm_frequency = DEFAULT_PWM_FREQUENCY
        pwm_active = False
        if pin in outputs:
            digital_value = bool(outputs[pin].value)
        if pin in pwm_outputs:
            pwm = pwm_outputs[pin]
            pwm_value = float(pwm.value)
            pwm_frequency = int(pwm.frequency)
            pwm_active = pwm_value > 0
        pins.append({'pin': pin, 'digital': {'value': digital_value}, 'pwm': {'active': pwm_active, 'duty_cycle': pwm_value, 'frequency': pwm_frequency}})
    return {'ok': True, 'type': 'startup', 'protocol': {'version': PROTOCOL_VERSION}, 'device': {'name': platform.node(), 'platform': platform.system(), 'release': platform.release(), 'mock_gpio': MOCK_GPIO}, 'capabilities': ['digital', 'pwm', 'read', 'shell'], 'pwm': {'default_frequency': DEFAULT_PWM_FREQUENCY, 'duty_cycle_min': 0.0, 'duty_cycle_max': 1.0}, 'pins': pins}

def handle_pin(message):
    action = message.get('action')
    if 'pin' not in message:
        raise ValueError('Missing pin')
    pin = validate_pin(message['pin'])
    if action == 'set':
        if 'value' not in message:
            raise ValueError('Missing value')
        value = bool(message['value'])
        output = get_output(pin)
        output.value = value
        if MOCK_GPIO:
            print(f"[MOCK] GPIO {pin} -> {('HIGH' if value else 'LOW')}")
        return {'ok': True, 'type': 'pin', 'action': 'set', 'pin': pin, 'value': bool(output.value)}
    if action == 'toggle':
        output = get_output(pin)
        output.toggle()
        return {'ok': True, 'type': 'pin', 'action': 'toggle', 'pin': pin, 'value': bool(output.value)}
    if action == 'read':
        input_pin = get_input(pin)
        return {'ok': True, 'type': 'pin', 'action': 'read', 'pin': pin, 'value': bool(input_pin.value)}
    if action == 'pwm_set':
        if 'duty_cycle' not in message:
            raise ValueError('Missing duty_cycle')
        duty_cycle = float(message['duty_cycle'])
        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError('duty_cycle must be between 0.0 and 1.0')
        frequency = int(message.get('frequency', DEFAULT_PWM_FREQUENCY))
        if frequency <= 0:
            raise ValueError('frequency must be positive')
        pwm = get_pwm(pin)
        pwm.frequency = frequency
        pwm.value = duty_cycle
        if MOCK_GPIO:
            print(f'[MOCK] PWM GPIO {pin} -> duty={duty_cycle:.3f} frequency={frequency}Hz')
        return {'ok': True, 'type': 'pwm', 'action': 'pwm_set', 'pin': pin, 'duty_cycle': float(pwm.value), 'frequency': int(pwm.frequency)}
    if action == 'pwm_stop':
        pwm = get_pwm(pin)
        pwm.value = 0
        if MOCK_GPIO:
            print(f'[MOCK] PWM GPIO {pin} stopped')
        return {'ok': True, 'type': 'pwm', 'action': 'pwm_stop', 'pin': pin, 'duty_cycle': 0.0, 'frequency': int(pwm.frequency)}
    raise ValueError(f'Unknown pin action: {action}')
ALLOWED_COMMANDS = {'hostname', 'uptime', 'date', 'uname'}

async def handle_shell(message):
    command = message.get('command')
    if not command:
        raise ValueError('Missing command')
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f'Command not allowed: {command}')
    args = message.get('args', [])
    if not isinstance(args, list):
        raise ValueError('args must be a list')
    argv = [command, *[str(arg) for arg in args]]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=5, shell=False)
    except subprocess.TimeoutExpired:
        raise ValueError('Command timed out')
    return {'ok': result.returncode == 0, 'type': 'shell', 'command': command, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

async def client_handler(websocket):
    client = websocket.remote_address
    print(f'Client connected: {client}')
    try:
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    raise ValueError('Message must be a JSON object')
                message_type = message.get('type')
                if message_type == 'startup':
                    response = get_startup_state()
                elif message_type == 'ping':
                    response = {'ok': True, 'type': 'pong'}
                elif message_type == 'pin':
                    response = handle_pin(message)
                elif message_type == 'shell':
                    response = await handle_shell(message)
                else:
                    raise ValueError(f'Unknown message type: {message_type}')
            except json.JSONDecodeError:
                response = {'ok': False, 'error': 'Invalid JSON'}
            except Exception as exc:
                response = {'ok': False, 'error': str(exc)}
            await websocket.send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f'Client disconnected: {client}')

def cleanup():
    for device in outputs.values():
        device.close()
    for device in inputs.values():
        device.close()
    for device in pwm_outputs.values():
        device.close()

async def main():
    mode = 'MOCK GPIO' if MOCK_GPIO else 'RASPBERRY PI GPIO'
    print('=' * 60)
    print('Raspberry Pi WebSocket GPIO Server')
    print('=' * 60)
    print(f'Protocol : {PROTOCOL_VERSION}')
    print(f'Mode     : {mode}')
    print(f'Host     : {HOST}')
    print(f'Port     : {PORT}')
    print(f'Pins     : {sorted(ALLOWED_PINS)}')
    print('=' * 60)
    try:
        async with websockets.serve(client_handler, HOST, PORT):
            print('WebSocket server ready')
            await asyncio.Future()
    finally:
        cleanup()
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nServer stopped')

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
# MODULE: modular\config.py
# ============================================================

import os
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8765'))
PROTOCOL_VERSION = 1
DEFAULT_PWM_FREQUENCY = int(os.getenv('PWM_FREQUENCY', '1000'))
ALLOWED_PINS = {17, 18, 22, 23, 24, 25}
MOCK_GPIO = os.getenv('MOCK_GPIO', '').lower() in {'1', 'true', 'yes'}
ALLOWED_SHELL_COMMANDS = {'hostname', 'uptime', 'date', 'uname'}

# ============================================================
# MODULE: modular\events.py
# ============================================================

import asyncio
import json

class EventManager:

    def __init__(self):
        self.clients = set()

    def add(self, websocket):
        self.clients.add(websocket)

    def remove(self, websocket):
        self.clients.discard(websocket)

    async def broadcast(self, event, data=None):
        message = {'type': 'event', 'event': event, 'data': data or {}}
        payload = json.dumps(message)
        if not self.clients:
            return
        clients = list(self.clients)
        results = await asyncio.gather(*[client.send(payload) for client in clients], return_exceptions=True)
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                self.remove(client)

# ============================================================
# MODULE: tests\test_connection.py
# ============================================================

import json
import pytest
import websockets
from websockets.protocol import State

@pytest.mark.asyncio
async def test_connection(websocket_server):
    async with websockets.connect('ws://localhost:8765') as ws:
        assert ws.state != State.CLOSED
        response = json.loads(await ws.recv())
        assert response['type'] == 'connected'

# ============================================================
# MODULE: tests\test_ping.py
# ============================================================

import json
import pytest
import websockets

@pytest.mark.asyncio
async def test_ping(websocket_server):
    async with websockets.connect('ws://localhost:8765') as ws:
        await ws.recv()
        await ws.send(json.dumps({'type': 'ping'}))
        response = json.loads(await ws.recv())
        assert response['type'] == 'pong'

# ============================================================
# MODULE: tests\test_shell.py
# ============================================================

import json
import pytest
import websockets

@pytest.mark.asyncio
async def test_shell(websocket_server):
    async with websockets.connect('ws://localhost:8765') as ws:
        await ws.recv()
        await ws.send(json.dumps({'type': 'shell_start'}))
        response = json.loads(await ws.recv())
        assert response['type'] == 'shell_started'
        await ws.send(json.dumps({'type': 'shell_input', 'data': 'echo pytest'}))
        output = json.loads(await ws.recv())
        assert output['type'] == 'shell_output'
        assert 'pytest' in output['data']

# ============================================================
# MODULE: modular\i2c\config.py
# ============================================================

import os
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8765'))
PROTOCOL_VERSION = 1
DEFAULT_PWM_FREQUENCY = int(os.getenv('PWM_FREQUENCY', '1000'))
ALLOWED_PINS = {17, 18, 22, 23, 24, 25}
I2C_BUS = int(os.getenv('I2C_BUS', '1'))
I2C_MOCK = os.getenv('I2C_MOCK', '').lower() in {'1', 'true', 'yes'}
MOCK_GPIO = os.getenv('MOCK_GPIO', '').lower() in {'1', 'true', 'yes'}
ALLOWED_SHELL_COMMANDS = {'hostname', 'uptime', 'date', 'uname'}

# ============================================================
# MODULE: modular\i2c\mock.py
# ============================================================

class MockI2CBackend:
    is_mock = True

    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.devices = {72: bytearray(256), 80: bytearray(256)}
        self.devices[72][0] = 66
        self.devices[72][1] = 18
        self.devices[80][0] = 170
        print(f'[MOCK] I2C bus {bus_number} initialized')

    def _device(self, address):
        if address not in self.devices:
            raise OSError(f'No I2C device at 0x{address:02X}')
        return self.devices[address]

    def scan(self):
        return sorted(self.devices.keys())

    def read_byte(self, address):
        device = self._device(address)
        return device[0]

    def write_byte(self, address, value):
        device = self._device(address)
        device[0] = value & 255
        print(f'[MOCK] I2C 0x{address:02X} write byte 0x{value:02X}')

    def read_register(self, address, register):
        device = self._device(address)
        return device[register & 255]

    def write_register(self, address, register, value):
        device = self._device(address)
        register &= 255
        value &= 255
        device[register] = value
        print(f'[MOCK] I2C 0x{address:02X} reg=0x{register:02X} value=0x{value:02X}')

    def read_block(self, address, register, length):
        device = self._device(address)
        register &= 255
        return list(device[register:register + length])

    def write_block(self, address, register, data):
        device = self._device(address)
        register &= 255
        for index, value in enumerate(data):
            position = register + index
            if position >= len(device):
                break
            device[position] = value & 255
        print(f'[MOCK] I2C 0x{address:02X} register=0x{register:02X} data={data}')

    def close(self):
        pass

# ============================================================
# MODULE: modular\i2c\real.py
# ============================================================

from smbus2 import SMBus

class RealI2CBackend:
    is_mock = False

    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.bus = SMBus(bus_number)

    def scan(self):
        devices = []
        for address in range(3, 120):
            try:
                self.bus.write_quick(address)
                devices.append(address)
            except OSError:
                pass
        return devices

    def read_byte(self, address):
        return self.bus.read_byte(address)

    def write_byte(self, address, value):
        self.bus.write_byte(address, value)

    def read_register(self, address, register):
        return self.bus.read_byte_data(address, register)

    def write_register(self, address, register, value):
        self.bus.write_byte_data(address, register, value)

    def read_block(self, address, register, length):
        return self.bus.read_i2c_block_data(address, register, length)

    def write_block(self, address, register, data):
        self.bus.write_i2c_block_data(address, register, list(data))

    def close(self):
        self.bus.close()

# ============================================================
# MODULE: modular\gpio\real.py
# ============================================================

from gpiozero import DigitalInputDevice, DigitalOutputDevice, PWMOutputDevice

class RealGPIOBackend:
    is_mock = False

    def output(self, pin):
        return DigitalOutputDevice(pin, initial_value=False)

    def input(self, pin):
        return DigitalInputDevice(pin)

    def pwm(self, pin):
        return PWMOutputDevice(pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY)

    def close(self):
        pass

# ============================================================
# MODULE: modular\shell.py
# ============================================================

import asyncio
import subprocess

class ShellManager:

    async def execute(self, message):
        command = message.get('command')
        if not command:
            raise ValueError('Missing command')
        if command not in ALLOWED_SHELL_COMMANDS:
            raise ValueError(f'Command not allowed: {command}')
        args = message.get('args', [])
        if not isinstance(args, list):
            raise ValueError('args must be a list')
        argv = [command, *[str(arg) for arg in args]]
        try:
            result = await asyncio.to_thread(subprocess.run, argv, capture_output=True, text=True, timeout=5, shell=False)
        except subprocess.TimeoutExpired:
            raise ValueError('Command timed out')
        return {'ok': result.returncode == 0, 'type': 'shell', 'command': command, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

# ============================================================
# MODULE: update_manager.py
# ============================================================

import asyncio
import os
import subprocess
from datetime import datetime

def run(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    return {'code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

async def deploy():
    version = datetime.now().strftime('%Y%m%d_%H%M%S')
    release = f'{RELEASES_DIR}/{version}'
    os.makedirs(release, exist_ok=True)
    yield {'step': 'download', 'message': 'Cloning repository'}
    result = run(f'git clone --branch {UPDATE_BRANCH} {REPO_URL} {release}')
    if result['code'] != 0:
        yield {'step': 'error', 'message': result['stderr']}
        return
    yield {'step': 'dependencies', 'message': 'Installing packages'}
    run('python3 -m venv venv', cwd=release)
    run('./venv/bin/pip install -r requirements.txt', cwd=release)
    yield {'step': 'switch', 'message': 'Switching release'}
    run(f'ln -sfn {release} {CURRENT_LINK}')
    yield {'step': 'restart', 'message': 'Restarting service'}
    run(f'sudo systemctl restart {SERVICE_NAME}')
    yield {'step': 'done', 'message': version}

# ============================================================
# MODULE: modular\gpio\mock.py
# ============================================================


class MockOutput:

    def __init__(self, pin, initial_value=False):
        self.pin = pin
        self.value = bool(initial_value)
        print(f'[MOCK] GPIO {pin} output initialized value={self.value}')

    def toggle(self):
        self.value = not self.value
        print(f'[MOCK] GPIO {self.pin} toggled value={self.value}')

    def close(self):
        pass

class MockInput:

    def __init__(self, pin):
        self.pin = pin
        self.value = False
        print(f'[MOCK] GPIO {pin} input initialized')

    def close(self):
        pass

class MockPWM:

    def __init__(self, pin, initial_value=0, frequency=DEFAULT_PWM_FREQUENCY):
        self.pin = pin
        self.value = float(initial_value)
        self.frequency = int(frequency)
        print(f'[MOCK] PWM GPIO {pin} initialized duty={self.value} frequency={self.frequency}')

    def close(self):
        pass

class MockGPIOBackend:
    is_mock = True

    def output(self, pin):
        return MockOutput(pin)

    def input(self, pin):
        return MockInput(pin)

    def pwm(self, pin):
        return MockPWM(pin)

    def close(self):
        pass

# ============================================================
# MODULE: modular\protocol.py
# ============================================================

import platform

class Protocol:

    def __init__(self, gpio, shell, i2c):
        self.gpio = gpio
        self.shell = shell
        self.i2c = i2c

    async def handle(self, message):
        if not isinstance(message, dict):
            raise ValueError('Message must be a JSON object')
        message_type = message.get('type')
        if message_type == 'startup':
            return self.startup()
        if message_type == 'ping':
            return {'ok': True, 'type': 'pong'}
        if message_type == 'pin':
            return self.pin(message)
        if message_type == 'i2c':
            return self.i2c_command(message)
        if message_type == 'shell':
            return await self.shell_command(message)
        raise ValueError(f'Unknown message type: {message_type}')

    def startup(self):
        return {'ok': True, 'type': 'startup', 'protocol': {'version': PROTOCOL_VERSION}, 'device': {'name': platform.node(), 'platform': platform.system(), 'release': platform.release(), 'mock_gpio': MOCK_GPIO}, 'capabilities': ['digital', 'pwm', 'read', 'i2c', 'shell'], 'pins': sorted(ALLOWED_PINS), 'pwm': {'default_frequency': DEFAULT_PWM_FREQUENCY, 'duty_cycle_min': 0.0, 'duty_cycle_max': 1.0}, 'i2c': {'bus': I2C_BUS, 'mock': self.i2c.backend.is_mock, 'operations': ['scan', 'read_byte', 'write_byte', 'read_register', 'write_register', 'read_block', 'write_block']}, 'shell': {'commands': sorted(ALLOWED_SHELL_COMMANDS)}, 'state': {'gpio': self.gpio.state(), 'i2c': self.i2c.state()}}

    def pin(self, message):
        action = message.get('action')
        pin = message.get('pin')
        if pin is None:
            raise ValueError('Missing pin')
        if action == 'set':
            result = self.gpio.set(pin, message.get('value'))
        elif action == 'toggle':
            result = self.gpio.toggle(pin)
        elif action == 'read':
            result = self.gpio.read(pin)
        elif action == 'pwm_set':
            result = self.gpio.pwm_set(pin, message.get('duty_cycle'), message.get('frequency'))
        elif action == 'pwm_stop':
            result = self.gpio.pwm_stop(pin)
        else:
            raise ValueError(f'Unknown pin action: {action}')
        return {'ok': True, 'type': 'pin', 'action': action, **result}

    def i2c_command(self, message):
        action = message.get('action')
        if action == 'scan':
            result = self.i2c.scan()
        elif action == 'read_byte':
            result = self.i2c.read_byte(message.get('address'))
        elif action == 'write_byte':
            result = self.i2c.write_byte(message.get('address'), message.get('value'))
        elif action == 'read_register':
            result = self.i2c.read_register(message.get('address'), message.get('register'))
        elif action == 'write_register':
            result = self.i2c.write_register(message.get('address'), message.get('register'), message.get('value'))
        elif action == 'read_block':
            result = self.i2c.read_block(message.get('address'), message.get('register'), message.get('length'))
        elif action == 'write_block':
            result = self.i2c.write_block(message.get('address'), message.get('register'), message.get('data'))
        else:
            raise ValueError(f'Unknown I2C action: {action}')
        return {'ok': True, 'type': 'i2c', 'action': action, **result}

    async def shell_command(self, message):
        return await self.shell.execute(message)

# ============================================================
# MODULE: modular\server.py
# ============================================================

import asyncio
import json
import websockets
from events import EventManager
from gpio import GPIOManager
from i2c import I2CManager
from protocol import Protocol
events = EventManager()

def emit_event(event, data):
    asyncio.create_task(events.broadcast(event, data))
gpio = GPIOManager(event_callback=emit_event)
i2c = I2CManager(event_callback=emit_event)
shell = ShellManager()
protocol = Protocol(gpio=gpio, i2c=i2c, shell=shell)

async def client_handler(websocket):
    client = websocket.remote_address
    events.add(websocket)
    print(f'[WS] Client connected: {client}')
    try:
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                response = await protocol.handle(message)
            except json.JSONDecodeError:
                response = {'ok': False, 'error': 'Invalid JSON'}
            except Exception as exc:
                response = {'ok': False, 'error': str(exc)}
            await websocket.send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        events.remove(websocket)
        print(f'[WS] Client disconnected: {client}')

async def main():
    print('=' * 50)
    print('Raspberry Pi Control Server')
    print('=' * 50)
    print(f'WebSocket : {HOST}:{PORT}')
    print(f"GPIO      : {('MOCK' if gpio.backend.is_mock else 'REAL')}")
    print(f"I2C       : {('MOCK' if i2c.backend.is_mock else 'REAL')} (bus {i2c.bus_number})")
    print('=' * 50)
    try:
        async with websockets.serve(client_handler, HOST, PORT):
            print('[WS] Server ready')
            await asyncio.Future()
    finally:
        gpio.close()
        i2c.close()
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nServer stopped')

# ============================================================
# MODULE: client.py
# ============================================================

import json
from datetime import datetime, timezone

class ClientSession:

    def __init__(self, websocket):
        self.websocket = websocket
        self.shell = None
        self.authenticated = False
        self.connected_at = datetime.now(timezone.utc)

    async def send(self, payload):
        await self.websocket.send(json.dumps(payload))

    async def start(self):
        await self.send({'type': 'connected', 'timestamp': self.timestamp(), 'message': 'Raspberry Pi Gateway ready'})

    def timestamp(self):
        return datetime.now(timezone.utc).isoformat()

    async def handle_message(self, message):
        msg_type = message.get('type')
        if msg_type == 'ping':
            await self.send({'type': 'pong', 'timestamp': self.timestamp()})
        elif msg_type == 'info':
            await self.send({'type': 'info', 'connected_at': self.connected_at.isoformat()})
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

# ============================================================
# MODULE: server.py
# ============================================================

import asyncio
if __name__ == '__main__':
    asyncio.run(run())

# ============================================================
# MODULE: tests\conftest.py
# ============================================================

import sys
import subprocess
from pathlib import Path
import pytest_asyncio
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SERVICE_NAME = 'mio-python.service'

@pytest_asyncio.fixture(scope='session')
async def websocket_server():
    subprocess.run(['sudo', 'systemctl', 'stop', SERVICE_NAME], check=True)
    server = None
    try:
        server = await create_server()
        yield server
    finally:
        if server is not None:
            server.close()
            await server.wait_closed()
        subprocess.run(['sudo', 'systemctl', 'start', SERVICE_NAME], check=True)

# ============================================================
# MODULE: modular\gpio\manager.py
# ============================================================


class GPIOManager:

    def __init__(self, event_callback=None):
        self.outputs = {}
        self.inputs = {}
        self.pwm_outputs = {}
        self.event_callback = event_callback
        self.backend = self._create_backend()

    def _create_backend(self):
        if MOCK_GPIO:
            return MockGPIOBackend()
        try:
            return RealGPIOBackend()
        except ImportError:
            print('[GPIO] gpiozero unavailable, falling back to mock')
            return MockGPIOBackend()

    def _emit(self, event, data):
        if self.event_callback:
            self.event_callback(event, data)

    def validate_pin(self, pin):
        try:
            pin = int(pin)
        except (TypeError, ValueError):
            raise ValueError('Invalid GPIO pin')
        if pin not in ALLOWED_PINS:
            raise ValueError(f'GPIO {pin} is not allowed')
        return pin

    def _get_output(self, pin):
        pin = self.validate_pin(pin)
        if pin not in self.outputs:
            self.outputs[pin] = self.backend.output(pin)
        return self.outputs[pin]

    def _get_input(self, pin):
        pin = self.validate_pin(pin)
        if pin not in self.inputs:
            self.inputs[pin] = self.backend.input(pin)
        return self.inputs[pin]

    def _get_pwm(self, pin):
        pin = self.validate_pin(pin)
        if pin not in self.pwm_outputs:
            self.pwm_outputs[pin] = self.backend.pwm(pin)
        return self.pwm_outputs[pin]

    def set(self, pin, value):
        pin = self.validate_pin(pin)
        output = self._get_output(pin)
        output.value = bool(value)
        result = {'pin': pin, 'value': bool(output.value)}
        self._emit('pin_changed', result)
        return result

    def toggle(self, pin):
        pin = self.validate_pin(pin)
        output = self._get_output(pin)
        output.toggle()
        result = {'pin': pin, 'value': bool(output.value)}
        self._emit('pin_changed', result)
        return result

    def read(self, pin):
        pin = self.validate_pin(pin)
        input_device = self._get_input(pin)
        return {'pin': pin, 'value': bool(input_device.value)}

    def pwm_set(self, pin, duty_cycle, frequency=None):
        pin = self.validate_pin(pin)
        duty_cycle = float(duty_cycle)
        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError('duty_cycle must be between 0.0 and 1.0')
        if frequency is None:
            frequency = DEFAULT_PWM_FREQUENCY
        frequency = int(frequency)
        if frequency <= 0:
            raise ValueError('frequency must be positive')
        pwm = self._get_pwm(pin)
        pwm.frequency = frequency
        pwm.value = duty_cycle
        result = {'pin': pin, 'duty_cycle': float(pwm.value), 'frequency': int(pwm.frequency)}
        self._emit('pwm_changed', result)
        return result

    def pwm_stop(self, pin):
        pin = self.validate_pin(pin)
        pwm = self._get_pwm(pin)
        pwm.value = 0
        result = {'pin': pin, 'duty_cycle': 0.0, 'frequency': int(pwm.frequency)}
        self._emit('pwm_changed', result)
        return result

    def state(self):
        pins = []
        for pin in sorted(ALLOWED_PINS):
            digital_value = False
            pwm_value = 0.0
            pwm_frequency = DEFAULT_PWM_FREQUENCY
            if pin in self.outputs:
                digital_value = bool(self.outputs[pin].value)
            if pin in self.pwm_outputs:
                pwm = self.pwm_outputs[pin]
                pwm_value = float(pwm.value)
                pwm_frequency = int(pwm.frequency)
            pins.append({'pin': pin, 'digital': {'value': digital_value}, 'pwm': {'active': pwm_value > 0, 'duty_cycle': pwm_value, 'frequency': pwm_frequency}})
        return pins

    def close(self):
        for device in self.outputs.values():
            device.close()
        for device in self.inputs.values():
            device.close()
        for device in self.pwm_outputs.values():
            device.close()
        self.backend.close()

# ============================================================
# MODULE: modular\gpio\__init__.py
# ============================================================

from .manager import GPIOManager
__all__ = ['GPIOManager']

# ============================================================
# MODULE: modular\i2c\manager.py
# ============================================================


class I2CManager:

    def __init__(self, event_callback=None):
        self.bus_number = I2C_BUS
        self.event_callback = event_callback
        self.backend = self._create_backend()

    def _create_backend(self):
        if I2C_MOCK:
            return MockI2CBackend(self.bus_number)
        try:
            return RealI2CBackend(self.bus_number)
        except ImportError:
            print('[I2C] smbus2 unavailable, falling back to mock')
            return MockI2CBackend(self.bus_number)

    def _emit(self, event, data):
        if self.event_callback:
            self.event_callback(event, data)

    @staticmethod
    def validate_address(address):
        try:
            address = int(address)
        except (TypeError, ValueError):
            raise ValueError('Invalid I2C address')
        if not 3 <= address <= 119:
            raise ValueError('I2C address must be between 0x03 and 0x77')
        return address

    @staticmethod
    def validate_byte(value, name='value'):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f'Invalid {name}')
        if not 0 <= value <= 255:
            raise ValueError(f'{name} must be between 0 and 255')
        return value

    @staticmethod
    def validate_register(register):
        return I2CManager.validate_byte(register, 'register')

    @staticmethod
    def validate_length(length):
        try:
            length = int(length)
        except (TypeError, ValueError):
            raise ValueError('Invalid block length')
        if not 1 <= length <= 32:
            raise ValueError('I2C block length must be between 1 and 32')
        return length

    @staticmethod
    def validate_data(data):
        if not isinstance(data, list):
            raise ValueError('data must be a list')
        if len(data) > 32:
            raise ValueError('I2C block cannot exceed 32 bytes')
        return [I2CManager.validate_byte(value, 'data value') for value in data]

    def scan(self):
        addresses = self.backend.scan()
        result = {'bus': self.bus_number, 'addresses': addresses}
        self._emit('i2c_scan', result)
        return result

    def read_byte(self, address):
        address = self.validate_address(address)
        value = self.backend.read_byte(address)
        result = {'bus': self.bus_number, 'address': address, 'value': value}
        self._emit('i2c_read', result)
        return result

    def write_byte(self, address, value):
        address = self.validate_address(address)
        value = self.validate_byte(value)
        self.backend.write_byte(address, value)
        result = {'bus': self.bus_number, 'address': address, 'value': value}
        self._emit('i2c_write', result)
        return result

    def read_register(self, address, register):
        address = self.validate_address(address)
        register = self.validate_register(register)
        value = self.backend.read_register(address, register)
        result = {'bus': self.bus_number, 'address': address, 'register': register, 'value': value}
        self._emit('i2c_read', result)
        return result

    def write_register(self, address, register, value):
        address = self.validate_address(address)
        register = self.validate_register(register)
        value = self.validate_byte(value)
        self.backend.write_register(address, register, value)
        result = {'bus': self.bus_number, 'address': address, 'register': register, 'value': value}
        self._emit('i2c_register_changed', result)
        return result

    def read_block(self, address, register, length):
        address = self.validate_address(address)
        register = self.validate_register(register)
        length = self.validate_length(length)
        data = self.backend.read_block(address, register, length)
        result = {'bus': self.bus_number, 'address': address, 'register': register, 'data': list(data)}
        self._emit('i2c_read', result)
        return result

    def write_block(self, address, register, data):
        address = self.validate_address(address)
        register = self.validate_register(register)
        data = self.validate_data(data)
        self.backend.write_block(address, register, data)
        result = {'bus': self.bus_number, 'address': address, 'register': register, 'data': data}
        self._emit('i2c_block_changed', result)
        return result

    def state(self):
        return {'bus': self.bus_number, 'mock': self.backend.is_mock}

    def close(self):
        self.backend.close()

# ============================================================
# MODULE: modular\i2c\__init__.py
# ============================================================

from .manager import I2CManager
__all__ = ['I2CManager']
