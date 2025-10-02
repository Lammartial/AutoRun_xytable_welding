"""
BQ76942 - AFE (analog front end)
3-Series to 10-Series High Accuracy Battery Monitor and Protector for
Li-Ion, Li- Polymer, and LiFePO4 Battery Packs for Li-Ion and Phosphate Applications.

"""

__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from time import sleep, monotonic_ns
from binascii import hexlify
from struct import pack, unpack
from collections import OrderedDict
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from rrc.smbus import BusMaster

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

def _od2t(d: OrderedDict) -> tuple:
    """To convert an ordered dict to a tuple of values for TestStand Container.

    Args:
        d (OrderedDict): _description_

    Returns:
        tuple: _description_
    """

    return tuple([t for t in d.values()])

def _maybe_hexlify(self, what: bytes | bytearray, hexi: None | bool | str) -> bytes | bytearray | str:
        """Helper to convert returned bytes on user request from bytearray or bytes to hex string with optional separator.

        Note: for internal use mainly in the chipset functions which inherits all from this class.

        Args:
            what (bytes | bytearray): data to convert or not
            hexi (None | bool | str): depending on the type data will be hex converted and separated.
                                      None or bool(False): no conversion
                                      str: conversion with given separator.
                                      bool(True): conversion without separator
                                      any else type: use default separator ","

        Returns:
            bytes | bytearray | string: either what as it comes in or hex encoded string
        """
        if hexi is None:
            return what  # as it is
        if isinstance(hexi, str):
            return hexlify(what, hexi).decode()
        if isinstance(hexi, bool):
            if hexi:
                return hexlify(what).decode()
            return what  # as it is
        # hexi is something, but nothing we can use -> use default separator
        return hexlify(what, ",").decode()


# --------------------------------------------------------------------------- #

class BQ76942:
    """
    AFE for 3-to 15-Series Cell Battery Monitor using a 400kHz or 100kHz I²C bus interface.

    The communications interface includes programmable timeout capability, this should only be used if the bus will
    be operating at 100 kHz or 400 kHz. If this is enabled with the device set to 100 kHz mode, then the device will
    reset the communications interface logic if a clock is detected low longer than a tTIMEOUT of 25 ms to 35 ms, or if
    the cumulative clock low responder extend time exceeds ≈25 ms, or if the cumulative clock low controller extend
    time exceeds 10 ms. If the timeouts are enabled with the device set to 400 kHz mode, then the device will reset
    the communications interface logic if a clock is detected low longer than tTIMEOUT of 5 ms to 20 ms. The bus also
    includes a long-term timeout if the SCL pin is detected low for more than 2 seconds, which applies whether or
    not the timeouts above are enabled.
    """
    def __init__(self, smbus: BusMaster, slvAddress: int = 0x08, pec: bool = False) -> None:
        """_summary_

        Args:
            smbus (BusMaster): Convenience class to communicate on the I2C bus using retries and tiemouts.
            slvAddress (int, optional): The right aligned 7-bit slave address which is shifted by one
                to the left when sent to the bus. Defaults to 0x08.
            pec (bool, optional): _description_. Defaults to False.
        """

        self.bus = smbus
        self.address = int(slvAddress)
        self.pec = bool(pec)
        _bat = self

    # --------------------------------------------

    def __str__(self) -> str:
        return f"BQ76942 AFE at 0x{self.address} on {self.bus}"

    def __repr__(self) -> str:
        return f"BQ76942({repr(self.bus)}, slvAddress={self.address}, pec={self.pec})"

    # --------------------------------------------




#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ### Initialize the logging
    #logger_init(filename_base=None)  ## init root logger
    #_log = getLogger(__name__, DEBUG)

    print("NO TESTS: ", __file__)

    #
    # to test please setup a "test_xxx.py" module !
    #



# END OF FILE