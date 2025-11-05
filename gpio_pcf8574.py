from time import sleep
from math import ceil, floor
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

class PCF8574:

    def __init__(self, i2c: I2CBase,
                 i2c_address_7bit: int = 0x20,
                 number_of_gpio: int = 8,
                 retry_limit: int = 1,
                 pause_us: int = 5000
                ) -> None:
                
        self.bus = i2c
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.retry_limit = retry_limit
        self.pause_us = pause_us
        assert ((number_of_gpio >= 1) and (number_of_gpio <= 64)), "Maximum number of GPIO pins is 64."
        self._number_of_gpio = number_of_gpio  # max 64 !!
        self._number_of_gpio_mask = (1 << number_of_gpio) - 1


    #--------------------------------------------

    def __str__(self) -> str:
        return f"PCF8574 GPIO device with address {self.i2c_address_7bit:02x} on {self.bus}"

    def __repr__(self) -> str:
        return f"PCF8574({repr(self.bus)}, i2c_address_7bit={self.i2c_address_7bit})"

    
    #--------------------------------------------
    # private functions
    def _write_helper(self, value: int) -> bool:
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
        # prepare the value into a data array
        b = value.to_bytes(ceil(self._number_of_gpio / 8), "little")
        buf = bytearray(b)
        for n in range(0, self.retry_limit):
            try:
                wlen = self.bus.writeto(self.i2c_address_7bit, buf)
                ok: bool = len(buf) == wlen
                if ok:
                    self._shadow_reg = value  # we can shadow the value
                return ok
            except OSError:
                if n == self.retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")


    def _read_helper(self) -> int:
        length = ceil(self._number_of_gpio / 8)
        for n in range(0, self.retry_limit):
            try:
                buf = self.bus.readfrom(self.i2c_address_7bit, length)  # does 3 retries with 1ms pause between
                #print(hexlify(buf).decode())  # DEBUG
                try:
                    value = int.from_bytes(buf, "little", signed=False) & self._number_of_gpio_mask
                    #self._shadow_reg = value
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

    #----------------------------------------------------------------------------------------------

    def read_input(self) -> int:
        return self._read_helper()

    #----------------------------------------------------------------------------------------------

    def write_output(self, value: int | str) -> bool:
        if isinstance(value, str):
            _v = shifting_plus(value)
        else:
            _v = value                             
        return self._write_helper(_v)

    #----------------------------------------------------------------------------------------------

    def get_config(self) -> int:
        return self._shadow_reg  # the shadow reg determines with its 1's if the port could be an input or outputs a 0

    #----------------------------------------------------------------------------------------------

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

    
    #----------------------------------------------------------------------------------------------

    def set_pin(self, pin_number: int) -> bool:
        """Set the specified GPIO to a logic high level (5 V).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _value = self._shadow_reg | (1 << (pin_number & self._number_of_gpio_mask))  # set corresponding bit
        return self._write_helper(_value)

    #----------------------------------------------------------------------------------------------

    def reset_pin(self, pin_number: int) -> bool:
        """Set the specified GPIO to a logic low level (Gnd).
        Has now effect if the GPIO is configured as an input.

        Args:
            gpio_n int: Index of the GPIO to configure [0, number_of_gpio-1]
        """

        pin_number = int(pin_number)
        _value = self._shadow_reg & ~(1 << (pin_number & self._number_of_gpio_mask))  # clear corresponding bit
        return self._write_helper( _value)



#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CMuxedBus, BusMux


    i2c_p = I2CPort("172.21.101.30:2101")
    print("MASTER:", i2c_p.i2c_bus_scan())
    mux = BusMux(i2c_p, 0x77)   # on base adapter
    #mux.setChannelMask(0xff)
    dutcom = I2CMuxedBus(i2c_p, mux, 2)
    print("CH2:", dutcom.i2c_bus_scan())
    mux2 = BusMux(dutcom, 0x70)  # on cartridge
    gpio = PCF8574(I2CMuxedBus(dutcom, mux2, 8))
    print(gpio.read_input())
    gpio.write_output("10010000")  # 1 = input or open drain output, 0=output 0
    print(gpio.read_input())
    for p in range(8):
        gpio.set_pin(p)
        print(f"P{p}_S:", hex(gpio.read_input()), hex(gpio._shadow_reg))
        gpio.reset_pin(p)
        print(f"P{p}_R:", hex(gpio.read_input()), hex(gpio._shadow_reg))

    #print(gpio.get_pin(0))
    #print(gpio.get_pin(1))
    #print(gpio.get_pin(2))
    #print(gpio.get_pin(3))

    #gpio.set_pin(3)
    #gpio.reset_pin(3)


# END OF FILE