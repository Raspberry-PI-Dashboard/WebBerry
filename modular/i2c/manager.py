from config import I2C_BUS, I2C_MOCK

from .mock import MockI2CBackend


class I2CManager:

    def __init__(self, event_callback=None):
        self.bus_number = I2C_BUS
        self.event_callback = event_callback
        self.backend = self._create_backend()

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------

    def _create_backend(self):

        if I2C_MOCK:
            return MockI2CBackend(
                self.bus_number
            )

        try:
            from .real import RealI2CBackend

            return RealI2CBackend(
                self.bus_number
            )

        except ImportError:
            print(
                "[I2C] smbus2 unavailable, "
                "falling back to mock"
            )

            return MockI2CBackend(
                self.bus_number
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _emit(self, event, data):
        if self.event_callback:
            self.event_callback(
                event,
                data,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_address(address):
        try:
            address = int(address)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid I2C address"
            )

        if not 0x03 <= address <= 0x77:
            raise ValueError(
                "I2C address must be between "
                "0x03 and 0x77"
            )

        return address

    @staticmethod
    def validate_byte(value, name="value"):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid {name}"
            )

        if not 0 <= value <= 0xFF:
            raise ValueError(
                f"{name} must be between "
                "0 and 255"
            )

        return value

    @staticmethod
    def validate_register(register):
        return I2CManager.validate_byte(
            register,
            "register",
        )

    @staticmethod
    def validate_length(length):
        try:
            length = int(length)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid block length"
            )

        if not 1 <= length <= 32:
            raise ValueError(
                "I2C block length must be "
                "between 1 and 32"
            )

        return length

    @staticmethod
    def validate_data(data):
        if not isinstance(data, list):
            raise ValueError(
                "data must be a list"
            )

        if len(data) > 32:
            raise ValueError(
                "I2C block cannot exceed 32 bytes"
            )

        return [
            I2CManager.validate_byte(
                value,
                "data value",
            )
            for value in data
        ]

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self):

        addresses = self.backend.scan()

        result = {
            "bus": self.bus_number,
            "addresses": addresses,
        }

        self._emit(
            "i2c_scan",
            result,
        )

        return result

    # ------------------------------------------------------------------
    # Byte operations
    # ------------------------------------------------------------------

    def read_byte(self, address):

        address = self.validate_address(
            address
        )

        value = self.backend.read_byte(
            address
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "value": value,
        }

        self._emit(
            "i2c_read",
            result,
        )

        return result

    def write_byte(
        self,
        address,
        value,
    ):

        address = self.validate_address(
            address
        )

        value = self.validate_byte(
            value
        )

        self.backend.write_byte(
            address,
            value,
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "value": value,
        }

        self._emit(
            "i2c_write",
            result,
        )

        return result

    # ------------------------------------------------------------------
    # Register operations
    # ------------------------------------------------------------------

    def read_register(
        self,
        address,
        register,
    ):

        address = self.validate_address(
            address
        )

        register = self.validate_register(
            register
        )

        value = self.backend.read_register(
            address,
            register,
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "register": register,
            "value": value,
        }

        self._emit(
            "i2c_read",
            result,
        )

        return result

    def write_register(
        self,
        address,
        register,
        value,
    ):

        address = self.validate_address(
            address
        )

        register = self.validate_register(
            register
        )

        value = self.validate_byte(
            value
        )

        self.backend.write_register(
            address,
            register,
            value,
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "register": register,
            "value": value,
        }

        self._emit(
            "i2c_register_changed",
            result,
        )

        return result

    # ------------------------------------------------------------------
    # Block operations
    # ------------------------------------------------------------------

    def read_block(
        self,
        address,
        register,
        length,
    ):

        address = self.validate_address(
            address
        )

        register = self.validate_register(
            register
        )

        length = self.validate_length(
            length
        )

        data = self.backend.read_block(
            address,
            register,
            length,
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "register": register,
            "data": list(data),
        }

        self._emit(
            "i2c_read",
            result,
        )

        return result

    def write_block(
        self,
        address,
        register,
        data,
    ):

        address = self.validate_address(
            address
        )

        register = self.validate_register(
            register
        )

        data = self.validate_data(
            data
        )

        self.backend.write_block(
            address,
            register,
            data,
        )

        result = {
            "bus": self.bus_number,
            "address": address,
            "register": register,
            "data": data,
        }

        self._emit(
            "i2c_block_changed",
            result,
        )

        return result

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def state(self):
        return {
            "bus": self.bus_number,
            "mock": self.backend.is_mock,
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self.backend.close()