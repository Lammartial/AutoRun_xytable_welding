"""Collection of exceptions used in ncd_i2c_interface.py."""

from rrc.eth2i2c.i2c_errors import *


class NCDError(Exception):
    def __init__(self, ncd_interface):
        self.ncd_interface = ncd_interface

class NCDSelfTestFailedError(NCDError):

    def __str__(self):
        return f"{self.ncd_interface} is not responding"


class NCDChecksumError(NCDError):

    def __str__(self):
        return f"Checksum error. Something went wrong during communication on {self.ncd_interface}."


class NCDTimeoutError(NCDError):

    def __str__(self):
        return f"Timeout error. Device on {self.ncd_interface} didn't respond in time."


class NCDUnknownResponseError(NCDError):
    def __init__(self, ncd_interface, response):
        super().__init__(ncd_interface)
        self.response = response

    def __str__(self):
        return f"Unknown response ({self.response}) on {self.ncd_interface}."


class NCDUnknownErrorCodeError(NCDError):
    def __init__(self, ncd_interface, error_code):
        super().__init__(ncd_interface)
        self.error_code = error_code

    def __str__(self):
        return f"Unknown NCD Error code: {self.error_code} on {self.ncd_interface})"


class NCDConnectionToInterfaceBroken(NCDError):

    def __str__(self):
        return f"The NCD interface that was connected via {self.ncd_interface} can't be reached anymore."


class NCDCantFindInterface(NCDError):

    def __str__(self):
        return f"Can't connect to the NCD interface at {self.ncd_interface}."

#
# Implemeting the I2CError classes for NCD
#

class NCD_I2CInvalidParametersError(I2CInvalidParametersError):
    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


class NCD_I2CReadError(I2CReadError):

    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


class NCD_I2CWriteError1(I2CError):

    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


class NCD_I2CWriteError2(I2CError):

    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


class NCD_I2CNotImplementedError(I2CError):

    def __str__(self):
        return f"Function not implemented yet on NCD interface."


class NCD_I2CAckError(I2CError):

    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


class NCD_I2CInvalidAddressError(I2CError):

    def __init__(self, i2c_address, ncd_interface):
        super().__init__(i2c_address)
        self.ncd_interface = ncd_interface

    def __str__(self):
        return f"{super().__str__()} on NCD interface {self.ncd_interface}"


# END OF FILE