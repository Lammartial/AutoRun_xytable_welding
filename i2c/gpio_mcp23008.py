from time import sleep


class MCP23008:
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

    def __init__(self, i2c_port, i2c_address_7bit):
        self.i2c_port = i2c_port
        self.i2c_address_7bit = i2c_address_7bit

        # self.set_pin_as_output(0)
        #
        # self.set_pin_as_output(7)
        # self.set_pin(7)
        #
        # self.set_pin_as_input(6)
        # self.enable_pullup(6)
        #
        # while True:
        #     if self.get_pin(6) is False:
        #         self.set_pin(0)
        #     else:
        #         self.reset_pin(0)
        #     sleep(0.2)

    def set_pin(self, pin_n: int):
        value = self.get_gpio_register()
        value |= (1 << pin_n)
        self.set_gpio_register(value)

    def reset_pin(self, pin_n: int):
        value = self.get_gpio_register()
        value &= ~(1 << pin_n)
        self.set_gpio_register(value)

    def get_pin(self, pin_n: int) -> bool:
        value = self.get_gpio_register()
        return bool(value & (1 << pin_n))

    def enable_pullup(self, pin_n: int):
        value = self.get_gppu_register()
        value |= (1 << pin_n)
        self.set_gppu_register(value)

    def disable_pullup(self, pin_n: int):
        value = self.get_gppu_register()
        value &= ~(1 << pin_n)
        self.set_gppu_register(value)

    def set_pin_as_output(self, pin_n: int):
        value = self.get_iodir_register()
        value &= ~(1 << pin_n)
        self.set_iodir_register(value)

    def set_pin_as_input(self, pin_n: int):
        value = self.get_iodir_register()
        value |= (1 << pin_n)
        self.set_iodir_register(value)

    def set_iodir_register(self, value: int):
        self.__write_register(MCP23008.IODIR, value)

    def get_iodir_register(self) -> int:
        return self.__read_register(MCP23008.IODIR)

    def set_gpio_register(self, value: int):
        self.__write_register(MCP23008.GPIO, value)

    def get_gpio_register(self) -> int:
        return self.__read_register(MCP23008.GPIO)

    def set_gppu_register(self, value: int):
        self.__write_register(MCP23008.GPPU, value)

    def get_gppu_register(self) -> int:
        return self.__read_register(MCP23008.GPPU)

    def __write_register(self, register: int, value: int):
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([register, value]))

    def __read_register(self, register: int):
        value = self.i2c_port.readfrom_mem(self.i2c_address_7bit, bytearray([register]), 1)
        return value[0]
