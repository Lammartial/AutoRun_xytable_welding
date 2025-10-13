"""
BQ76942 - AFE (analog front end)
3-Series to 10-Series High Accuracy Battery Monitor and Protector for
Li-Ion, Li- Polymer, and LiFePO4 Battery Packs for Li-Ion and Phosphate Applications.

"""

__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from typing import List, Tuple
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


def _maybe_hexlify(what: bytes | bytearray, hexi: None | bool | str) -> bytes | bytearray | str:
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

    def write_subcommand(self, subcmd: int, data: bytes | bytearray = None, timeout: float = 2.0) -> bool:
        """Write a subcommand with optional data to the BQ76942.

        Args:
            subcmd (int): The subcommand to write.
            data (bytes | bytearray, optional): Optional data to send with the subcommand. Defaults to b''.
        """

        if not (0 <= subcmd <= 0xFFFF):
            raise ValueError("Subcommand must be a 16-bit value (0-65535).")

        if not self.bus.writeWord(self.address, 0x3E, subcmd, pec=self.pec):  # write Subcommand to the registers 0x3E and 0x3F
            return False
        t0 = monotonic_ns()  # common timeout over the rest of the function
        response = 0xFFFF
        while response != subcmd:
            response = self.bus.readWord(self.address, 0x3E, pec=self.pec)  # read back the subcommand register
            t1 = monotonic_ns()
            if (t1 - t0) > timeout * 1e+9:  # scale timeout to ns
                raise TimeoutError("While wait for subcommand to complete.")
        if data:
            checksum = (subcmd & 0xFF) | ((subcmd >> 8) & 0xFF)
            for b in data:
                checksum += b   # generate the checksum by simple addition
            checksum = ~checksum & 0xFF  # bitwise inverse
            if not self.bus.writeBytes(self.address, 0x40, data, pec=self.pec):  # write data to the data registers starting at 0x40
                return False
            # activate the data transfer of the command
            buf = (checksum, ((len(data) + 4) << 8))  # length of data + checksum byte + length byte + the two subcommandbytes
            if not self.bus.writeBytes(self.address, 0x60, buf, pec=self.pec):  # write checksum to the checksum register 0x60
                return False
        return True


    def read_subcommand(self, subcmd: int, length: int = 0, timeout: float = 2.0, hexi: None | bool | str = None) -> bytes | bytearray | str:
        """Read data from a subcommand.

        Args:
            subcmd (int): The subcommand to read from.
            length (int, optional): The number of bytes to read. Defaults to 0.
            timeout (float, optional): Timeout in seconds for the operation. Defaults to 2.0.
            hexi (None | bool | str, optional): If set to True or a string separator, the returned bytes will be hexlified.
                                                Defaults to None.
        Returns:
            bytes | bytearray | str: The data read from the subcommand, possibly hexlified.
        """

        if not (0 <= subcmd <= 0xFFFF):
            raise ValueError("Subcommand must be a 16-bit value (0-65535).")

        if not self.bus.writeWord(self.address, 0x3E, subcmd, pec=self.pec):  # write Subcommand to the registers 0x3E and 0x3F
            return False
        t0 = monotonic_ns()  # common timeout over the rest of the function
        response = 0xFFFF
        while response != subcmd:
            response = self.bus.readWord(self.address, 0x3E, pec=self.pec)  # read back the subcommand register
            t1 = monotonic_ns()
            if (t1 - t0) > timeout * 1e+9:  # scale timeout to ns
                raise TimeoutError("While wait for subcommand to complete.")
        # data is ready now
        ctrl, ok = self.bus.readBytes(self.address, 0x60, 2, pec=self.pec)  # read checksum and length
        if not ok:
            raise IOError("Failed to read checksum and length from BQ76942.")
        count = ctrl[1]
        buf, ok = self.bus.readBytes(self.address, 0x40, count, pec=self.pec)
        # calc expected checksum
        checksum = (subcmd & 0xff) | ((subcmd >> 8) & 0xff)
        for b in buf:
            checksum += b   # generate the checksum by simple addition
        checksum = ~checksum & 0xFF # bitwise inverse
        # verify checksum
        if checksum != ctrl[0]:
            raise IOError("Checksum mismatch reading from BQ76942.")
        # success
        return buf


    def read_cell_voltages(self, hexi: None | bool | str = bool) -> Tuple[Tuple[float], Tuple[str]]:
        """Read cell voltages from the BQ76942.

        Args:
            count (int): Number of cell voltages to read (3 to 10).
            hexi (None | bool | str, optional): If set to True or a string separator, the returned bytes will be hexlified.
                                                Defaults to None.
        Returns:
            List[float], List[str]: List of voltages read, all values in raw as hex format str.
        """

        _standard_scale = 1e-3 # mV -> V
        _user_scale = 1e-3  # user defined scale for the last three voltages: Stack Voltage (VC10 pin), PACK pin voltage, LD pin voltage
        scale = [_standard_scale] * 10 + [_user_scale] * 3
        voltages = ()
        raw = ()
        regadr = 0x14 # base register address for Cell 1 Voltage
        for i in range(13):  # 10 cells + 3 special Voltages:
            buf = self.bus.readBytes(self.address, regadr, 2, pec=self.pec)  # pre-read all cell voltages to update the registers
            volt = unpack("<H", buf[0])[0] * scale[i]  # scale returned value into Volts
            voltages += (volt,)
            raw += (_maybe_hexlify(buf, hexi),)
            regard += 2
        return voltages, raw


    def read_temperatures(self, hexi: None | bool | str = bool) -> Tuple[Tuple[float], Tuple[str]]:
        """Read temperature values from the BQ76942.

        Args:
            hexi (None | bool | str, optional): If set to True or a string separator, the returned bytes will be hexlified.
                                                Defaults to None.
        Returns:
            List[float], List[str]: List of temperatures read, all values in raw as hex format str.
        """

        _standard_scale = 0.1  # 0.1K -> K
        _user_scale = 1.0  # user defined scale for the temperature on the TS pin
        scale = [_standard_scale] * 10
        temperatures = ()
        raw = ()
        regadr = 0x68 # base register address for Temperature 1
        for i in range(4):  # 3 internal + 1 external temperature:
            buf = self.bus.readBytes(self.address, regadr, 2, pec=self.pec)  # pre-read all temperature to update the registers
            temp = (unpack("<H", buf[0])[0] * scale[i]) - KELVIN_ZERO_DEGC  # scale returned value into °C
            temperatures += (temp,)
            raw += (_maybe_hexlify(buf, hexi),)
            regard += 2
        return temperatures, raw


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