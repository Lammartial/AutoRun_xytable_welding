from rrc.gpio_pca9536 import PCA9536
from rrc.i2cbus import I2CBase


class CellStackRelayBoard():
    """A class for I2C Adapter Cell Stack Tester controlled by NCD (PR2B-10)

    This board has 4 GPIOs that are numbered from 1 to 4.
    Use theese numbers to address the right GPIO in this class.
    Uses PCA9536 Remote 4-Bit I2C and SMBus I/O Expander.
    """
    gpio_pin_0 = 0       
    gpio_pin_1 = 1
    gpio_pin_2 = 2
    gpio_pin_3 = 3
    input_dict = {1: gpio_pin_0, 2: gpio_pin_1, 3: gpio_pin_2, 4: gpio_pin_3}

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x41):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c: The I2CPort instance this board is connected to
            i2c_address_7bit: The board's 7-bit I2C address
        """
        self.gpio = PCA9536(i2c, int(i2c_address_7bit))
        #super().__init__(i2c, int(i2c_address_7bit))    
        # Setup PCA9536 GPIO
        self.gpio.reset_inversion()
        self.gpio.set_pin_as_input(self.gpio_pin_0)
        self.gpio.set_pin_as_input(self.gpio_pin_1)
        self.gpio.set_pin_as_input(self.gpio_pin_2)
        self.gpio.set_pin_as_input(self.gpio_pin_3)

    def __str__(self) -> str:
        return f"CorePackRelayBoard using {self.gpio}"

    def __repr__(self) -> str:
        return f"CorePackRelayBoard({repr(self.gpio.i2c)}, i2c_address_7bit={self.gpio.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def read_input(self, input_n: int) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n (int): Index of the GPIO

        Returns:
            bool: The logic level of the GPIO.

        Raises:
            ValueError: If gpio_n is invalid
        """
        input_n = int(input_n)
        self.__validate_gpio_pin(input_n)
        return self.gpio.get_pin(self.input_dict[input_n])

    def __validate_gpio_pin(self, input_n: int):
        if input_n not in self.input_dict.keys():
            raise ValueError(f"Input number for {str(self)} must be 1 ... 4. You selected {input_n}")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import BusMux, I2CMuxedBus
    i2c = I2CPort("172.21.101.31")
    mux = BusMux(i2c, 0x77)
    bus = I2CMuxedBus(i2c, mux, 7)
    ib = CellStackRelayBoard(bus)

    i2c.close()
    pass

# END OF FILE
