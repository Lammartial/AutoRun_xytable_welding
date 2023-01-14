from rrc.i2cbus import I2CBase

class MCP23008:
    """A class to control the MCP23008 8-bit I2C I/O Expander.

    https://www.microchip.com/en-us/product/MCP23008
    """
    number_of_pins = 8
    IODIR = 0x00
    IPOL = 0x01
    GPINTEN = 0x02
    DEFVAL = 0x03
    INTCON = 0x04
    IOCON = 0x05
    GPPU = 0x06
    INTF = 0x07
    INTCAP = 0x08
    GPIO = 0x09
    OLAT = 0x0A

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x20):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c: The I2CPort instance this IC is connected to
            i2c_address_7bit: The IC's 7-bit I2C address
        """
        self.i2c = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)

    def set_pin(self, pin_n: int):
        """Set the specified pin to a logic high level.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_gpio_register()
        value |= (1 << pin_n)
        self.set_gpio_register(value)

    def reset_pin(self, pin_n: int):
        """Set the specified pin to a logic low level.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_gpio_register()
        value &= ~(1 << pin_n)
        self.set_gpio_register(value)

    def get_pin(self, pin_n: int) -> bool:
        """Read the logic level of the specified pin.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Returns:
            bool: The logic level of the pin.

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_gpio_register()
        return bool(value & (1 << pin_n))

    def enable_pullup(self, pin_n: int):
        """Enables a 100k pullup on the specified pin, if it is configured as an input.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_gppu_register()
        value |= (1 << pin_n)
        self.set_gppu_register(value)

    def disable_pullup(self, pin_n: int):
        """Disables the pullup on the specified pin.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_gppu_register()
        value &= ~(1 << pin_n)
        self.set_gppu_register(value)

    def set_pin_as_output(self, pin_n: int):
        """Configure the specified pin as an output.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_iodir_register()
        value &= ~(1 << pin_n)
        self.set_iodir_register(value)

    def set_pin_as_input(self, pin_n: int):
        """Configure the specified pin as an input.

        Args:
            pin_n (int): Index of the pin that should be modified. Must be in [0, 7]

        Raises:
            ValueError: If the pin_n is invalid (< 0 or > 7).
        """
        pin_n = int(pin_n)
        self.__validate_pin_number(pin_n)
        value = self.get_iodir_register()
        value |= (1 << pin_n)
        self.set_iodir_register(value)

    def set_iodir_register(self, value: int):
        value = int(value)
        self.__write_register(MCP23008.IODIR, value)

    def get_iodir_register(self) -> int:
        return self.__read_register(MCP23008.IODIR)

    def set_gpio_register(self, value: int):
        value = int(value)
        self.__write_register(MCP23008.GPIO, value)

    def get_gpio_register(self) -> int:
        return self.__read_register(MCP23008.GPIO)

    def set_gppu_register(self, value: int):
        value = int(value)
        self.__write_register(MCP23008.GPPU, value)

    def get_gppu_register(self) -> int:
        return self.__read_register(MCP23008.GPPU)

    def __write_register(self, register: int, value: int):
        self.i2c.writeto(self.i2c_address_7bit, bytearray([register, value]))

    def __read_register(self, register: int):
        value = self.i2c.readfrom_mem(self.i2c_address_7bit, bytearray([register]), 1)
        return value[0]

    def __validate_pin_number(self, pin_n: int):
        if pin_n < 0 or pin_n >= MCP23008.number_of_pins:
            raise ValueError(f"Invalid pin number for MCP23008 at address 0x{self.i2c_address_7bit:02X}. Must be "
                             f"between 0 and {self.i2c_address_7bit-1}")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    pass


# END OF FILE