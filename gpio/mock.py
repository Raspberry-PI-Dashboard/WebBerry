from config import DEFAULT_PWM_FREQUENCY


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