"""Common I2C interface exceptions."""

class I2CError(Exception):
    pass

class I2CReadError(I2CError):

    def __init__(self, i2c_address):
        self.i2c_address = i2c_address

    def __str__(self):
        return f"Timeout Error on read, slave did not respond. Check I2C address (device 0x{self.i2c_address:02X}."


class I2CWriteError1(I2CError):

    def __init__(self, i2c_address):
        self.i2c_address = i2c_address

    def __str__(self):
        return f"Timeout Error1 on write, slave did not respond. Check I2C address (device 0x{self.i2c_address:02X}."


class I2CWriteError2(I2CError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout Error2 on write, slave did not respond. Check I2C address (device 0x{self.i2c_address:02X}."


class I2CNotImplementedError(I2CError):

    def __str__(self):
        return f"Function not implemented yet."


class I2CAckError(I2CError):

    def __init__(self, i2c_address):
        self.i2c_address = i2c_address

    def __str__(self):
        return f"Timeout error on waiting for acknowledge of device 0x{self.i2c_address:02X}."


class I2CInvalidAddressError(I2CError):

    def __init__(self, i2c_address):
        self.i2c_address = i2c_address

    def __str__(self):
        return f"Invalid I2C address (0x{self.i2c_address:02X}). May be of 7 bit size only."

class I2CInvalidParametersError(I2CError):
    def __init__(self, i2c_address):
        self.i2c_address = i2c_address

    def __str__(self):
        return f"Invalid parameters for device 0x{self.i2c_address:02X}. Check digits and length of data."


# END OF FILE