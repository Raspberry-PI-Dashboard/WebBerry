from smbus2 import SMBus


class RealI2CBackend:

    is_mock = False

    def __init__(self, bus_number):
        self.bus_number = bus_number
        self.bus = SMBus(bus_number)

    def scan(self):
        devices = []

        for address in range(0x03, 0x78):
            try:
                self.bus.write_quick(address)
                devices.append(address)
            except OSError:
                pass

        return devices

    def read_byte(self, address):
        return self.bus.read_byte(address)

    def write_byte(self, address, value):
        self.bus.write_byte(
            address,
            value,
        )

    def read_register(
        self,
        address,
        register,
    ):
        return self.bus.read_byte_data(
            address,
            register,
        )

    def write_register(
        self,
        address,
        register,
        value,
    ):
        self.bus.write_byte_data(
            address,
            register,
            value,
        )

    def read_block(
        self,
        address,
        register,
        length,
    ):
        return self.bus.read_i2c_block_data(
            address,
            register,
            length,
        )

    def write_block(
        self,
        address,
        register,
        data,
    ):
        self.bus.write_i2c_block_data(
            address,
            register,
            list(data),
        )

    def close(self):
        self.bus.close()