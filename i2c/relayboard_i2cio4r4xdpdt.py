from gpio_mcp23008 import MCP23008


class RelayBoard4Relay4GPIO:
    """A class for 4 relay + 4 GPIO controller by NCD (PR2B-10)

    This board has 4 relays that are numbered 1, 2, 3 and 4, and it also has 4 GPIOs that are numbered 4, 5, 6 and 7.
    The numbering of the GPIOs seems weird, but that's how they are labeled on the board. Use theese numbers to
    address the right GPIO or relay in this class.
    """
    r1 = 0
    r2 = 1
    r3 = 2
    r4 = 3
    relay_dict = {1: r1, 2: r2, 3: r3, 4: r4}
    gpio4 = 4
    gpio5 = 5
    gpio6 = 6
    gpio7 = 7
    gpio_dict = {4: gpio4, 5: gpio5, 6: gpio6, 7: gpio7}

    def __init__(self, i2c_port, i2c_address_7bit):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c_port: The I2CPort instance this board is connected to
            i2c_address_7bit: The board's 7-bit I2C address
        """
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.gpio = MCP23008(i2c_port, self.i2c_address_7bit)

        # Setup relay outputs
        for relay_pin in RelayBoard4Relay4GPIO.relay_dict.values():
            self.gpio.set_pin_as_output(relay_pin)

    def enable_relay_n(self, relay_n: int):
        """Enable relay number relay_n.

        Args:
            relay_n (int): Index of the relay that should be enabled .

        Raises:
            ValueError: If relay_n is invalid (< 1 or > 4)
        """
        relay_n = int(relay_n)
        self.__validate_relay_pin(relay_n)
        self.gpio.set_pin(RelayBoard4Relay4GPIO.relay_dict[relay_n])

    def disable_relay_n(self, relay_n: int):
        """Disable relay number relay_n.

        Args:
            relay_n (int): Index of the relay that should be disabled.

        Raises:
            ValueError: If relay_n is invalid (< 1 or > 4)
        """
        relay_n = int(relay_n)
        self.__validate_relay_pin(relay_n)
        self.gpio.reset_pin(RelayBoard4Relay4GPIO.relay_dict[relay_n])
        
    def set_gpio_n_as_output(self, gpio_n: int):
        """Configure the specified GPIO as an output.

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.set_pin_as_output(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def set_gpio_n_as_input(self, gpio_n: int):
        """Configure the specified GPIO as an input.

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.set_pin_as_input(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def enable_pullup_for_gpio_n(self, gpio_n: int):
        """Enable a 100k pullup for specified GPIO if it is configured as an input.

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.enable_pullup(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def disable_pullup_for_gpio_n(self, gpio_n: int):
        """Disable the pullup for specified GPIO.

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.disable_pullup(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def set_gpio_n_high(self, gpio_n: int):
        """Set the specified GPIO to a logic high level (5 V).

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.set_pin(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def set_gpio_n_low(self, gpio_n: int):
        """Set the specified GPIO to a logic low level (GND).

        Args:
            gpio_n (int): Index of the GPIO

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        self.gpio.reset_pin(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])
        
    def read_gpio_n(self, gpio_n: int) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n (int): Index of the GPIO

        Returns:
            bool: The logic level of the GPIO.

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        gpio_n = int(gpio_n)
        self.__validate_gpio_pin(gpio_n)
        return self.gpio.get_pin(RelayBoard4Relay4GPIO.gpio_dict[gpio_n])

    def __validate_relay_pin(self, relay_n: int):
        if relay_n not in RelayBoard4Relay4GPIO.relay_dict.keys():
            raise ValueError(f"Relay pin number for the relay board at 0x{self.i2c_address_7bit:02X} must be betwween"
                             f"1 and {max(RelayBoard4Relay4GPIO.relay_dict.keys())}. You selected {relay_n}")

    def __validate_gpio_pin(self, gpio_n: int):
        if gpio_n not in RelayBoard4Relay4GPIO.gpio_dict.keys():
            raise ValueError(f"GPIO pin number for the relay board at 0x{self.i2c_address_7bit:02X} must be betwween"
                             f"1 and {max(RelayBoard4Relay4GPIO.gpio_dict.keys())}. You selected {gpio_n}")
