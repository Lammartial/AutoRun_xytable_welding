"""Collection of exceptions used in ncd_i2c_interface.py."""

from rrc.eth2i2c.i2c_errors import *


class NCDError(Exception):
    pass


class SelfTestFailedError(NCDError):
    def __init__(self, ncd_interface_address: str):
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"NCD USB-I2C on port {self.ncd_interface_address} is not responding"


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
        return f"Can't connect to the NCD interface at {self.ncd_interface_address}."

#
# Implemeting the I2CError classes for NCD
#

class NCD_I2CInvalidParametersError(I2CInvalidParametersError):
    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


class NCD_I2CReadError(I2CReadError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


class NCD_I2CWriteError1(I2CError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


class NCD_I2CWriteError2(I2CError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


class NCD_I2CNotImplementedError(I2CError):

    def __str__(self):
        return f"Function not implemented yet on NCD interface."


class NCD_I2CAckError(I2CError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


class NCD_I2CInvalidAddressError(I2CError):

    def __init__(self, i2c_address, ncd_interface_address):
        self.super().__init__(i2c_address)
        self.ncd_interface_address = ncd_interface_address

    def __str__(self):
        return f"{self.super().__str__()} on NCD interface {self.ncd_interface_address}"


# END OF FILE