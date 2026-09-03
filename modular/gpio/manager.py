from config import (
    ALLOWED_PINS,
    DEFAULT_PWM_FREQUENCY,
    MOCK_GPIO,
)

from .mock import MockGPIOBackend


class GPIOManager:

    MODES = {"input", "output", "pwm"}

    def __init__(self, event_callback=None):
        self.outputs = {}
        self.inputs = {}
        self.pwm_outputs = {}
        self.modes = {}

        self.event_callback = event_callback
        self.backend = self._create_backend()

    def _create_backend(self):
        if MOCK_GPIO:
            return MockGPIOBackend()

        try:
            from .real import RealGPIOBackend
            return RealGPIOBackend()
        except ImportError:
            print(
                "[GPIO] gpiozero unavailable, "
                "falling back to mock"
            )
            return MockGPIOBackend()

    def _emit(self, event, data):
        if self.event_callback:
            self.event_callback(event, data)

    def validate_pin(self, pin):
        try:
            pin = int(pin)
        except (TypeError, ValueError):
            raise ValueError("Invalid GPIO pin")

        if pin not in ALLOWED_PINS:
            raise ValueError(
                f"GPIO {pin} is not allowed"
            )

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

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def mode(self, pin, mode):
        pin = self.validate_pin(pin)

        if mode not in self.MODES:
            raise ValueError(
                f"Invalid GPIO mode: {mode}"
            )

        if self.modes.get(pin) == mode:
            return {
                "pin": pin,
                "mode": mode,
            }

        # Release any existing device for this pin.
        if pin in self.outputs:
            self.outputs[pin].close()
            del self.outputs[pin]

        if pin in self.inputs:
            self.inputs[pin].close()
            del self.inputs[pin]

        if pin in self.pwm_outputs:
            self.pwm_outputs[pin].close()
            del self.pwm_outputs[pin]

        if mode == "input":
            self._get_input(pin)

        elif mode == "output":
            self._get_output(pin)

        elif mode == "pwm":
            self._get_pwm(pin)

        self.modes[pin] = mode

        result = {
            "pin": pin,
            "mode": mode,
        }

        self._emit(
            "pin_mode_changed",
            result,
        )

        return result

    def _require_mode(self, pin, expected):
        pin = self.validate_pin(pin)

        actual = self.modes.get(pin)

        if actual != expected:
            raise ValueError(
                f"GPIO {pin} is in mode "
                f"{actual or 'unset'}, expected {expected}"
            )

    # ------------------------------------------------------------------
    # Digital
    # ------------------------------------------------------------------

    def set(self, pin, value):
        pin = self.validate_pin(pin)
        self._require_mode(pin, "output")

        output = self._get_output(pin)
        output.value = bool(value)

        result = {
            "pin": pin,
            "value": bool(output.value),
        }

        self._emit("pin_changed", result)

        return result

    def toggle(self, pin):
        pin = self.validate_pin(pin)
        self._require_mode(pin, "output")

        output = self._get_output(pin)
        output.toggle()

        result = {
            "pin": pin,
            "value": bool(output.value),
        }

        self._emit("pin_changed", result)

        return result

    def read(self, pin):
        pin = self.validate_pin(pin)
        self._require_mode(pin, "input")

        input_device = self._get_input(pin)

        return {
            "pin": pin,
            "value": bool(input_device.value),
        }

    # ------------------------------------------------------------------
    # PWM
    # ------------------------------------------------------------------

    def pwm_set(self, pin, duty_cycle, frequency=None):
        pin = self.validate_pin(pin)
        self._require_mode(pin, "pwm")

        duty_cycle = float(duty_cycle)

        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError(
                "duty_cycle must be between 0.0 and 1.0"
            )

        if frequency is None:
            frequency = DEFAULT_PWM_FREQUENCY

        frequency = int(frequency)

        if frequency <= 0:
            raise ValueError(
                "frequency must be positive"
            )

        pwm = self._get_pwm(pin)

        pwm.frequency = frequency
        pwm.value = duty_cycle

        result = {
            "pin": pin,
            "duty_cycle": float(pwm.value),
            "frequency": int(pwm.frequency),
        }

        self._emit("pwm_changed", result)

        return result

    def pwm_stop(self, pin):
        pin = self.validate_pin(pin)
        self._require_mode(pin, "pwm")

        pwm = self._get_pwm(pin)

        pwm.value = 0

        result = {
            "pin": pin,
            "duty_cycle": 0.0,
            "frequency": int(pwm.frequency),
        }

        self._emit("pwm_changed", result)

        return result

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def state(self):
        pins = []

        for pin in sorted(ALLOWED_PINS):
            digital_value = False
            pwm_value = 0.0
            pwm_frequency = DEFAULT_PWM_FREQUENCY

            if pin in self.outputs:
                digital_value = bool(
                    self.outputs[pin].value
                )

            if pin in self.pwm_outputs:
                pwm = self.pwm_outputs[pin]
                pwm_value = float(pwm.value)
                pwm_frequency = int(pwm.frequency)

            pins.append({
                "pin": pin,
                "mode": self.modes.get(pin),
                "digital": {
                    "value": digital_value,
                },
                "pwm": {
                    "active": self.modes.get(pin) == "pwm",
                    "duty_cycle": pwm_value,
                    "frequency": pwm_frequency,
                },
            })

        return pins

    def close(self):
        for device in self.outputs.values():
            device.close()

        for device in self.inputs.values():
            device.close()

        for device in self.pwm_outputs.values():
            device.close()

        self.backend.close()