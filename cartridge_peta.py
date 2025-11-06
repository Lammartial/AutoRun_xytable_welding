"""
Convenience wrapper for PETA cartridge adapter insert.
"""

from rrc.i2cbus import I2CBus, BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.gpio_pcf8574 import PCF8574 as GPIOExtender


class CartridgePETA:


    def __init__(self, i2c: I2CBus, mux_address: int = 0x70) -> None:
        """
        Initialize the CartridgePETA with the given I2C bus.

        It provides another I2C MUX to select channels on the cartridge.

        Args:
            i2c (I2CBus): The I2C bus to use for communication.
        """

        self._i2c = i2c
        self._onboard_mux = BusMux(self._i2c, address=int(mux_address))  # important to have only ONE instance here
        self.bus_to_mirco = self.get_muxed_i2c_bus_for(1)         # needs a switch to CAN or I2C !
        self.backyard_bus = self.get_muxed_i2c_bus_for(2)
        self.bus_to_gpio = self.get_muxed_i2c_bus_for(8)
        self.gpio = GPIOExtender(self.bus_to_gpio, i2c_address_7bit=0x20, number_of_gpio=8)  # Extender on channel 8 of the cartridge MUX
        # configure GPIO
        self.gpio.write_output("10010000")  # 1 = input or open drain output, 0=output 0
        # -> disable CAN and I2C, Reset MCU (Pin7=1), all MOSFETs OFF


    def reset_mux(self) -> None:
        """Reset the onboard MUX to no channel selected."""
        self._onboard_mux.reset()


    def get_muxed_i2c_bus_for(self, channel: int) -> I2CMuxedBus:
        """
        Get the I2C bus for the specified channel on the cartridge MUX.

        Args:
            channel (int): The channel number to select (1-8).
        Returns:
            Muxed I2C bus for the specified channel.
        """

        return I2CMuxedBus(self._i2c, self._onboard_mux, int(channel))


    def switch_mosfet(self, index: int, state: bool | int) -> None:
        """
        Set the state of the MOSFET at the given index.

        Args:
            index (int): Index of the MOSFET to set.
            state (bool): True to turn on, False to turn off.
        """

        index = int(index)
        if index < 0 or index > 3:
            raise ValueError("Index must be between 0 and 3 for the 4 MOSFETs.")

        pin_no = (index + 0)  # Assuming MOSFETs are connected to GPIO pins 0-3

        if bool(state):
            return self.gpio.set_pin(pin_no)
        else:
            return self.gpio.reset_pin(pin_no)
                


    def select_bus_to_micro(self, bustype: str) -> None:
        """
        Set the state of the SDA line.

        Args:
            bustype (str): Either "CAN" or "I2C". Defaults to none of the two if unknown string passed.
        """

        #mask = self.gpio.get_output_shadow() & ~((0 << 6) | (0 << 5))  # clear both GPIO P5 (CANH) and P6 (SDA)
        if "CAN" in bustype.upper():
            #mask |= ((1 << 6) | (0 << 5))  # Set GPIO P6 (CANH) and P5 (SDA) for CAN
            self.gpio.reset_pin(5)  # disable I2C
            self.gpio.set_pin(6)  # enable CAN
        elif "I2C" in bustype.upper():
            #mask |= ((0 << 6) | (1 << 5))  # Set GPIO P6 (CANH) and P5 (SDA) for I2C
            self.gpio.reset_pin(6)  # disable CAN
            self.gpio.set_pin(5)  # enable I2C
        else:
            self.gpio.reset_pin(6)  # disable I2C
            self.gpio.reset_pin(5)  # disable CAN
            #pass  # open both GPIO P6 and P5 so that NO ONE works!
        #self.gpio.write_output(mask)  # modify the two port pins at the same time


    def switch_some_io(self, pin_number: int, state: bool | int) -> bool:
        """
        Set the state of the IO at the given index.

        Args:
            index (int): Index of the IO to set.
            state (bool): True to turn on, False to turn off.
        """

        pin_number = int(pin_number)
        if pin_number not in (4, 7):
            raise ValueError("Index must be either 4 or 7 for the 4 GPIOs.")

        if bool(state):
            return self.gpio.set_pin(pin_number)
        else:
            return self.gpio.reset_pin(pin_number)


    # convenience functions
    def disable_mcu(self) -> bool:
        return self.switch_some_io(7, 1)  # 1 on GPIO pulls down the RESET

    def enable_mcu(self) -> bool:
        return self.switch_some_io(7, 0)  # 0 on GPIO releases the RESET



# END OF FILE