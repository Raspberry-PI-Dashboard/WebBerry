from gpiozero import (
    DigitalInputDevice,
    DigitalOutputDevice,
    PWMOutputDevice,
)

from config import DEFAULT_PWM_FREQUENCY


class RealGPIOBackend:
    is_mock = False

    def output(self, pin):
        return DigitalOutputDevice(
            pin,
            initial_value=False,
        )

    def input(self, pin):
        return DigitalInputDevice(pin)

    def pwm(self, pin):
        return PWMOutputDevice(
            pin,
            initial_value=0,
            frequency=DEFAULT_PWM_FREQUENCY,
        )

    def close(self):
        pass