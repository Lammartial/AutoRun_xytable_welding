"""
BQ76942 - AFE (analog front end)
3-Series to 10-Series High Accuracy Battery Monitor and Protector for
Li-Ion, Li- Polymer, and LiFePO4 Battery Packs for Li-Ion and Phosphate Applications.

"""

__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from io import BufferedIOBase
import math
import numpy as np
from itertools import combinations, chain
from multiprocessing import Value
from typing import List, Tuple
from time import sleep, monotonic_ns
from binascii import hexlify, unhexlify
from struct import pack, unpack, unpack_from, iter_unpack
from collections import OrderedDict
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from rrc.eth2i2c import I2CBase

from rrc.smbus_pec import calc as pec_calc

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
    def __init__(self, i2c: I2CBase, slvAddress: int = 0x08, pec: bool = True, retry_limit: int = 1, pause_us: int = 50) -> None:
        """_summary_

        Args:
            smbus (BusMaster): Convenience class to communicate on the I2C bus using retries and tiemouts.
            slvAddress (int, optional): The right aligned 7-bit slave address which is shifted by one
                to the left when sent to the bus. Defaults to 0x08.
            pec (bool, optional): _description_. Defaults to False.
        """

        self.i2c = i2c
        self.address = int(slvAddress)
        self.pec = bool(pec)
        self.pause_us = int(pause_us)  # in micro seconds
        self.retry_limit = int(retry_limit)  # number of read repetitions, must be integer in range 1 .. 10
        self._max_possible_cells = 10  # this is maximum cell for this IC type, it is NOT related to USED CELLs !!
        self._standard_scale_volt = 1e-3  # mV -> V
        self._user_scale_volt = 1e-3      # user defined scale for the last three voltages: Stack Voltage (VC10 pin), PACK pin voltage, LD pin voltage
        self._standard_scale_current = 1e-3 # mA -> A
        self._standard_scale_temp = 0.1  # 0.1K -> K
        self._user_scale_temp = 1.0  # user defined scale for the temperature on the TS pin

    # --------------------------------------------

    def __str__(self) -> str:
        return f"BQ76942 AFE at 0x{self.address} on {self.i2c}"

    def __repr__(self) -> str:
        return f"BQ76942({repr(self.i2c)}, slvAddress={self.address}, pec={self.pec})"

    # --------------------------------------------

    # ----------------------------------------------------------------------------------------------
    @property
    def retry_limit(self) -> int:
        return self._retry_limit

    @retry_limit.setter
    def retry_limit(self, value: int):
        if not (isinstance(value, int) and (value >= 1) and (value <= 1000)):
            raise ValueError("Retry count limit must be an integer 1 ... 1000")
        self._retry_limit = value


    # ----------------------------------------------------------------------------------------------
    # core functions (all others a reusing these ones)
    def writeBytes(self, slvAddress: int, cmd: int, buffer: bytes | bytearray, use_pec: bool = False) -> bool:
        """Writes a given sequence of bytes to a slave device addressed by slvAddress and command.

        Args:
            slvAddress (byte | int): 8 bit slave address (0..255)
            cmd (byte | int): command code (0..255)
            buffer (bytes | bytearray): payload bytes to be written to slave
            use_pec (bool, optional): Use a PEC checksum to verify the transfer if True. Defaults to False.

        Returns:
            bool: True if write transfer was successfully completed including PEC if given.
        """

        if use_pec:
            # calculate the PEC and insert it
            buf_with_pec = [cmd]
            _cs = pec_calc(bytearray([(slvAddress << 1), cmd]))
            for b in buffer:
                _cs = pec_calc((b).to_bytes(1, "little"), _cs)
                buf_with_pec.append(b)
                buf_with_pec.append(_cs)
                _cs = 0x00  # reset PEC seed
            bufc = bytearray(bytes(buf_with_pec))  # should have double the size of buffer + 1
        else:
            bufc = bytearray(bytes([cmd]) + bytes(buffer))
        #print("BQ76 write bytes", hexlify(bufc).decode())  # DEBUG
        for n in range(0, self._retry_limit):
            try:
                # wlen = self.i2c.writeto_mem(slvAddress,cmd,buf)
                wlen = self.i2c.writeto(slvAddress, bufc)
                # ok = (wlen > 0)
                ok: bool = len(bufc) == wlen
                return ok
            except OSError:
                if n == self._retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")


    def _retry_read_helper(self, slvAddress: int, cmd: int, count: int) -> bytearray:
        for n in range(0, self._retry_limit):
            try:
                buf = self.i2c.readfrom_mem(slvAddress, cmd, count)
                return buf
            except OSError:
                if n == self._retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")


    def readBytes(self, slvAddress: int, cmd: int, count: int, use_pec: bool = False) -> Tuple[bytearray, bool]:
        """Read bytes from a BQ76942 device by given address with given command code written after slave address.
        It handles the crappy PEC implementation correct or ignores it f disabled.

        Args:
            slvAddress (byte | int): 8 bit slave address (0..255)
            cmd (byte | int): command code (0..255)
            count (int): number of bytes to read
            use_pec (bool, optional): Use a PEC checksum to verify the transfer if True. Defaults to False.

        Returns:
            bytearray: bytes buffer that has been read.
            bool: True, if count bytes have been read and checksum was correct (if given), False else.
        """
        if use_pec:
            # crappy shit of the BQ device: it sends an PEC over adress, cmd, (address | 1) and first byte after first byte,
            # then it resets the PEC seed and sends an PEC oafter every next byte for just this byte -> we need to double
            # the amount of data to read
            if count > 1024:
                count = 1024  # meaningful limit
            count_with_pec = count * 2
            buf_with_pec = self._retry_read_helper(slvAddress, cmd, count_with_pec)
            # first byte PEC
            checksum_ok = True
            _cs = pec_calc(bytes([(slvAddress << 1), cmd, ((slvAddress << 1) | 1)]))
            for i in range(0, len(buf_with_pec), 2):
                _cs = pec_calc(buf_with_pec[i].to_bytes(1, "little"), _cs)  # calc the PEC for the data byte
                if _cs != buf_with_pec[i + 1]:  # compare with its PEC
                    checksum_ok = False
                _cs = 0x00  # reset the _cs seed for next bytes
            buf = buf_with_pec[::2]  # extract the real data bytes
            rlen = len(buf)
            ok = (rlen == count) and checksum_ok
            return buf, ok  # remove the checksum from the data
        else:
            buf = self._retry_read_helper(slvAddress, cmd, count)
            rlen = len(buf)
            ok = (rlen == count)
            return buf, ok

    # ----------------------------------------------------------------------------------------------

    def readWord(self, reg: int, signed: bool = False) -> Tuple[int, bool]:
        """read a word from the BQ76942 with PEC if enabled.

        Args:
            reg (int): _description_
            signed (bool, optional): _description_. Defaults to False.

        Returns:
            Tuple[int, bool]: _description_
        """

        if 1:
            buf, ok = self.readBytes(self.address, int(reg), 2, use_pec=self.pec)
            #print(_maybe_hexlify(buf, hexi=True))  # DEBUG
            if ok:
                response = unpack(("<h" if signed else "<H"), buf)[0]
            else:
                response = None
            return response, ok
        else:
            buf1, ok1 = self.readBytes(self.address, reg,     1, use_pec=self.pec)
            buf2, ok2 = self.readBytes(self.address, reg + 1, 1, use_pec=self.pec)
            buf = buf1 + buf2
            #print(_maybe_hexlify(buf, hexi=True))  # DEBUG
            if ok1 and ok2:
                response = unpack(("<h" if signed else "<H"), buf)[0]
            else:
                response = None
            return response, (ok1 and ok2)


    def writeWord(self, reg: int, value: int) -> bool:
        """Helper to write a word to the BQ76942 with PEC if enabled.

        Args:
            reg (int): The register address to write to.
            value (int): The word value to write.
        Returns:
            bool: True if the write was successful, False otherwise.
        """

        buf = int(value).to_bytes(2, "little" )
        if 1:
            return self.writeBytes(self.address, int(reg), bytearray(buf), use_pec=self.pec)
        else:
            if not self.writeBytes(self.address, reg,     bytearray(buf[:1]), use_pec=self.pec):
                 return False
            if not self.writeBytes(self.address, reg + 1, bytearray(buf[1:]), use_pec=self.pec):
                return False
        return True


    def disable_checksum(self) -> bool:
        buf = int(0x29e7).to_bytes(2, "little" )
        #return self.writeBytes(self.address, int(reg), bytearray(buf), use_pec=True)
        if not self.writeBytes(self.address, 0x3E, bytearray(buf[:1]), use_pec=True):
             return False
        if not self.writeBytes(self.address, 0x3F, bytearray(buf[1:]), use_pec=True):
            return False
        self.pec = False
        return True


    # ----------------------------------------------------------------------------------------------
    # Interface for bq_flasher module

    # def enable_full_access(self) -> bool:
    #     # ...
    #     return True

    def device_name(self):
        c = ("PETALITE AFE", 1, 2)
        return (c[0], "", "Name", c)

    def readBlockFlasher(self, address_from_file: int, cmd: int, byte_count: int = -1) -> Tuple[bytearray, bool]:
        return self.readBytes(address_from_file, int(cmd), int(byte_count), use_pec=self.pec)

    def writeBlockFlasher(self, address_from_file: int, cmd: int, buffer: bytearray | bytes) -> bool:
        print("BQ76 write bytes", address_from_file, cmd, hexlify(buffer).decode())  # DEBUG
        return self.writeBytes(address_from_file, int(cmd), bytearray(buffer), use_pec=self.pec)


    # ----------------------------------------------------------------------------------------------


    def is_ready(self) -> bool:
        ok = False
        try:
            _, ok = self.readBytes(self.address, 0x00, 1, use_pec=False)  # check if we can get the first byte of CONTROL STATUS without PEC
        except OSError as ex:
            pass
        return ok


    def wait_for_ready(self, timeout_ms: int = 250, invert: bool = False, throw: bool = False) -> bool:
        t0 = monotonic_ns()
        pause = int(timeout_ms * 100)  # = timeout_ms/10 * 1000
        while ((monotonic_ns() - t0) / 1000000) < timeout_ms:
            if not invert and self.is_ready(): return True
            if invert and not self.is_ready(): return True
            sleep(pause / 1000000)
        if throw: 
            raise IOError("Timeout {}ms while waiting for AFE ready.".format(timeout_ms))
        return False


    # ----------------------------------------------------------------------------------------------

    def is_sealed(self, refresh: bool = False) -> bool:
        """
        Check if battery is sealed including retries on bus error.
        Takes up to 1s before throwing finally.

        Args:
            refresh (bool, optional): if True, the operation_status shadow will be read fresh from battery before analyze its flags. Defaults to False.

        Returns:
            bool: True, if sealed False otherwise
        """

        if refresh or self._battery_status is None:
            # using a more robust implementation to read operation_status at this point
            # as we had issues on EOL test's shipping mode function here
            #self.read_battery_status_robust()
            self.read_battery_status()
        _sec_bits = tuple(int(self._battery_status[k]) for k in ("SEC1", "SEC0"))
        return _sec_bits == (1, 1)  # both bits set means sealed


    def is_unsealed(self, check_fullaccess: bool = False, refresh: bool = False) -> bool:
        """Checks if the battery is sealed including retries on bus error.

        Takes up to 1s before throwing finally.

        NOTE: Something is wrong in the manual.
              Reality: SEC = 10 -> UNSEAL, SEC = 01 -> FULL_ACCESS
              Manual says 10 -> FULL_ACCESS, SEC = 01 -> UNSEAL

           Args:
             check_fullaccess (bool): if check_fullaccess is true, it also checks if battery is in full access mode.
             refresh (bool): if True, the operation_status shadow will be read fresh from battery before analyze its flags

           Returns
              (bool): true of the device is NOT sealed if check_fullaccess is true,
                      else only true if battery is unsealed and in full access mode.
        """

        if refresh or self._battery_status is None:
            # using a more robust implementation to read operation_status at this point
            # as we had issues on EOL test's shipping mode function here
            #self.read_battery_status_robust()
            self.read_battery_status()
        # using shadow copy to avoid bus access
        _sec_bits = tuple(int(self._battery_status[k]) for k in ("SEC1", "SEC0"))
        if check_fullaccess:
            return _sec_bits in ((0, 1), (0, 0))  # full access
        return _sec_bits == (1, 0)  # unsealed


    #----------------------------------------------------------------------------------------------


    def _write_key(self, key: int | bytes | bytearray | str) -> None:
        """Writes a given key of 32bits to the battery by manufacturer_access.

            Used to unseal the battery for TI chipsets.

            Args:
               key (int | bytes | bytearray | str): either a 32bit integer or bytes, bytearray of 4 bytes or a string of 8 hex characters,
                            optionally preceded by a colon ":"
            Exceptions:
                AttributeError - if key is neither an integer nor string
                TypeError - if key is not in correct form for unhexlify()
            Returns
                None
        """
        #hexlify(unseal_key, ':').decode()
        if isinstance(key, int):
            ikey = key # already integer
        elif isinstance(key, bytearray) or isinstance(key, bytes):
            ikey = int.from_bytes(key, "big")
        elif isinstance(key, str):
            if key[0] == ":":
                b = unhexlify(key[1:])
            else:
                b = unhexlify(key)
            ikey = int.from_bytes(b, "big")
        else:
            raise AttributeError("Invalid battery key")

        self.write_subcommand(ikey & 0xffff)         # low word first
        self.write_subcommand((ikey >> 16) & 0xffff) # high word then


    def unseal(self,
               unseal_key: int | bytes | bytearray | str,
               fullaccess_key: int | bytes | bytearray | str = None,
               force: bool = False) -> bool:
        """Unseals the battery using a key given in hexadecimal format.

           Note: this function needs to have is_unsealed() implemented!

           The key can also be given in key encoded format, prepend a colon
           in this case (":abcdef...").

            Args:
                (string): unseal_key
                (string): fullaccess_key
                (bool): True do NOT check if unseald. Defaults to False.

            Returns:
                (boolean)
        """
        check_fullaccess=fullaccess_key is not None
        if (not force) and self.is_unsealed(check_fullaccess=check_fullaccess, refresh=True):
            return True # already in correct mode
        # Note: After sealing, the bq will not accept unsealing for about
        #       3s to 5s, therefore we retry.
        for _ in range(0, 20):
            self._write_key(unseal_key)
            sleep(0.25) # wait a bit (250ms)
            if self.is_unsealed():
                #print("bestens")
                break
        sleep(0.1)
        if not self.is_unsealed(refresh=True):
            return False
        if fullaccess_key is None:
            return True # only unseal needed
        sleep(0.1)
        if self.is_unsealed(check_fullaccess=True, refresh=True):
            return True # already full access without dedicated key
        #print("try full access")
        # Batteries might need a time between 1s and 4s to accept full access
        # after the unseal key was written.
        for _ in range(0, 8):
            sleep(0.5)
            self._write_key(fullaccess_key)
            if self.is_unsealed(check_fullaccess=True, refresh=True):
                #print("superbestens")
                return True
        #print("grrr")
        return False


    # ------------------------------------------------
    # --- commands that work only in unsealed mode ---
    # ------------------------------------------------

    def seal(self) -> bool:
        """Seals the battery."""
        if self.is_sealed(refresh=True): return True
        self.write_subcommand(0x0030)  # this is chipset specific! Send SEAL command
        sleep(0.1)
        if not self.is_sealed(refresh=True): return False
        # After sealing quite a few commands are not recognised by the bq.
        # Therefore we explicitly wait before proceeding with further script
        # actions.
        sleep(0.5) # was 5s !!!
        return True


    def enable_full_access(self) -> bool:
        #
        # no encrypted keys here!
        #
        #return self.unseal(0x8D21FAC3, 0x63DB2CE4)  # low-word goes first to battery
        return self.unseal(0xEC5D9F23, 0x3E5F75CE)  # low-word goes first to battery


    # ----------------------------------------------------------------------------------------------


    def _control_status_to_dict(self, buf: bytearray, hexi: None | bool | str = None) -> OrderedDict[str, bytes | bytearray | str | int]:
        os = unpack("<H", buf)[0]
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "RSVD":      ((os>>3) & (1<<12)-1),
            "DEEPSLEEP":  ((os>>2) & 1),
            "LD_TIMEOUT": ((os>>1) & 1),
            "LD_ON":      ((os>>0) & 1),
        })

    def read_control_status(self) -> Tuple[int, bool]:
        buf, ok = self.readBytes(self.address, 0x00, 2)
        if ok:
            return self._control_status_to_dict(buf), True
        else:
            None, False


    #----------------------------------------------------------------------------------------------


    def _battery_status_to_dict(self, buf: bytearray, hexi: None | bool | str = None) -> OrderedDict[str, bytes | bytearray | str | int]:
        os = unpack("<H", buf)[0]
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "SLEEP":     ((os>>15) & 1),
            "RSVD1":     ((os>>14) & 1),
            "SDM":       ((os>>13) & 1),
            "PF":        ((os>>12) & 1),
            "SS":        ((os>>11) & 1),
            "FUSE":      ((os>>10) & 1),
            "SEC1":      ((os>>9) & 1),
            "SEC0":      ((os>>8) & 1),
            "OTPB":      ((os>>7) & 1),
            "OTPW":      ((os>>6) & 1),
            "COW_CHK":   ((os>>5) & 1),
            "WD":        ((os>>4) & 1),
            "POR":       ((os>>3) & 1),
            "SLEEP_EN":  ((os>>2) & 1),
            "PCHG_MODE": ((os>>1) & 1),
            "CFGUPDATE": ((os>>0) & 1),
        })

    def read_battery_status(self) -> Tuple[int, bool]:
        buf, ok = self.readBytes(self.address, 0x12, 2)
        if ok:
            self._battery_status = self._battery_status_to_dict(buf)
        return _od2t(self._battery_status)
        

    def read_battery_status_robust(self, retries: int = 10, pause_on_retry: float = 0.1) -> None:
        """Reads battery_status() until successfully read or throw after limit of retries."""
        retries = int(retries)
        while (retries >= 0):
            try:
                self.read_battery_status()  # => update the self._operation_status attribute
            except OSError as ex:
                sleep(pause_on_retry)
                if retries == 0:
                    raise ex  # no more retries -> propagate failure
            finally:
                retries -= 1



    #----------------------------------------------------------------------------------------------


    def _alarm_status_to_dict(self, buf: bytearray, hexi: None | bool | str = None) -> OrderedDict[str, bytes | bytearray | str | int]:
        os = unpack("<H", buf)[0]
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "SSBC":     ((os>>15) & 1),
            "SSA":      ((os>>14) & 1),
            "PF":       ((os>>13) & 1),
            "MSK_SFALERT": ((os>>12) & 1),
            "MSK_PFALERT": ((os>>11) & 1),
            "INITSTART": ((os>>10) & 1),
            "INITCOMP": ((os>>9) & 1),
            "RSVD1":    ((os>>8) & 1),
            "FULLSCAN": ((os>>7) & 1),
            "XCHG":     ((os>>6) & 1),
            "XDSG":     ((os>>5) & 1),
            "SHUTV":    ((os>>4) & 1),
            "FUSE":     ((os>>3) & 1),
            "CB":       ((os>>2) & 1),
            "ADSCAN":   ((os>>1) & 1),
            "WAKE":     ((os>>0) & 1),
        })

    def read_alarm_status(self) -> Tuple[int, bool]:
        buf, ok = self.readBytes(self.address, 0x62, 2)
        if ok:
            self._alarm_status = self._alarm_status_to_dict(buf)
            return self._alarm_status, True
        else:
            return None, False


    #----------------------------------------------------------------------------------------------


    def write_subcommand(self, subcmd: int, data: bytes | bytearray = None, timeout: float = 3.0) -> bool:
        """Write a subcommand with optional data to the BQ76942.

        Args:
            subcmd (int): The subcommand to write.
            data (bytes | bytearray, optional): Optional data to send with the subcommand. Defaults to b''.
        """

        if not (0 <= subcmd <= 0xFFFF):
            raise ValueError("Subcommand must be a 16-bit value (0-65535).")
        if data:
            wholeblock = [subcmd & 0xFF, ((subcmd >> 8) & 0xFF)] + ([data & 0xff] if isinstance(data, int) else list(data))
            checksum = ~sum(wholeblock) & 0xFF # bitwise inverse
            if not self.writeBytes(self.address, 0x3E, bytearray(wholeblock), use_pec=self.pec):  # write data to the data registers starting at 0x3E including the address
                return False
            return self.writeBytes(self.address, 0x60, bytearray([checksum, len(wholeblock) + 2]), use_pec=self.pec)  # write data to the data registers starting at 0x60
        else:
            return self.writeWord(0x3E, subcmd)  # write Subcommand to the registers 0x3E and 0x3F
        #return True


    #----------------------------------------------------------------------------------------------


    def read_subcommand(self, subcmd: int, length: int = 0, timeout: float = 5.0,
                        pause_before_data_available: float = None,
                        hexi: None | bool | str = None) -> bytes | bytearray | str:
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
        if not self.writeWord(0x3E, subcmd):  # write Subcommand to the registers 0x3E and 0x3F
            return False

        if pause_before_data_available is not None:
            sleep(pause_before_data_available)

        t0 = monotonic_ns()  # common timeout over the rest of the function
        response = 0xFFFF
        while response != subcmd:
            response, ok = self.readWord(0x3E)
            t1 = monotonic_ns()
            if (t1 - t0) > (timeout * 1e+9):  # scale timeout to ns
                raise TimeoutError("While wait for subcommand to complete.")
            sleep(0.005)
        # data is ready now
        buf, ok = self.readBytes(self.address, 0x3E, 36, use_pec=self.pec)
        if not ok:
            raise IOError("Could not read from BQ76942.")
        #print(list(buf))  # DEBUG
        incoming_cs, count = list(buf[-2:])  # get expected checksum and length
        checksum = ~sum(buf[:-2]) & 0xFF  # bitwise inverse
        # verify checksum
        if checksum != incoming_cs:
           raise IOError("Checksum mismatch reading from BQ76942.")
        # success
        if length > 0:
            if length > 32:
                length = 32
            else:
                pass
        else:
            length = (count - 4) if (count > 4) else 0   # exclude overhead
        #print(subcmd, "->", list(buf[2:(2 + length)]))  # DEBUG
        return buf[2:(2 + length)]

    #----------------------------------------------------------------------------------------------


    def read_cell_voltages(self) -> np.array:
        """Read cell voltages from the BQ76942.

        Args:
            count (int): Number of cell voltages to read (3 to 10).
        Returns:
            List[float], List[str]: List of voltages read, all values in raw as hex format str.
        """

        scale = [self._standard_scale_volt] * self._max_possible_cells
        voltages = ()
        regadr = 0x14 # base register address for Cell 1 Voltage
        for i in range(10):  # 10 cells
            raw, ok = self.readWord(regadr)
            volt = raw * scale[i]  # scale returned value into Volts
            voltages += (volt,)
            regadr += 2
            sleep(0.005)
        return np.array(voltages)


    #----------------------------------------------------------------------------------------------

    def read_pack_voltage(self) -> float:
        """Read the pack voltage from the BQ76942.

        Returns:
            float, bool: The pack voltage in volts and a boolean indicating success.
        """

        raw, ok = self.readWord(0x36)  # PACK Voltage register
        if not ok:
            return None
        volt = raw * self._user_scale_volt  # scale returned value into Volts
        return volt

    #----------------------------------------------------------------------------------------------

    def read_tos_voltage(self) -> float:
        """Read the TOS voltage from the BQ76942.

        Returns:
            float, bool: The TOST voltage in volts and a boolean indicating success.
        """

        raw, ok = self.readWord(0x34)  # TOS Voltage register
        if not ok:
            return None
        volt = raw * self._user_scale_volt  # scale returned value into Volts
        return volt


    #----------------------------------------------------------------------------------------------


    def read_ld_voltage(self) -> float:
        """Read the LD voltage from the BQ76942.

        Returns:
            float, bool: The LD voltage in volts and a boolean indicating success.
        """

        raw, ok = self.readWord(0x38)  # LD Voltage register
        if not ok:
            return None
        volt = raw * self._user_scale_volt  # scale returned value into Volts
        return volt


    #----------------------------------------------------------------------------------------------


    def read_cc2_current(self) -> float:
        """Read the CC2 current from the BQ76942.

        Returns:
            float, bool: The CC2 current in Amperes and a boolean indicating success.
        """
       
        raw, ok = self.readWord(0x3A, signed=True)  # CC2 Current register
        if not ok:
            return None
        curr = raw * self._standard_scale_current  # scale returned value into Amperes
        return curr


    #----------------------------------------------------------------------------------------------


    def read_temperatures(self) -> Tuple[float]:
        """Read temperature values from the BQ76942.

        Args:
            hexi (None | bool | str, optional): If set to True or a string separator, the returned bytes will be hexlified.
                                                Defaults to None.
        Returns:
            List[float], List[str]: List of temperatures read, all values in raw as hex format str.
        """

       
        scale = [self._standard_scale_temp] * self._max_possible_cells
        temperatures = ()
        #raw = ()
        regadr = 0x68 # base register address for Temperature 1
        for i in range(10):  # 3 internal + 1 external temperature:
            raw, ok = self.readWord(regadr, signed=True)
            if raw is None:
                raise IOError("Could not read from IC.")
            temp = (raw * scale[i]) - KELVIN_ZERO_DEGC  # scale returned value into °C
            temperatures += (temp,)
            #raw += (_maybe_hexlify(tckelvin.to_bytes(2, "little"), hexi),)
            regadr += 2
            sleep(0.005)
        return temperatures


    #----------------------------------------------------------------------------------------------

    def _decode_safety_status(self, buf: bytearray| bytes, hexi: bool | str | None = None) -> OrderedDict:

        def _b_to_dict_A(b: bytearray) -> OrderedDict[str, bytes | bytearray | str | int]:
            os = unpack("<B", b)[0]
            return OrderedDict({
                "block": _maybe_hexlify(b, hexi),
                # data come little endian
                "SCD": ((os>>7) & 1),  #
                "OCD2": ((os>>6) & 1),  #
                "OCD1": ((os>>5) & 1),  #
                "OCC": ((os>>4) & 1),  #
                "COV": ((os>>3) & 1),  #
                "CUV": ((os>>2) & 1),  #
                "RSVD1": ((os>>1) & 1),  # Reserved. Do not use.
                "RSVD2": ((os>>0) & 1),  # Reserved. Do not use.
            })

        def _b_to_dict_B(b: bytearray) -> OrderedDict[str, bytes | bytearray | str | int]:
            os = unpack("<B", b)[0]
            return OrderedDict({
                "block": _maybe_hexlify(b, hexi),
                # data come little endian
                "OTF": ((os>>7) & 1),  #
                "OTINT": ((os>>6) & 1),  #
                "OTD": ((os>>5) & 1),  #
                "OTC": ((os>>4) & 1),  #
                "RSVD1": ((os>>3) & 1),  # Reserved. Do not use.
                "UTINT": ((os>>2) & 1),  #
                "UTD": ((os>>1) & 1),  #
                "UTC": ((os>>0) & 1),  #
            })

        def _b_to_dict_C(b: bytearray) -> OrderedDict[str, bytes | bytearray | str | int]:
            os = unpack("<B", b)[0]
            return OrderedDict({
                "block": _maybe_hexlify(b, hexi),
                # data come little endian
                "OCD3": ((os>>7) & 1),  #
                "SCDL": ((os>>6) & 1),  #
                "OCDL": ((os>>5) & 1),  #
                "COVL": ((os>>4) & 1),  #
                "RSVD1": ((os>>3) & 1),  # Reserved. Do not use.
                "PTO": ((os>>2) & 1),  #
                "HWDF": ((os>>1) & 1),  #
                "RSVD2": ((os>>0) & 1),  # Reserved. Do not use.
            })

        da_A = _b_to_dict_A(buf[0:1])
        ds_A = _b_to_dict_A(buf[1:2])
        da_B = _b_to_dict_B(buf[2:3])
        ds_B = _b_to_dict_B(buf[3:4])
        da_C = _b_to_dict_C(buf[4:5])
        ds_C = _b_to_dict_C(buf[5:6])

        # combine the ordered dicts
        d = da_A | ds_A | da_B | ds_B | da_C | ds_C
        return d


    def read_safety_status(self, hexi: bool | str | None = None) -> tuple:
        buf, ok = self.readBytes(self.address, 0x02, 6, use_pec=self.pec)
        self._safety_status = self._decode_safety_status(buf, hexi=hexi)
        return _od2t(self._safety_status)  # Teststand interface
        #return self._safety_status


    def _decode_fet_status(self, buf: bytearray| bytes, hexi: bool | str | None = None) -> OrderedDict:
        os = unpack_from("<B", buf, 0)[0]
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "RSVD0": ((os>>7) & 1),
            "ALRT_PIN": ((os>>6) & 1),
            "DDSG_PIN": ((os>>5) & 1),
            "DCHG_PIN": ((os>>4) & 1),
            "PDSG_FET": ((os>>3) & 1),
            "DSG_FET": ((os>>2) & 1),
            "PCHG_FET": ((os>>1) & 1),
            "CHG_FET": ((os>>0) & 1),
        })


    def read_fet_status(self, hexi: bool | str| None = None) -> OrderedDict:
        buf, ok = self.readBytes(self.address, 0x7F, 1, use_pec=self.pec)
        self._fet_status = self._decode_fet_status(buf, hexi=hexi)
        return _od2t(self._fet_status)


    def _decode_manufacturing_status(self, buf: bytearray| bytes, hexi: bool | str | None = None) -> OrderedDict:
        os = unpack_from("<B", buf, 0)[0]
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "OTPW_EN": ((os>>7) & 1),
            "PF_EN": ((os>>6) & 1),
            "PDSG_TEST": ((os>>5) & 1),
            "FET_EN": ((os>>4) & 1),
            "RSVD": ((os>>3) & 1),
            "DSG_TEST": ((os>>2) & 1),
            "CHG_TEST": ((os>>1) & 1),
            "PCHG_TEST": ((os>>0) & 1),
        })

    def read_manufacturing_status(self, hexi: bool | str| None = None) -> int:
        buf = self.read_subcommand(0x0057)
        self._fet_status = self._decode_manufacturing_status(buf, hexi=hexi)
        return self._fet_status


    def charge_test(self, hexi: bool | str| None = None) -> bool:
        return self.write_subcommand(0x001F)

    def discharge_test(self, hexi: bool | str| None = None) -> bool:
        return self.write_subcommand(0x0020)


    def all_fets_on(self, hexi: bool | str| None = None) -> bool:
        """Using build-in function of BQ76942.

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.

        Returns:
            bool: _description_
        """
        
        return self.write_subcommand(0x0096)


    def all_fets_off(self, hexi: bool | str| None = None) -> bool:
        """Using build-in function of BQ76942.

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.

        Returns:
            bool: _description_
        """
        return self.write_subcommand(0x0095)


    def toggle_fet_enable(self, hexi: bool | str| None = None) -> bool:
        return self.write_subcommand(0x0022)


    def enable_fets(self, timeout: float = 10.0) -> None:
        """ENABLE FETs using toggle and flag check.

        Args:
            timeout (float, optional): _description_. Defaults to 10.0.

        Raises:
            RuntimeError: _description_
        """
        n = int(round(timeout * 10))  # in 100ms rounds
        while n > 0:
            self.read_fet_status()
            status = self._fet_status
            if (status["DDSG_PIN"] == 0) and (status["CHG_FET"] == 1) and (status["DSG_FET"] == 1):
                return
            print(status)  # DEBUG
            #if (status["DDSG_PIN"] == 0):
            _ok = self.toggle_fet_enable()
            sleep(0.1)
            n -= 1
        raise RuntimeError(f"Could not enable FET {status}")

    
    def disable_fets(self, timeout: float = 10.0) -> None:
        """DISABLE FETs using toggle and flag check.

        Args:
            timeout (float, optional): _description_. Defaults to 10.0.

        Raises:
            RuntimeError: _description_
        """
        n = int(round(timeout * 10))  # in 100ms rounds
        while n > 0:
            self.read_fet_status()
            status = self._fet_status
            if (status["DDSG_PIN"] == 1) and (status["CHG_FET"] == 0) and (status["DSG_FET"] == 0):
                return
            print(status)  # DEBUG
            #if (status["DDSG_PIN"] == 1):
            _ok = self.toggle_fet_enable()
            sleep(0.1)
            n -= 1
        raise RuntimeError(f"Could not disable FET {status}")



    def read_dastatus(self) -> Tuple[List[int], List[int]]:
        """Reads all DAStatus 1 to 3

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.

        Returns:
            Tuple[List[int], List[int]]: _description_
        """

        buf1 = self.read_subcommand(0x0071)  # DASTATUS1
        buf2 = self.read_subcommand(0x0072)  # DASTATUS2
        buf3 = self.read_subcommand(0x0073)  # DASTATUS3
        #buf4 = self.read_subcommand(0x0074)  # DASTATUS4

        _fmt = "<L"  # unsigned long, 4 bytes
        all_items = [n[0] for n in list(chain.from_iterable([iter_unpack(_fmt, bytes(buffer)) for buffer in [buf1, buf2, buf3]]))]
        self.cell_voltage_counts = all_items[::2]  # every 2nd is a voltage count, starting from first element
        self.cell_current_counts = all_items[1::2]  # every 2nd is a current count, starting from 2nd element
        #print(self.cell_voltage_counts)
        #print(self.cell_current_counts)
        return self.cell_voltage_counts, self.cell_current_counts


    def read_dastatus_average(self, num_samples: int, pause_between: float = 0.005) -> Tuple[List[float], List[float]]:
        _cell_voltages = [0] * self._max_possible_cells
        _cell_currents = [0] * self._max_possible_cells     
        for n in enumerate(range(int(num_samples))):
            _cv, _cc = self.read_dastatus()
            if len(_cv) < len(_cell_voltages):
                raise ValueError(f"Not enough cell voltage data {len(_cv)}")
            for i in range(len(_cell_voltages)):
                _cell_voltages[i] += _cv[i]
                _cell_currents[i] += _cc[i]
            if pause_between and (float(pause_between) > 0):
                sleep(float(pause_between))
        return [(v / num_samples) for v in _cell_voltages], [(a / num_samples) for a in _cell_currents]


    def read_cal1(self, hexi: bool | str | None = None) -> OrderedDict:
        """READ_CAL1 - Mix of different calibration values.

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.

        Returns:
            dict: _description_
        """
        buf = self.read_subcommand(0xF081)
        self.calibration_counts = OrderedDict({
                "block": _maybe_hexlify(buf, hexi),
                # data come little endian
                "calibration_data_counter": unpack_from("<H", buf, 0)[0],
                "cc2_counts": unpack_from("<l", buf, 2)[0],
                "pack_pin_adc_counts": unpack_from("<h", buf, 6)[0],
                "tos_adc_counts": unpack_from("<h", buf, 8)[0],
                "ld_pin_adc_counts": unpack_from("<h", buf, 10)[0],
            })
        return self.calibration_counts


    def read_cal1_average(self, num_samples: int, pause_between: float = 0.005) -> OrderedDict:
        cal1 = OrderedDict({})
        for n in range(int(num_samples)):
            d = self.read_cal1()
            for k,v in d.items():
                u = cal1.get(k, 0)  # fill and sum
                if isinstance(v, (int, float)):
                    cal1[k] = u + v
                else:
                    cal1[k] = v
            if pause_between and (float(pause_between) > 0):
                sleep(float(pause_between))
        result = OrderedDict({})
        for k,v in cal1.items():
            result[k] = (v / num_samples) if isinstance(v, (int,float)) else v
        return result
    

    #----------------------------------------------------------------------------------------------


    def calib_write_cell_voltages(self, reference_cell_voltages: np.array, num_samples: int = 10, pause_between: float = 0.005) -> Tuple[float, np.array]:
        reference_cell_voltages = list(reference_cell_voltages)
        # Take the average of measurements and calculate gains        
        cell_voltage_counts, _  = self.read_dastatus_average(num_samples=int(num_samples), pause_between=pause_between)
        if len(cell_voltage_counts) != len(reference_cell_voltages):
            raise ValueError(f"Length of parameter array reference_cell_voltages {len(reference_cell_voltages)} has to match length of cell_voltage_counts {len(cell_voltage_counts)}.")
        
        # calculate the cell gains
        _dummy_gain = 0  # 12100
        cell_gain = [0] * len(cell_voltage_counts)
        for i in range(0, len(cell_gain)):
            _test_voltage = reference_cell_voltages[i]  # in Volts
            _adc_counts = cell_voltage_counts[i]
            print(_test_voltage, _adc_counts)  # DEBUG
            if _adc_counts == 0:
                # avoid div by zero
                cell_gain[i] = _dummy_gain
                continue
            test_v = 3.03 / 2**24 * _adc_counts  # DEBUG
            gain = 2**24 * ((_test_voltage * 1e+3) / _adc_counts)  # 5 x 1.212V / 2**23 = 6,06V / 2**23 => 3,03 / 2**24 * _adc_counts = _test_voltage
            if gain < -32768 or gain > 32767:
                gain = _dummy_gain
            cell_gain[i] = int(round(gain))
            print("Cell ",i+1," Gain = ", cell_gain[i])  # DEBUG

        # Calculate Cell Offset based on Cell1
        #cell_offset = ((cell_gain[0] * cell_voltage_counts_a[0]) / 2**24) - 2500
        cell_offset_float = ((cell_gain[0] * cell_voltage_counts[0]) / 2**24) - (reference_cell_voltages[0] * 1e+3)
        cell_offset = int(round(cell_offset_float))
        print("Cell Offset:", cell_offset_float, "->", cell_offset)  # DEBUG
        # write voltage calibration into RAM
        self.enter_config_update_mode()
        self.write_cell_offset(cell_offset)
        # Cell Voltage Gains
        self.write_cell_gain(cell_gain)
        self.exit_config_update_mode()
        return float(cell_offset), np.array([float(g) for g in cell_gain])  # Teststand easier to handle


    def calib_write_pack_tos_ld_voltages(self, ref_pack_voltage: float, ref_tos_voltage: float, ref_ld_voltage: float, 
                                       num_samples: int = 10, pause_between: float = 0.005) -> Tuple[float]:
        d = self.read_cal1_average(num_samples=num_samples, pause_between=pause_between)
        # Calculate PACK, TOS, LD gains by using the measured voltages in cV (not mV !!)
        PACK_Gain = int(round(2**16 * ((ref_pack_voltage * 1e+2) / d["pack_pin_adc_counts"])))
        TOS_Gain = int(round(2**16 * ((ref_tos_voltage * 1e+2) / d["tos_adc_counts"])))
        LD_Gain = int(round(2**16 * ((ref_ld_voltage * 1e+2) / d["ld_pin_adc_counts"])))
        # write voltage calibration into RAM
        self.enter_config_update_mode()
        self.write_pack_gain(PACK_Gain)
        self.write_tos_gain(TOS_Gain)        
        self.write_ld_gain(LD_Gain)        
        self.exit_config_update_mode()
        return PACK_Gain, TOS_Gain, LD_Gain
   

    def calib_write_board_offset_current(self, num_samples: int = 10, pause_between: float = 0.005) -> float:
        stored_board_offset = self.read_board_offset()
        stored_offset_samples = self.read_coulomb_counter_offset_sample()
        # should be 64 but we calculate here with 1
        offset_samples = 1  # stored_offset_samples
        d = self.read_cal1_average(num_samples=num_samples, pause_between=pause_between)
        board_offset = offset_samples * int(round(d["cc2_counts"] * 1e+1))
        if board_offset < -32768 or board_offset > 32767:
            raise ValueError(f"Board_offset out of boundaries -> cannot calibrate current: {board_offset}")
        self.enter_config_update_mode()
        self.write_board_offset(board_offset)
        self.exit_config_update_mode()
        return board_offset


    def calib_write_cc_gain_and_capacity_gain(self, ref_current: float, num_samples: int = 10, pause_between: float = 0.005) -> Tuple[float, float]:        
        num_samples = int(num_samples)
        stored_cc_gain = self.read_cc_gain()
        stored_capacity_gain = self.read_capacity_gain()
        cc2_current = 0
        for n in range(num_samples):
            cc2_current += self.read_cc2_current()
            if pause_between and (pause_between > 0):
                sleep(pause_between)
        cc2_current = cc2_current / num_samples
        #cc_gain_float = (current_diff / cc_counts_diff) / 1e-3
        #cc_gain_float = (current_diff / cc2_current_diff) * stored_cc_gain  # alternative calculation using CC2 current directly
        cc_gain_float = (ref_current / cc2_current) * stored_cc_gain  # alternative calculation using CC2 current directly
        capacity_gain_float = 298261.6178 * cc_gain_float  # Note: constant 298261.6178 comes from TI doc
        # write calibration into RAM
        self.enter_config_update_mode()
        self.write_cc_gain(cc_gain_float)
        self.write_capacity_gain(capacity_gain_float)
        self.exit_config_update_mode()
        return cc_gain_float, capacity_gain_float


    def calib_write_temperatures(self, reference_temperature: float, num_samples: int = 5, pause_between: float = 0.05) -> Tuple[float]:
        """Expects a calibration reference temperature as INPUT and calculates from that
        the following offsets:
        
            Internal Temperature
            CFETOFF Temperature (CFETOFF pin thermistor) - unused
            DFETOFF Temperature (DFETOFF pin thermistor) - unused
            ALERT Temperature (ALERT pin thermistor) - unused
            TS1 (TS1 pin thermistor)
            TS2 (TS2 pin thermistor) - unused
            TS3 (TS3 pin thermistor)
            HDQ Temperature (HDQ pin thermistor)
            DCHG Temperature (DCHG pin thermistor)
            DDSG Temperature (DDSG pin thermistor)

        Args:
            temp_cal (Tuple[float]): Calibrated reference temperature
        """

        num_samples = int(num_samples)  # Teststand
        # 1) measure the temperatures (10 measurement points)
        t_meas = [0.0] * 10
        for n in range(num_samples):
            t0 = self.read_temperatures()
            for i in range(len(t_meas)):
                t_meas[i] += t0[i]
            if pause_between:
                sleep(pause_between)
        t_meas = [t / num_samples for t in t_meas]
        # 2) calculate the offsets
        temp_offsets = [(float(reference_temperature - t) if t > -100 else 0) for t in t_meas]
        #print("T-OFFSETS:", temp_offsets)
        # 3) write the temperature calibration values
        self.enter_config_update_mode()
        self.read_temperature_calibration_offsets() # stores them into afe.temperature_calibration_offsets        
        self.write_temperature_calibration_offsets(temp_offsets)
        self.exit_config_update_mode()        
        return tuple(temp_offsets)


    # ----------------------------------------------------------------------------------------------


    def read_cell_gain(self) -> list:
        buf = bytearray()
        for i in range(18):
            buf += self.read_subcommand(0x9180 + i*2)
        _fmt = "<h"  # signed short, 2 bytes
        self.cell_gain = [n[0] for n in list(chain.from_iterable(iter_unpack(_fmt, buf)))]
        return self.cell_gain


    def write_cell_gain(self, cell_gain_list: list = None) -> bool:
        if cell_gain_list is None:
            if self.cell_gain is None:
                raise ValueError("Need to provide a cell gain calibration list to write.")
            cell_gain_list = self.cell_gain
        if len(cell_gain_list) > 17:
            raise ValueError(f"A maximum if 17 values is allowed, but presented {len(cell_gain_list)}.")
        _fmt = "<h"  # signed short, 2 bytes
        for i in range(len(cell_gain_list)):
            buf = pack(_fmt, cell_gain_list[i])
            if not self.write_subcommand(0x9180 + i*2, data=buf):
                return False
        return True


    def write_cell_offset(self, cell_offset: int) -> bool:
        buf = pack("<h", cell_offset)
        return self.write_subcommand(0x91B0, data=buf)


    def read_pack_gain(self) -> int:
        buf = self.read_subcommand(0x91A0)
        return unpack_from("<H", buf, 0)[0]

    def write_pack_gain(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91A0, data=buf)


    def read_tos_gain(self) -> int:
        buf = self.read_subcommand(0x91A2)
        return unpack_from("<H", buf, 0)[0]

    def write_tos_gain(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91A2, data=buf)


    def read_ld_gain(self) -> int:
        buf = self.read_subcommand(0x91A4)
        return unpack_from("<H", buf, 0)[0]

    def write_ld_gain(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91A4, data=buf)


    def read_vdiv_gain(self) -> int:
        buf = self.read_subcommand(0x91B2)
        return unpack_from("<h", buf, 0)[0]  # signed

    def write_vdiv_gain(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91B2, data=buf)


    def read_adc_gain(self) -> int:
        buf = self.read_subcommand(0x91A6)
        return unpack_from("<h", buf, 0)[0]  # signed

    def write_adc_gain(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91A6, data=buf)


    #----------------------------------------------------------------------------------------------


    def read_cc_gain(self) -> float:
        buf = self.read_subcommand(0x91A8)
        #return unpack_from("<f", buf, 0)[0]  # float
        i = unpack_from("<L", buf, 0)[0]  # to int
        v = self._flash_to_float(i)
        return v


    def write_cc_gain(self, value: float) -> bool:
        v = self._float_to_flash(value)
        buf = pack("<L", v)  # pack the bytes as 4 bytes little endian
        return self.write_subcommand(0x91A8, data=buf)

    #----------------------------------------------------------------------------------------------


    def read_capacity_gain(self) -> float:
        buf = self.read_subcommand(0x91AC)
        #return unpack_from("<h", buf, 0)[0]  # signed
        i = unpack_from("<L", buf, 0)[0]  # to int
        v = self._flash_to_float(i)
        return v


    def write_capacity_gain(self, value: float) -> bool:
        #buf = pack("f", value)
        v = self._float_to_flash(value)
        buf = pack("<L", v)  # pack the bytes as 4 bytes little endian
        return self.write_subcommand(0x91AC, data=buf)


    #----------------------------------------------------------------------------------------------


    def read_coulomb_counter_offset_samples(self) -> int:
        buf = self.read_subcommand(0x91C6)
        return unpack("<H", buf)[0]  # unsigned

    def write_coulomb_counter_offset_samples(self, value: int) -> bool:
        buf = pack("<H", value)
        return self.write_subcommand(0x91C6, data=buf)


    def read_board_offset(self) -> int:
        buf = self.read_subcommand(0x91C8)
        return unpack_from("<h", buf, 0)[0]  # signed

    def write_board_offset(self, value: int) -> bool:
        buf = pack("<h", value)
        return self.write_subcommand(0x91C8, data=buf)


    def read_coulomb_counter_offset_sample(self) -> int:
        buf = self.read_subcommand( 0x91C6)
        return unpack_from("<H", buf, 0)[0]  # unsigned


    def read_temperature_calibration_offsets(self, hexi: bool | str | None = None) -> tuple:
        # buf = bytearray()
        # for i in range(10):
        #     buf += self.read_subcommand(0x91CA + i)
        buf = self.read_subcommand(0x91CA, length=9, pause_before_data_available=0.1)
        self.temperature_calibration_offsets = OrderedDict({
                "block": _maybe_hexlify(buf, hexi),
                # data come little endian
                "internal_temperature_offset": unpack_from("<b", buf, 0)[0],
                "cfetoff_temp_offset": unpack_from("<b", buf, 1)[0],
                "dfetoff_temp_offset": unpack_from("<b", buf, 2)[0],
                "ts1_temp_offset": unpack_from("<b", buf, 3)[0],
                "ts2_temp_offset": unpack_from("<b", buf, 4)[0],
                "ts3_temp_offset": unpack_from("<b", buf, 5)[0],
                "hdq_temp_offset": unpack_from("<b", buf, 6)[0],
                "dchg_temp_offset": unpack_from("<b", buf, 7)[0],
                "ddsg_temp_offset": unpack_from("<b", buf, 8)[0],
            })
        return _od2t(self.temperature_calibration_offsets)


    def write_temperature_calibration_offsets(self, temperature_calibration_offsets: dict | List[float], hexi: bool | str | None = None) -> tuple:
        """_summary_

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.
            temperature_calibration_offsets (dict | List[float], optional): Expects a list of celsius offsets as floats. Defaults to None.

        Raises:
            ValueError: _description_
            ValueError: _description_
            ValueError: _description_

        Returns:
            tuple: _description_
        """

        def _celsius_to_tenth_of_kelvin_as_int(value) -> int:
            """converts a Celsius degree float value into an offset of 0.1 KELVIN or Celsius scaled integer.

            Args:
                value (_type_): _description_

            Returns:
                int: _description_
            """

            v = int(round((value * 10), 0))
            if v > 127: v = 127
            if v < -128: v = -128

            print(value, v)
            return v


        if temperature_calibration_offsets is None:
            if self.temperature_calibration_offsets is None:
                raise ValueError("Need to provide a temperature offset calibration dict to write.")
            temperature_calibration_offsets = self.temperature_calibration_offsets
        if isinstance(temperature_calibration_offsets, (tuple, list)):
            if len(temperature_calibration_offsets) > 10:
                raise ValueError("Length of list 'temperature_calibration_offsets' must be maximum of 10.")
            buf = bytearray([pack("<b", _celsius_to_tenth_of_kelvin_as_int(n))[0] for n in temperature_calibration_offsets])
        elif isinstance(temperature_calibration_offsets, dict):
            buf = bytearray([pack("<b", _celsius_to_tenth_of_kelvin_as_int(temperature_calibration_offsets[n]))[0]
                             for n in
                ["internal_temperature_offset",
                "cfetoff_temp_offset",
                "dfetoff_temp_offset",
                "ts1_temp_offset",
                "ts2_temp_offset",
                "ts3_temp_offset",
                "hdq_temp_offset",
                "dchg_temp_offset",
                "ddsg_temp_offset"]
            ])
        else:
            raise ValueError("Argument 'temperature_calibration_offsets' must be either a list or a dict")
        #print(temperature_calibration_offsets)
        #print(hexlify(buf))  # DEBUG
        if not self.write_subcommand(0x91CA, data=buf):
            return False
        return True



    def calibrate_cell_over_voltage(self) -> bool:
        """COV Calibration.
        Apply the desired value for the cell over-voltage threshold to device cell inputs.
        Calibration will use the voltage applied to the top cell of the device.
        For example, Apply 4350mV

        Returns:
            bool: _description_
        """

        ok = True
        ok = ok and self.enter_config_update_mode()
        ok = ok and self.write_subcommand(0xF091)  # execute CAL_COV()
        ok = ok and self.exit_config_update_mode()
        return ok

    def calibrate_cell_under_voltage(self) -> bool:
        """CUV Calibration
        Apply the desired value for the cell under-voltage threshold to device cell inputs.
        Calibration will use the voltage applied to the top cell of the device.
        For example, Apply 2400mV.

        Returns:
            bool: _description_
        """
        ok = True
        ok = ok and self.enter_config_update_mode()
        ok = ok and self.write_subcommand(0xF090)  # execute CAL_CUV()
        ok = ok and self.exit_config_update_mode()
        return ok


    def wait_for_battery_status_flag(self, bs_key: str, state: bool | int, retries: int = 20, pause_on_retry: float = 0.1) -> bool:
        """Wait for battery status flags == state."""
        retries = int(retries)
        while (retries >= 0):
            try:
                self.read_battery_status()  # => update the self._operation_status attribute
                if bool(self._battery_status[bs_key]) == bool(state):
                    break
                sleep(pause_on_retry)
            except OSError as ex:
                sleep(pause_on_retry)
            finally:
                retries -= 1
        return bool(self._battery_status[bs_key]) == bool(state)


    def enter_config_update_mode(self) -> bool:
        if not self.write_subcommand(0x0090):  # write Subcommand to the registers 0x3E and 0x3F
            return False
        return self.wait_for_battery_status_flag("CFGUPDATE", 1)


    def exit_config_update_mode(self) -> bool:
        if not self.write_subcommand(0x0092):
            return False
        return self.wait_for_battery_status_flag("CFGUPDATE", 0)



    def disable_sleepmode(self) -> bool:
        return self.write_subcommand(0x009a)


    def enable_sleepmode(self) -> bool:
        return self.write_subcommand(0x0099)


    def read_otp_wr_check(self) -> Tuple[int, int]:
        buf = self.read_subcommand(0x00a0)
        results = unpack_from("<B", buf, 0)[0]
        data_fail_addr = unpack_from("<H", buf, 1)[0]
        return results, data_fail_addr


    def write_otp(self) -> Tuple[int, int]:
        """This writes to the OTP.

        !! PAY ATTENTION NOT TO CALL WITH UNREADY DATA !!

        Returns:
            Tuple[int, int]: _description_
        """

        buf = self.read_subcommand(0x00a0, pause_before_data_available=0.15)  # SIMULATION
        #buf = self.read_subcommand(0x00a1, pause_before_data_available=0.15)  # !!! HOT FUNCTION !!!
        results = unpack_from("<B", buf, 0)[0]
        data_fail_addr = unpack_from("<H", buf, 1)[0]
        return results, data_fail_addr



    def _float_to_flash(self, value: float) -> int:
        """This is the TI version of "IEEE754" float.
        Something is slightly different.
        """
        if value == 0:
            value += 0.0000001    # avoid log of zero
        if value < 0:
            bNegative = 1
            value *= -1
        else:
            bNegative = 0
        exponent = int( (math.log(value)/math.log(2)) )
        MSB = exponent + 127        # exponent bits
        mantissa = value / (2**exponent)
        mantissa = (mantissa - 1) / (2**-23)
        if (bNegative == 0):
            mantissa = int(mantissa) & 0x7fffff   # remove sign bit if number is positive
        #result = hex(int(round(mantissa + MSB * 2**23)))
        result = int(round(mantissa + MSB * 2**23))
        #print(hex(result))  # DEBUG
        return result


    def _flash_to_float(self, value: int) -> float:
        exponent = 0xff & int(value / (2**23))  # exponent is most significant byte after sign bit
        mantissa = value % (2**23)
        if (0x80000000 & value == 0):   # check if number is positive
            isPositive = 1
        else:
            isPositive = 0
        mantissa_f = 1.0
        mask = 0x400000
        for i in range(0,23):
            if ((mask >> i) & mantissa):
                mantissa_f += 2**(-1*(i+1))
        result = mantissa_f * 2**(exponent-127)
        if not(isPositive):
            result *= -1
        return float(result)



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