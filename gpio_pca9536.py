from time import sleep
from rrc.i2cbus import I2CBase


# helper to get a bit pattern from a bitlist of integers
def shifting_plus(bitlist: tuple | list) -> int:
    out = 0
    for bit in bitlist:
        out = out * 2 + (int(bit) & 0x01)
    return out


class PCA9536:
    """
    A class to control the PCA9536 4-bit I2C I/O Expander.

    https://www.ti.com/product/PCA9536

    The PCA9536 features 4-bit Configuration (input or
    output selection), Input Port, Output Port, and Polarity
    Inversion (active high or active low) registers. At
    power on, the I/Os are configured as inputs with a
    weak pullup to VCC. However, the system controller
    can enable the I/Os as either inputs or outputs by
    writing to the I/O configuration bits.

    If no signals are applied externally to the PCA9536,
    the voltage level is 1, or high, because of the internal
    pullup resistors.

    The data for each input or output is stored in the
    corresponding Input Port or Output Port register. The
    polarity of the Input Port register can be inverted
    with the Polarity Inversion register and the system
    controller reads all registers.

    The system controller resets the PCA9536 in the
    event of a timeout or other improper operation by
    utilizing the power-on reset feature, which puts the
    registers in their default state and initializes the I2C/
    SMBus state machine.

    """
    REG_INPUT_PORT = 0x00
    REG_OUTPUT = 0x01
    REG_POLARITY_INVERSE = 0x02
    REG_CONFIGURATION = 0x03

    WRITABLE_REGS = (REG_OUTPUT, REG_POLARITY_INVERSE, REG_CONFIGURATION)

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x41, init_shadow_from_ic: bool = False):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c: The I2CPort instance this IC is connected to
            i2c_address_7bit: The IC's 7-bit I2C address
        """
        self.i2c = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.retry_limit = 10
        self.pause_us = 5000        
        # prepare shadow registers
        self._shadow_regs = [
            None,
            self.get_output_register() if init_shadow_from_ic else 0x00,
            self.get_polarity_register() if init_shadow_from_ic else 0x00,
            self.get_config_register() if init_shadow_from_ic else 0x0F,      # power-up pins input 0..3, 4..7 not used
        ]
    
    def __str__(self) -> str:
        return f"PCA9536 GPIO device with address {self.i2c_address_7bit:02x} on {self.i2c}"

    def __repr__(self) -> str:
        return f"PCA9536({repr(self.i2c)}, i2c_address_7bit={self.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def configure_pins(self, pin_io: tuple | str, invert_input: tuple | str, preset_output: None | tuple | str = None):
        """The Configuration register (register 3) configures the directions of the I/O pins.
        If a bit in this register is set to 1, the corresponding port pin is enabled as an input
        with high-impedance output driver. If a bit in this register is cleared to 0,
        the corresponding port pin is enabled as an output.

        Args:
            pin_io (tuple | str):  4-tuple of 0 | 1, 0=pin is output, 1=pin is input
            invert_input (tuple | str):   4-tuple of 0 | 1, 0=pin is read normal, 1=pin is read inverted
            preset_output (tuple | str):  4-tuple of 0 | 1, preset if outout
        """
        if len(pin_io) != 4:
            raise ValueError("Parameter 'pin_as_output' must be tuple if 4 integers or a string of length 4.")
        if len(invert_input) != 4:
            raise ValueError("Parameter 'invert_input' must be tuple if 4 integers or a string of length 4.")
        if preset_output is not None:
            if len(preset_output) != 4:
                raise ValueError("Parameter 'output' must be tuple if 4 integers or a string of length 4.")
            _output = shifting_plus(preset_output)
            self._write_register(PCA9536.REG_OUTPUT, _output)
        _polarity = shifting_plus(invert_input)
        _config = shifting_plus(pin_io)
        self._write_register(PCA9536.REG_POLARITY_INVERSE, _polarity)
        self._write_register(PCA9536.REG_CONFIGURATION, _config)

    def reset_inversion(self):
        self._write_register(PCA9536.REG_POLARITY_INVERSE, 0x00)

    def set_pin_as_input(self, pin_n: int):
        """Configure the GPIO with the index n (starts at 0) as an input with a 100k pullup.

        Args:
            gpio_n int: Index of the GPIO to configure [0, 3]
        """
        pin_n = int(pin_n)
        _config = self._shadow_regs[PCA9536.REG_CONFIGURATION] | (1 << (pin_n & 0x03))  # set corresponding bit in configuration
        self._write_register(PCA9536.REG_CONFIGURATION, _config)

    def set_pin_as_output(self, pin_n: int):
        """Configure the GPIO with the index n (starts at 0) as an output.

        Args:
            gpio_n int: Index of the GPIO to configure [0, 3]
        """
        pin_n = int(pin_n)
        _config = self._shadow_regs[PCA9536.REG_CONFIGURATION] & ~(1 << (pin_n & 0x03))  # clear corresponding bit in configuration

        self._write_register(PCA9536.REG_CONFIGURATION, _config)


    def get_pin(self, pin_n: int) -> bool:
        """Read the logic level of the specified GPIO.

        Args:
            gpio_n int: Index of the GPIO [0, 3]

        Returns:
            bool: The logic level of the GPIO.
        """
        pin_n = int(pin_n)
        reg_value = self._read_input_register()
        self._shadow_regs[PCA9536.REG_INPUT_PORT] = reg_value  # keep also track of last reading of input
        return bool(reg_value & (1 << (pin_n & 0x03)))


    def set_pin(self, pin_n: int):
        """Set the specified GPIO to a logic high level (5 V).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO [0, 3]
        """
        pin_n = int(pin_n)
        _value = self._shadow_regs[PCA9536.REG_OUTPUT] | (1 << (pin_n & 0x03))  # set corresponding bit
        self._write_register(PCA9536.REG_OUTPUT, _value)

    def reset_pin(self, pin_n: int) -> None:
        """Set the specified GPIO to a logic low level (Gnd).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO [0, 3]
        """
        pin_n = int(pin_n)
        _value = self._shadow_regs[PCA9536.REG_OUTPUT] & ~(1 << (pin_n & 0x03))  # clear corresponding bit
        self._write_register(PCA9536.REG_OUTPUT, _value)

    # private functions
    def _write_register(self, register, value: int) -> bool:
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
        if register not in PCA9536.WRITABLE_REGS:
            raise ValueError(f"Register '{register}' of {self} not writable.")
        value = int(value)
        if not (0 <= value <= 15):
            raise ValueError(f"Invalid output register value for {self}. Must be between 0 and 15."
                             f"You sent {value}")


        data = bytearray([register, value])
        # if len(data) == self.i2c.writeto(self.i2c_address_7bit, data):
        #     self._shadow_regs[register] = value
        #     return True
        # else:
        #     return False
        for n in range(0, self.retry_limit):
            try:
                wlen = self.i2c.writeto(self.i2c_address_7bit, data)
                ok: bool = len(data) == wlen
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


    def _read_helper(self, adr: int, data: bytearray) -> bytearray:
        for n in range(0, self.retry_limit):
            try:
                value = self.i2c.readfrom_mem(adr, data, 1)  # does 3 retries with 1ms pause between
                try:
                    value = value[0]
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
    

    def _read_input_register(self) -> int:
        """Read the input register.

        Raises:
            IndexError: _description_

        Returns:
            int: _description_
        """
        data = bytearray([PCA9536.REG_INPUT_PORT])
        return self._read_helper(self.i2c_address_7bit, data)


#--------------------------------------------------------------------------------------------------


    def get_output_register(self) -> int:
        return self.__read_register(PCA9536.REG_OUTPUT)

    def get_polarity_register(self) -> int:
        return self.__read_register(PCA9536.REG_POLARITY_INVERSE)        

    def get_config_register(self) -> int:
        return self.__read_register(PCA9536.REG_CONFIGURATION)

    def __read_register(self, register: int):
        return self._read_helper(self.i2c_address_7bit, bytearray([register]))


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CMuxedBus, BusMux

    i2c_p = I2CPort("172.21.101.31:2101")
    mux = BusMux(i2c_p, 0x77)
    #mux.setChannelMask(0xff)
    mux.setChannel(7)

    gpio = PCA9536(i2c_p)
    gpio.configure_pins("0110", "0000", "0000")

    #gpio.set_pin_as_input(0)
    #gpio.set_pin_as_output(1)
    #gpio.set_pin(1)

    print(gpio.get_pin(0))
    print(gpio.get_pin(1))
    print(gpio.get_pin(2))
    print(gpio.get_pin(3))

    #gpio.set_pin(3)
    #gpio.reset_pin(3)

# END OF FILE