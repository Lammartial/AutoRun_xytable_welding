"""Collection of exceptions used in ncd_i2c_interface.py"""


class NCDError(Exception):
    pass


class SelfTestFailedError(NCDError):
    def __init__(self, ncd_interface_address: str):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"NCD USB-I2C on port {self.ncd_interface_address} is not responding"


class I2CReadError(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout Error, Chip did Not Respond, Check I2C Address (device 0x{self.i2c_address:02X} on NCD interface: {self.ncd_interface_address})"


class I2CWriteError1(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout Error 1, Chip did Not Respond, Check I2C Address (device 0x{self.i2c_address:02X} on NCD interface: {self.ncd_interface_address})"


class I2CWriteError2(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout Error 2, Chip did Not Respond, Check I2C Address (device 0x{self.i2c_address:02X} on NCD interface: {self.ncd_interface_address})"


class I2CNotImplementedError(NCDError):
    def __init__(self, ncd_interface_address):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Not Yet Implemented ( on NCD interface: {self.ncd_interface_address})"


class I2CAckError(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout Error, Chip did Not Acknowledge. device 0x{self.i2c_address:02X} on NCD interface: {self.ncd_interface_address}"


class InvalidI2CAddressError(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Invalid I2C i2c_address_7bit (0x{self.i2c_address:02X}) on NCD interface: {self.ncd_interface_address}"


class InvalidParametersError(NCDError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.i2c_address = i2c_address
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Invalid parameters for device 0x{self.i2c_address:02X} on NCD interface {self.ncd_interface_address}. Check digits"\
               " and/or length of data."


class ChecksumError(NCDError):
    def __init__(self, ncd_interface_address):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Checksum error. Something went wrong during communication on port {self.ncd_interface_address}."


class NCDTimeoutError(NCDError):
    def __init__(self, ncd_interface_address):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Timeout error. Device on port {self.ncd_interface_address} didn't respond in time."


class UnknownResponseError(NCDError):
    def __init__(self, ncd_interface_address, response):
        self.ncd_interface_address = ncd_interface_address
        self.response = response

    def __str__(self):
        return f"Unknown response ({self.response}) on port {self.ncd_interface_address}."


class UnknownNCDError(NCDError):
    def __init__(self, ncd_interface_address, error_code):
        self.ncd_interface_address = ncd_interface_address
        self.error_code = error_code

    def __str__(self):
        return f"Unknown NCD Error code: {self.error_code} (on NCD interface: {self.ncd_interface_address})"


class ConnectionToNCDInterfaceBroken(NCDError):
    def __init__(self, ncd_interface_address):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"The NCD interface that was connected via {self.ncd_interface_address} can't be reached anymore."


class CantFindNCDInterface(NCDError):
    def __init__(self, ncd_interface_address):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"Can't connect to the NCD interface at: {self.ncd_interface_address}."
