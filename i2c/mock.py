class MockI2CBackend:

    is_mock = True

    def __init__(self, bus_number):
        self.bus_number = bus_number

        # Simulated devices:
        #
        # 0x48 -> test device
        # 0x50 -> simulated EEPROM
        self.devices = {
            0x48: bytearray(256),
            0x50: bytearray(256),
        }

        # Test values
        self.devices[0x48][0x00] = 0x42
        self.devices[0x48][0x01] = 0x12

        self.devices[0x50][0x00] = 0xAA

        print(
            f"[MOCK] I2C bus {bus_number} initialized"
        )

    def _device(self, address):

        if address not in self.devices:
            raise OSError(
                f"No I2C device at "
                f"0x{address:02X}"
            )

        return self.devices[address]

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self):
        return sorted(
            self.devices.keys()
        )

    # ------------------------------------------------------------------
    # Byte
    # ------------------------------------------------------------------

    def read_byte(self, address):

        device = self._device(address)

        return device[0]

    def write_byte(
        self,
        address,
        value,
    ):

        device = self._device(address)

        device[0] = value & 0xFF

        print(
            f"[MOCK] I2C "
            f"0x{address:02X} "
            f"write byte "
            f"0x{value:02X}"
        )

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    def read_register(
        self,
        address,
        register,
    ):

        device = self._device(address)

        return device[
            register & 0xFF
        ]

    def write_register(
        self,
        address,
        register,
        value,
    ):

        device = self._device(address)

        register &= 0xFF
        value &= 0xFF

        device[register] = value

        print(
            f"[MOCK] I2C "
            f"0x{address:02X} "
            f"reg=0x{register:02X} "
            f"value=0x{value:02X}"
        )

    # ------------------------------------------------------------------
    # Block
    # ------------------------------------------------------------------

    def read_block(
        self,
        address,
        register,
        length,
    ):

        device = self._device(address)

        register &= 0xFF

        return list(
            device[
                register:
                register + length
            ]
        )

    def write_block(
        self,
        address,
        register,
        data,
    ):

        device = self._device(address)

        register &= 0xFF

        for index, value in enumerate(data):

            position = register + index

            if position >= len(device):
                break

            device[position] = (
                value & 0xFF
            )

        print(
            f"[MOCK] I2C "
            f"0x{address:02X} "
            f"register=0x{register:02X} "
            f"data={data}"
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        pass