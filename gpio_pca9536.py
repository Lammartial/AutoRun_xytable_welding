from rrc.i2cbus import I2CBase

class PCA9536:
    """
    A class to control the PCA9536 4-bit I2C I/O Expander.

    https://www.ti.com/product/PCA9536
    """
    reg_input_port = 0x00
    reg_output_port = 0x01
    reg_polarity_inversion = 0x02
    reg_configuration = 0x03
    reg_list = [reg_input_port, reg_output_port, reg_polarity_inversion, reg_configuration]
    gpio_list = [0, 1, 2, 3]

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x41):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c: The I2CPort instance this IC is connected to
            i2c_address_7bit: The IC's 7-bit I2C address
        """
        self.i2c = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)

    def __str__(self) -> str:
        return f"PCA9536 GPIO device with address {self.i2c_address_7bit:02x} on {self.i2c}"

    def __repr__(self) -> str:
        return f"PCA9536({repr(self.i2c)}, i2c_address_7bit={self.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def set_gpio_n_as_input(self, gpio_n: int):
        """Configure the GPIO with the index n (starts at 0) as an input with a 100k pullup.

        Args:
            gpio_n int: Index of the GPIO to configure [0, 3]
        """
        gpio_n = self.__validate_gpio_number(gpio_n)
        self.__set_bit_high(PCA9536.reg_configuration, gpio_n)

    def set_gpio_n_as_output(self, gpio_n: int):
        """Configure the GPIO with the index n (starts at 0) as an output.

        Args:
            gpio_n int: Index of the GPIO to configure [0, 3]
        """
        gpio_n = self.__validate_gpio_number(gpio_n)
        self.__set_bit_low(PCA9536.reg_configuration, gpio_n)

    def set_gpio_n_high(self, gpio_n: int):
        """Set the specified GPIO to a logic high level (5 V).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO [0, 3]
        """
        gpio_n = self.__validate_gpio_number(gpio_n)
        self.__set_bit_high(PCA9536.reg_output_port, gpio_n)

    def set_gpio_n_low(self, gpio_n):
        """Set the specified GPIO to a logic low level (Gnd).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO [0, 3]
        """
        gpio_n = self.__validate_gpio_number(gpio_n)
        self.__set_bit_low(PCA9536.reg_output_port, gpio_n)

    def read_gpio_n(self, gpio_n) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n int: Index of the GPIO [0, 3]

        Returns:
            bool: The logic level of the GPIO.
        """
        gpio_n = self.__validate_gpio_number(gpio_n)
        reg_value = self.__get_register(PCA9536.reg_input_port)
        return bool(reg_value & (1 << gpio_n))

    def __set_bit_high(self, register: int, bit_n: int):
        # Do a read-modify-write to set bit_n of the register to 1.
        reg_value = self.__get_register(register)
        reg_value |= (1 << bit_n)
        self.__set_register(register, reg_value)

    def __set_bit_low(self, register: int, bit_n: int):
        # Do a read-modify-write to set bit_n of the register to 0.
        reg_value = self.__get_register(register)
        reg_value &= ~(1 << bit_n)
        self.__set_register(register, reg_value)

    def __set_register(self, register: int, value: int):
        # Set the register in the IC to a certain value.
        register = self.__validate_control_register(register)

        value = int(value)
        if not (0 <= value <= 15):
            raise ValueError(f"Invalid register value for GPIO board. Must be between 0 and 15. You sent {value}. "
                             f"({self.__repr__()})")

        data = bytearray([register, value])
        self.i2c.writeto(self.i2c_address_7bit, data)

    def __get_register(self, register: int) -> int:
        # Read a register from the IC.
        register = self.__validate_control_register(register)

        data = bytearray([register])
        value = self.i2c.readfrom_mem(self.i2c_address_7bit, data, 1)

        try:
            value = value[0]
        except IndexError:
            raise IndexError(f"Didn't receive enough bytes for __get_register function from {self.__repr__()}.")

        return value

    def __validate_control_register(self, register: int):
        # Make sure register is an int and it's a valid register index.
        register = int(register)
        if register not in PCA9536.reg_list:
            raise ValueError(f"The register 0x{register:02X} is not in the list of available registers of the GPIO board"
                             f" ({PCA9536.reg_list}). ({self.__repr__()})")
        else:
            return register

    def __validate_gpio_number(self, gpio_n: int) -> int:
        # Make sure gpio_n is an int and it's a valid gpio index.
        gpio_n = int(gpio_n)
        if gpio_n not in PCA9536.gpio_list:
            raise ValueError(f"Pin {gpio_n} is not in the list of available pins of the GPIO board ({PCA9536.gpio_list}). "
                             f"({self.__repr__()})")
        else:
            return gpio_n


if __name__ == '__main__':
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CMuxedBus, BusMux

    i2c_p = I2CPort("192.168.1.119")
    mux = BusMux(i2c_p)
    mux.setChannelMask(0xff)

    gpio = PCA9536(i2c_p)

    gpio.set_gpio_n_as_input(0)

    gpio.set_gpio_n_as_output(1)
    gpio.set_gpio_n_low(1)

    print(gpio.read_gpio_n(0))
