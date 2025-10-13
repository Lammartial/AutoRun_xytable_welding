from time import sleep
from math import ceil, floor
from struct import pack, unpack
from binascii import hexlify
from rrc.i2cbus import I2CBase



#--------------------------------------------------------------------------------------------------

# helper to get a bit pattern from a bitlist of integers
def shifting_plus(bitlist: tuple | list) -> int:
    out = 0
    for bit in bitlist:
        out = out * 2 + (int(bit) & 0x01)
    return out

#--------------------------------------------------------------------------------------------------

class GPIO_BASE:
    """Base class for GPIO expanders."""

    def __init__(self,
                 i2c: I2CBase,
                 i2c_address_7bit: int,
                 number_of_gpio: int,
                 init_shadow_from_ic: bool,
                 retry_limit: int = 10,
                 pause_us: int = 5000) -> None:
        """_summary_

        Args:
            i2c (I2CBase): _description_
            i2c_address_7bit (int): _description_
            number_of_gpio (int): _description_
            init_shadow_from_ic (bool): _description_
            retry_limit (int, optional): _description_. Defaults to 10.
            pause_us (int, optional): _description_. Defaults to 5000.
        """

        self.bus = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.retry_limit = retry_limit
        self.pause_us = pause_us
        assert ((number_of_gpio >= 1) and (number_of_gpio <= 64)), "Maximum number of GPIO pins is 64."
        self._number_of_gpio = number_of_gpio  # max 64 !!
        self._number_of_gpio_mask = (1 << number_of_gpio) - 1
        # calculate the register addresses
        self.REG_INPUT = 0  * ceil(number_of_gpio / 8)
        self.REG_OUTPUT = 1 * ceil(number_of_gpio / 8)
        self.REG_POLARITY = 2 * ceil(number_of_gpio / 8)
        self.REG_CONFIGURATION = 3 * ceil(number_of_gpio / 8)
        # prepare shadow registers
        self._shadow_regs = {
            self.REG_OUTPUT: self.read_output() if init_shadow_from_ic else 0,  # can be up to 64 bits !
            self.REG_POLARITY: self.read_polarity() if init_shadow_from_ic else 0,  # can be up to 64 bits !
            self.REG_CONFIGURATION: self.read_direction() if init_shadow_from_ic else self._number_of_gpio_mask,  # power-up pins input
        }

    #--------------------------------------------
    # private functions
    def _write_helper(self, register: int, value: int) -> bool:
        """Write any of the r/w registers and keeps track of shadow registers for all but input.

        Args:
            register (_type_): _description_
            value (int): _description_

        Raises:
            ValueError: _description_
            ValueError: _description_

        Returns:
            bool: _description_
        """

        value = int(value)
        register = int(register)
        # prepare the value into a data array
        b = value.to_bytes(ceil(self._number_of_gpio / 8), "little")
        r = register.to_bytes(1, "little", signed=False)  # only 8 bits of register
        buf = bytearray(r + b)
        for n in range(0, self.retry_limit):
            try:
                wlen = self.bus.writeto(self.i2c_address_7bit, buf)
                ok: bool = len(buf) == wlen
                if ok:
                    # we can store the value
                    self._shadow_regs[register] = value
                return ok
            except OSError:
                if n == self.retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")


    def _read_helper(self, register: int) -> int:
        r = register.to_bytes(1, "little")  # only 8 bits of register
        length = ceil(self._number_of_gpio / 8)
        for n in range(0, self.retry_limit):
            try:
                buf = self.bus.readfrom_mem(self.i2c_address_7bit, bytearray(r), length)  # does 3 retries with 1ms pause between
                print(hexlify(buf).decode())  # DEBUG
                try:
                    value = int.from_bytes(buf, "little", signed=False) & self._number_of_gpio_mask
                    self._shadow_regs[register] = value
                except IndexError:
                    raise IndexError(f"Didn't receive correct number of bytes from {self}.")
                return value  # this is the good exit
            except OSError as ex:
                if n == self.retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")


    #--------------------------------------------
    # public generic functions

    def get_output_shadow(self) -> int:
        """Get the shadow register of the output register.

        Returns:
            int: Current value of the output shadow register.
        """
        return self._shadow_regs[self.REG_OUTPUT]


    def get_configuration_shadow(self) -> int:
        """Get the shadow register of the configuration register.

        Returns:
            int: Current value of the configuration shadow register.
        """
        return self._shadow_regs[self.REG_CONFIGURATION]


    def configure_pins(self,
                       pin_io: tuple | str,
                       invert_input: tuple | str,
                       preset_output: None | tuple | str = None) -> bool:
        """The Configuration register (register 3) configures the directions of the I/O pins.
        If a bit in this register is set to 1, the corresponding port pin is enabled as an input
        with high-impedance output driver. If a bit in this register is cleared to 0,
        the corresponding port pin is enabled as an output.

        Length depends on number of GPIO.

        Args:
            pin_io (tuple | str):  tuple of 0 | 1, 0=pin is output, 1=pin is input, length depends on number of GPIO
            invert_input (tuple | str):   tuple of 0 | 1, 0=pin is read normal, 1=pin is read inverted, length depends on number of GPIO
            preset_output (tuple | str):  tuple of 0 | 1, preset if outout, length depends on number of GPIO
        """

        if len(pin_io) != self._number_of_gpio:
            raise ValueError(f"Parameter 'pin_as_output' must be tuple of {self._number_of_gpio} integers or a string of length {self._number_of_gpio}.")
        if len(invert_input) != self._number_of_gpio:
            raise ValueError(f"Parameter 'invert_input' must be tuple of {self._number_of_gpio} integers or a string of length {self._number_of_gpio}.")
        if preset_output is not None:
            if len(preset_output) != self._number_of_gpio:
                raise ValueError(f"Parameter 'output' must be tuple if {self._number_of_gpio} integers or a string of length {self._number_of_gpio}.")
            _output = shifting_plus(preset_output)
            self._write_helper(self.REG_OUTPUT, _output)
        _polarity = shifting_plus(invert_input)
        _config = shifting_plus(pin_io)
        ok1 = self._write_helper(self.REG_POLARITY, _polarity)
        ok2 = self._write_helper(self.REG_CONFIGURATION, _config)
        return ok1 and ok2



    def set_pin_as_input(self, pin_number: int) -> bool:
        """Configure the GPIO with the index n (starts at 0) as an input with a 100k pullup.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _config = self._shadow_regs[self.REG_CONFIGURATION] | (1 << (pin_number & self._number_of_gpio_mask))  # set corresponding bit in configuration
        return self._write_helper(self.REG_CONFIGURATION, _config)


    def set_pin_as_output(self, pin_number: int) -> bool:
        """Configure the GPIO with the index n (starts at 0) as an output.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _config = self._shadow_regs[self.REG_CONFIGURATION] & ~(1 << (pin_number & self._number_of_gpio_mask))  # clear corresponding bit in configuration
        return self._write_helper(self.REG_CONFIGURATION, _config)


    def get_pin(self, pin_number: int) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        Returns:
            bool: The logic level of the GPIO.
        """

        pin_number = int(pin_number)
        reg_value = self.read_input()
        return bool(reg_value & (1 << (pin_number & self._number_of_gpio_mask)))


    def set_pin(self, pin_number: int) -> bool:
        """Set the specified GPIO to a logic high level (5 V).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _value = self._shadow_regs[self.REG_OUTPUT] | (1 << (pin_number & self._number_of_gpio_mask))  # set corresponding bit
        return self._write_helper(self.REG_OUTPUT, _value)


    def reset_pin(self, pin_number: int) -> bool:
        """Set the specified GPIO to a logic low level (Gnd).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _value = self._shadow_regs[self.REG_OUTPUT] & ~(1 << (pin_number & self._number_of_gpio_mask))  # clear corresponding bit
        return self._write_helper(self.REG_OUTPUT, _value)



    #--------------------------------------------
    # virtual functions to be implemented in derived classes
    def read_input(self) -> int:
        """Read the input register.

        Returns:
            int: Current value of the input register.
        """
        raise NotImplementedError("This is a base class. Use a derived class.")


    def read_output(self) -> int:
        """Read the output register.

        Returns:
            int: Current value of the output register.
        """
        raise NotImplementedError("This is a base class. Use a derived class.")


    def read_polarity(self) -> int:
        """Read the polarity register.

        Returns:
            int: Current value of the polarity register.
        """
        raise NotImplementedError("This is a base class. Use a derived class.")


    def read_direction(self) -> int:
        """Read the direction register.

        Returns:
            int: Current value of the direction register.
        """
        raise NotImplementedError("This is a base class. Use a derived class.")

#--------------------------------------------------------------------------------------------------

class TCAL6416(GPIO_BASE):

    def __init__(self, i2c: I2CBase,
                 i2c_address_7bit: int = 0x20,
                 init_shadow_from_ic: bool = False,
                 port0_open_drain: bool = False,
                 port1_open_drain: bool = False) -> None:
        super().__init__(i2c, i2c_address_7bit, 16, init_shadow_from_ic)
        # here go the TCAL specific register addresses
        self.REG_OUTPUT_DRIVE_STRENGTH = 0x40  # needs two bits per port pin -> 32 bits pin
        self.REG_PULL_RESISTOR_ENABLE = 0x46
        self.REG_PULL_RESISTOR_SELECTION = 0x48
        self.REG_OUTPUT_PORT_CONFIGURATION = 0x4f  # !! this is only one byte Register using bits 0 and 1 for the two ports !!
        self.REG_INPUT_LATCH = 0x44 # UNUSED
        self.REG_INTERRUPT_MAK = 0x4a # UNUSED
        self.REG_INTERRUPT_STATUS = 0x4c # UNUSED
        # preselect the output port type (one time at init)
        _nogpio = self._number_of_gpio  # we need to trick the _write_helper function to only write one byte
        self._number_of_gpio = 8  # temporarily set to 8
        _config_outport = (0x01 if port0_open_drain else 0) | (0x02 if port1_open_drain else 0)
        self._shadow_regs[self.REG_OUTPUT_PORT_CONFIGURATION] = _config_outport
        self._write_helper(self.REG_OUTPUT_PORT_CONFIGURATION, self._shadow_regs[self.REG_OUTPUT_PORT_CONFIGURATION])
        self._number_of_gpio = _nogpio  # restore
        # update the shadow registers
        self._shadow_regs[self.REG_OUTPUT_DRIVE_STRENGTH] = self.read_output_drive_strength() if init_shadow_from_ic else 0,
        self._shadow_regs[self.REG_PULL_RESISTOR_ENABLE] = self.read_pull_resistor_enable() if init_shadow_from_ic else 0,
        self._shadow_regs[self.REG_PULL_RESISTOR_SELECTION] = self.read_pull_resistor_selection if init_shadow_from_ic else self._number_of_gpio_mask, # 1=pullup, 0=pulldown


    #--------------------------------------------

    def __str__(self) -> str:
        return f"TCAL6416 GPIO device with address {self.i2c_address_7bit:02x} on {self.bus}"

    def __repr__(self) -> str:
        return f"TCAL6416({repr(self.bus)}, i2c_address_7bit={self.i2c_address_7bit})"

    #--------------------------------------------

    def configure_pins(self,
                       pin_io: tuple | str,
                       invert_input: tuple | str,
                       preset_output: None | tuple | str = None,
                       pull_resistors_config: tuple | str = None,
                       enable_pull_resistors: tuple | str = None,
                       ) -> bool:
        ok0 = super().configure_pins(pin_io, invert_input, preset_output=preset_output)
        if not ok0:
            return False
        if pull_resistors_config:
            if len(pull_resistors_config) != self._number_of_gpio:
                raise ValueError(f"Parameter 'pull_resistors_config' must be tuple of {self._number_of_gpio} integers or a string of length {self._number_of_gpio}.")
            _pull_config = shifting_plus(pull_resistors_config)
            ok1 = self._write_helper(self.REG_PULL_RESISTOR_SELECTION, _pull_config)
        else:
            ok1 = True
        if enable_pull_resistors:
            if len(enable_pull_resistors) != self._number_of_gpio:
                raise ValueError(f"Parameter 'enable_pull_resistors' must be tuple of {self._number_of_gpio} integers or a string of length {self._number_of_gpio}.")
            _pull_enable = shifting_plus(enable_pull_resistors)
            ok2 = self._write_helper(self.REG_PULL_RESISTOR_ENABLE, _pull_enable)
        else:
            ok2 = True
        return ok1 and ok2


    def read_input(self) -> int:
        return self._read_helper(self.REG_INPUT)


    def write_output(self, value: int) -> bool:
        return self._write_helper(self.REG_OUTPUT, value)

    def read_output(self) -> int:
        return self._read_helper(self.REG_OUTPUT)


    def set_direction(self, direction) -> bool:
        # direction: 1=input, 0=output
        return self._write_helper(self.REG_CONFIGURATION, direction)


    def read_direction(self)-> int:
        return self._read_helper(self.REG_CONFIGURATION)


    def set_polarity(self, polarity) -> bool:
        # polarity: 1=invert, 0=normal
        return self._write_helper(self.REG_POLARITY, polarity)


    def read_polarity(self) -> int:
        return self._read_helper(self.REG_POLARITY)


    def set_output_drive_strength(self, strength: int) -> bool:
        # strength: 2 bits per pin, 00=2mA, 01=4mA, 10=8mA, 11=12mA
        if (strength < 0) or (strength > 0x5555):
            raise ValueError("Output drive strength must be a 16 bit integer with each two bits in the range 0..3.")
        return self._write_helper(self.REG_OUTPUT_DRIVE_STRENGTH, strength)


    def read_output_drive_strength(self) -> int:
        p0 = self._read_helper(self.REG_OUTPUT_DRIVE_STRENGTH)
        p1 = self._read_helper(self.REG_OUTPUT_DRIVE_STRENGTH + 2)  # updates also the shadow register 0x42 but it will not be used
        self._shadow_regs[self.REG_OUTPUT_DRIVE_STRENGTH] = (p1 << 16) | p0
        return self._shadow_regs[self.REG_OUTPUT_DRIVE_STRENGTH]


    def set_pull_resistor_enable(self, enable_pattern: int) -> bool:
        # enable_pattern: 1=enable, 0=disable by port pin
        if (enable_pattern < 0) or (enable_pattern > self._number_of_gpio_mask):
            raise ValueError(f"Pull resistor enable must be a {self._number_of_gpio}-bit integer.")
        return self._write_helper(self.REG_PULL_RESISTOR_ENABLE, enable_pattern)


    def read_pull_resistor_enable(self) -> int:
        return self._read_helper(self.REG_PULL_RESISTOR_ENABLE)


    def set_pull_resistor_selection(self, selection_pattern: int) -> bool:
        # selection_pattern: 1=pullup, 0=pulldown by port pin
        if (selection_pattern < 0) or (selection_pattern > self._number_of_gpio_mask):
            raise ValueError(f"Pull resistor selection must be a {self._number_of_gpio}-bit integer.")
        return self._write_helper(self.REG_PULL_RESISTOR_SELECTION, selection_pattern)


    def read_pull_resistor_selection(self) -> int:
        return self._read_helper(self.REG_PULL_RESISTOR_SELECTION)



#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CMuxedBus, BusMux


    i2c_p = I2CPort("172.21.101.30:2101")
    print("MASTER:", i2c_p.i2c_bus_scan())
    mux = BusMux(i2c_p, 0x70)
    #mux.setChannelMask(0xff)
    mux.setChannel(8)  # bus no 8
    print("CH8:", i2c_p.i2c_bus_scan())

    gpio = TCAL6416(i2c_p)
    print(gpio.read_input())
    #gpio.configure_pins("0110", "0000", "0000")

    #gpio.set_pin_as_input(0)
    #gpio.set_pin_as_output(1)
    #gpio.set_pin(1)

    #print(gpio.get_pin(0))
    #print(gpio.get_pin(1))
    #print(gpio.get_pin(2))
    #print(gpio.get_pin(3))

    #gpio.set_pin(3)
    #gpio.reset_pin(3)


# END OF FILE