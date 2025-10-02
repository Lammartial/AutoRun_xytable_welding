from time import sleep
from struct import pack, unpack
from rrc.i2cbus import I2CBase


class TCAL6416:
    INPUT_PORT_0 = 0x00
    INPUT_PORT_1 = 0x01
    REG_INPUT = 0x00  # base
    OUTPUT_PORT_0 = 0x02
    OUTPUT_PORT_1 = 0x03
    REG_OUTPUT = 0x02  # base
    POLARITY_PORT_0 = 0x04
    POLARITY_PORT_1 = 0x05
    REG_POLARITY = 0x04 # base
    CONFIG_PORT_0 = 0x06
    CONFIG_PORT_1 = 0x07
    REG_CONFIGURATION = 0x06

    WRITABLE_REGS = (REG_OUTPUT, REG_POLARITY, REG_CONFIGURATION)

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x20, init_shadow_from_ic: bool = False):
        self.bus = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.i2c_address = int(i2c_address_7bit) << 1
        self.retry_limit = 10
        self.pause_us = 5000
        # prepare shadow registers
        self._shadow_regs = [
            None,  # dummy for input address
            self.read_output() if init_shadow_from_ic else 0x0000,
            self.read_polarity() if init_shadow_from_ic else 0x0000,
            self.read_direction() if init_shadow_from_ic else 0xFFFF,      # power-up pins input
        ]

    #--------------------------------------------

    def __str__(self) -> str:
        return f"TCAL6416 GPIO device with address {self.i2c_address_7bit:02x} on {self.bus}"

    def __repr__(self) -> str:
        return f"TCAL6416({repr(self.bus)}, i2c_address_7bit={self.i2c_address_7bit})"

    #--------------------------------------------

    def read_input(self):
        from binascii import hexlify
        port0 = self.bus.readfrom_mem(self.i2c_address_7bit, self.INPUT_PORT_0, 1)
        port1 = self.bus.readfrom_mem(self.i2c_address_7bit, self.INPUT_PORT_1, 1)
        buf = port0 + port1
        print(hexlify(buf).decode())
        return unpack("<H", buf)[0]

    def write_output(self, value):
        self.bus.write_byte_data(self.address, self.OUTPUT_PORT_0, value & 0xFF)
        self.bus.write_byte_data(self.address, self.OUTPUT_PORT_1, (value >> 8) & 0xFF)

    def read_output(self):
        port0 = self.bus.read_byte_data(self.address, self.OUTPUT_PORT_0)
        port1 = self.bus.read_byte_data(self.address, self.OUTPUT_PORT_1)
        return (port1 << 8) | port0

    def set_direction(self, direction):
        # direction: 1=input, 0=output, 16 bits
        self.bus.write_byte_data(self.address, self.CONFIG_PORT_0, direction & 0xFF)
        self.bus.write_byte_data(self.address, self.CONFIG_PORT_1, (direction >> 8) & 0xFF)

    def read_direction(self):
        port0 = self.bus.read_byte_data(self.address, self.CONFIG_PORT_0)
        port1 = self.bus.read_byte_data(self.address, self.CONFIG_PORT_1)
        return (port1 << 8) | port0

    def set_polarity(self, polarity):
        # polarity: 1=invert, 0=normal, 16 bits
        self.bus.write_byte_data(self.address, self.POLARITY_PORT_0, polarity & 0xFF)
        self.bus.write_byte_data(self.address, self.POLARITY_PORT_1, (polarity >> 8) & 0xFF)

    def read_polarity(self):
        port0 = self.bus.read_byte_data(self.address, self.POLARITY_PORT_0)
        port1 = self.bus.read_byte_data(self.address, self.POLARITY_PORT_1)
        return (port1 << 8) | port0

    # private functions
    def _write_register(self, register: int, value: int) -> bool:
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
        if register not in TCAL6416.WRITABLE_REGS:
            raise ValueError(f"Register '{register}' of {self} not writable.")
        value = int(value)
        if not (0 <= value <= 15):
            raise ValueError(f"Invalid output register value for {self}. Must be between 0 and 15."
                             f"You sent {value}")


        data = bytearray([register, value])
        # if len(data) == self.bus.writeto(self.i2c_address_7bit, data):
        #     self._shadow_regs[register] = value
        #     return True
        # else:
        #     return False
        for n in range(0, self.retry_limit):
            try:
                wlen = self.bus.writeto(self.i2c_address_7bit, data)
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
                value = self.bus.readfrom_mem(adr, data, 1)  # does 3 retries with 1ms pause between
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
        data = bytearray([TCAL6416.REG_INPUT_PORT])
        return self._read_helper(self.i2c_address_7bit, data)


    #----------------------------------------------------------------------------------------------

    # def configure_pins(self, pin_io: tuple | str, invert_input: tuple | str, preset_output: None | tuple | str = None):
    #     """The Configuration register (register 3) configures the directions of the I/O pins.
    #     If a bit in this register is set to 1, the corresponding port pin is enabled as an input
    #     with high-impedance output driver. If a bit in this register is cleared to 0,
    #     the corresponding port pin is enabled as an output.

    #     Args:
    #         pin_io (tuple | str):  4-tuple of 0 | 1, 0=pin is output, 1=pin is input
    #         invert_input (tuple | str):   4-tuple of 0 | 1, 0=pin is read normal, 1=pin is read inverted
    #         preset_output (tuple | str):  4-tuple of 0 | 1, preset if outout
    #     """
    #     if len(pin_io) != 4:
    #         raise ValueError("Parameter 'pin_as_output' must be tuple if 4 integers or a string of length 4.")
    #     if len(invert_input) != 4:
    #         raise ValueError("Parameter 'invert_input' must be tuple if 4 integers or a string of length 4.")
    #     if preset_output is not None:
    #         if len(preset_output) != 4:
    #             raise ValueError("Parameter 'output' must be tuple if 4 integers or a string of length 4.")
    #         _output = shifting_plus(preset_output)
    #         self._write_register(TCAL6416.REG_OUTPUT, _output)
    #     _polarity = shifting_plus(invert_input)
    #     _config = shifting_plus(pin_io)
    #     self._write_register(TCAL6416.REG_POLARITY_INVERSE, _polarity)
    #     self._write_register(TCAL6416.REG_CONFIGURATION, _config)



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