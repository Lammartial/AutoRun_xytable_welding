from rrc.gpio_pca9536 import PCA9536
from rrc.i2cbus import I2CBase


class CorePackRelayBoard():
    """A class for Corepack Tester Adapter controlled by NCD (PR2B-10)

    This board has 2 relays that are numbered 1 and 4, and it also has 2 GPIOs that are numbered 2 and 3.
    Use theese numbers to address the right GPIO or relay in this class.
    Uses PCA9536 Remote 4-Bit I2C and SMBus I/O Expander.
    Pin 1 (relay) - T-Pin Switch Relay, necessary for RRC3570 (0 - T-Pin Open, 1 - T-Pin shorted to GND)
    Pin 2 (input) - 300R Detection (0 - battery inserted, 1 - no battery)
    Pin 3 (input) - RRC3570 Detection (0 - RRC3570 inserted, 1 - no RRC3570 battery)
    Pin 4 (relay) - PSU/Hioki Relay (0 - Hioki Sense, 1 - PSU Sense)
    """
    relay_3570_switch = 0       
    inp_300ohm_detect = 1
    inp_3570_detect   = 2
    relay_meas        = 3
    relay_dict = {1: relay_3570_switch, 4: relay_meas}
    input_dict = {2: inp_300ohm_detect, 3: inp_3570_detect}

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
        self.gpio.set_pin_as_output(self.relay_3570_switch)
        self.gpio.set_pin_as_output(self.relay_meas)
        self.gpio.set_pin_as_input(self.inp_300ohm_detect)
        self.gpio.set_pin_as_input(self.inp_3570_detect)
        self.reset_relay(1)
        self.reset_relay(4)

    def __str__(self) -> str:
        return f"CorePackRelayBoard using {self.gpio}"

    def __repr__(self) -> str:
        return f"CorePackRelayBoard({repr(self.gpio.i2c)}, i2c_address_7bit={self.gpio.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def set_relay(self, relay_n: int):
        """Set relay number relay_n.

        Args:
            relay_n (int): Index of the relay.

        Raises:
            ValueError: If relay_n is invalid (!=1 or !=4)
        """
        relay_n = int(relay_n)
        self.__validate_relay(relay_n)
        self.gpio.set_pin(self.relay_dict[relay_n])

    def reset_relay(self, relay_n: int):
        """Reset relay number relay_n.

        Args:
            relay_n (int): Index of the relay.

        Raises:
            ValueError: If If relay_n is invalid (!=1 or !=4)
        """
        relay_n = int(relay_n)
        self.__validate_relay(relay_n)
        self.gpio.reset_pin(self.relay_dict[relay_n])

    def read_input(self, input_n: int) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n (int): Index of the GPIO

        Returns:
            bool: The logic level of the GPIO.

        Raises:
            ValueError: If gpio_n is invalid (< 4 or > 7)
        """
        input_n = int(input_n)
        self.__validate_gpio_pin(input_n)
        return self.gpio.get_pin(self.input_dict[input_n])

    def __validate_relay(self, relay_n: int):
        if relay_n not in self.relay_dict.keys():
            raise ValueError(f"Relay pin number for the {str(self)} must be 1 or 4. You selected {relay_n}")

    def __validate_gpio_pin(self, input_n: int):
        if input_n not in self.input_dict.keys():
            raise ValueError(f"Input number for {str(self)} must be 2 or 3. You selected {input_n}")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import BusMux, I2CMuxedBus
    i2c = I2CPort("172.21.101.31")
    mux = BusMux(i2c, 0x77)
    bus = I2CMuxedBus(i2c, mux, 7)
    rb = CorePackRelayBoard(bus)

    print(rb.gpio.get_polarity_register())

    rb.set_relay(4)

    print(rb.read_input(2))
    print(rb.read_input(3))

    rb.reset_relay(4)

    i2c.close()
    pass

# END OF FILE
