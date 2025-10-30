"""
BQ34Z100-R2 Wide Range Fuel Gauge with Impedance Track Technology.

"""

__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

import math
from typing import Tuple
from time import sleep, monotonic_ns
from binascii import hexlify
from struct import pack, unpack, unpack_from, pack_into
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


class BQ34Z100:

    def __init__(self, smbus: BusMaster, slvAddress: int = 0x55, pec: bool = False) -> None:
        """_summary_

        Args:
            smbus (BusMaster): _description_
            slvAddress (int, optional): _description_. Defaults to 0x55.
            pec (bool, optional): _description_. Defaults to False.
        """

        self.bus = smbus
        self.address = int(slvAddress)
        self.pec = bool(pec)
        self._voltage_scale = None
        self._current_scale = None
        self._energy_scale = None
        _bat = self


    # --------------------------------------------

    def __str__(self) -> str:
        return f"BQ34Z100 Fuel Gauge at 0x{self.address} on {self.bus}"

    def __repr__(self) -> str:
        return f"BQ34Z100({repr(self.bus)}, slvAddress={self.address}, pec={self.pec})"

    # --------------------------------------------

    def _read(self, cmd: int, length: int = 1) -> bytes:
        """Read a number of bytes from a given command/register.

        Args:
            cmd (int): The command/register to read from.
            length (int, optional): The number of bytes to read. Defaults to 1.
        Returns: bytes
            The read bytes.
        """

        if length < 1:
            raise ValueError(f"Length must be a positive integer, got {length}.")
        if not (0 <= (cmd + length) <= 0xFF):
            raise ValueError(f"Command + length must be a byte value (0-255), got {cmd} with length {length} = {cmd+length}.")

        data = bytes()
        for i in range(0, length):
            _cmd = cmd + i
            b, ok = self.bus.readBytes(self.address, _cmd, 1, use_pec=self.pec)
            if not ok:
                raise IOError(f"Failed to read {length} bytes from command 0x{_cmd:02X} at address 0x{self.address:02X} on {self.bus}.")
            data = data + bytes(b)

        return data  # return data as bytes

        # if len(data) == 1:
        #     _fmt = "<B"  # unsigned char
        # if len(data) == 2:
        #     _fmt = "<H"  # unsigned short
        # value = unpack(_fmt, data)[0]
        # return value



    # ----------------------------------------------------------------------------------------------
    # Interface for bq_flasher module

    def enable_full_access(self) -> bool:
        # ...
        return True

    def device_name(self):
        c = ("PETALITE GASGAUGE", 1, 2)
        return (c[0], "", "Name", c)


    def readBlockFlasher(self, address_from_file: int, cmd: int, byte_count: int = -1) -> Tuple[bytearray, bool]:
        return self.bus.readBytes(address_from_file, int(cmd), int(byte_count), use_pec=self.pec)

    def writeBlockFlasher(self, address_from_file: int, cmd: int, buffer: bytearray | bytes) -> bool:
        print("BQZ100 write bytes", address_from_file, cmd, hexlify(buffer).decode())  # DEBUG
        return self.bus.writeBytes(address_from_file, int(cmd), bytearray(buffer), use_pec=self.pec)

    # ----------------------------------------------------------------------------------------------


    def write_dataflash_class(self, subclass_and_offset: int, data: bytes | bytearray = None, timeout: float = 3.0) -> bool:
        """Write a data flash subclass to the FLASH of GG, using the subclass ID and offset.
        Data can be ommitted for commands without data.

        Args:
            subclass_and_offset (int): The subclass (LOW) and offset (HIGH) combined into a single 16-bit value.
            data (bytes | bytearray, optional): Optional data to send with the subcommand. Defaults to b''.
        """

        if not (0 <= subclass_and_offset <= 0xFFFF):
            raise ValueError("Subcommand must be a 16-bit value (0-65535).")
        if data:
            if not self.bus.writeWord(self.address, 0x3E, subclass_and_offset, use_pec=self.pec):
                return False
            rd_buf, ok = self.bus.readBytes(self.address, 0x40, 32, use_pec=self.pec)  # read full block
            if not ok:
                raise IOError(f"Could not read page {subclass_and_offset}from BQ34Z100.")

            wholeblock = bytearray(data + rd_buf)[:32]
            #print(list(wholeblock))  # DEBUG
            checksum = ~sum(wholeblock) & 0xFF # bitwise inverse
            if not self.bus.writeBytes(self.address, 0x40, wholeblock, use_pec=self.pec):  # write data to the data registers starting at 0x3E including the address
                return False
            return self.bus.writeBytes(self.address, 0x60, bytearray([checksum]), use_pec=self.pec)  # write data to the data registers starting at 0x60
        else:
            return self.bus.writeWord(0x3E, subclass_and_offset)  # write Subcommand to the registers 0x3E and 0x3F


    #----------------------------------------------------------------------------------------------


    def read_dataflash_class(self, subclass_and_offset: int, length: int = 0, timeout: float = 5.0,
                        pause_before_data_available: float = None,
                        hexi: None | bool | str = None) -> bytes | bytearray | str:
        """Read data from a subcommand.

        Args:
            subclass_and_offset (int): The subclass (LOW) and offset (HIGH) combined into a single 16-bit value.
            timeout (float, optional): Timeout in seconds for the operation. Defaults to 2.0.
            pause_before_data_available (float, optional): Pause time in seconds before checking for data availability. Defaults to None.
            hexi (None | bool | str, optional): If set to True or a string separator, the returned bytes will be hexlified.
                                                Defaults to None.
        Returns:
            bytes | bytearray | str: The data read from the subcommand, possibly hexlified.
        """

        if not (0 <= subclass_and_offset <= 0xFFFF):
            raise ValueError("Subcommand must be a 16-bit value (0-65535).")
        if not self.bus.writeBytes(self.address, 0x61, bytearray([0x00]), use_pec=self.pec):  # enable block data flash control
            return False
        if not self.bus.writeWord(self.address, 0x3E, subclass_and_offset, use_pec=self.pec):  # write Subcommand to the registers 0x3E and 0x3F
            return False

        if pause_before_data_available is not None:
            sleep(pause_before_data_available)

        t0 = monotonic_ns()  # common timeout over the rest of the function
        response = 0xFFFF
        while response != subclass_and_offset:
            response, ok = self.bus.readWord(self.address, 0x3E, use_pec=self.pec)
            t1 = monotonic_ns()
            if (t1 - t0) > (timeout * 1e+9):  # scale timeout to ns
                raise TimeoutError("While wait for subcommand to complete.")
            sleep(0.005)
        # data is ready now
        buf, ok = self.bus.readBytes(self.address, 0x40, 34, use_pec=self.pec)
        if not ok:
            raise IOError("Could not read from BQ76942.")
        #print(list(buf))  # DEBUG
        incoming_cs, count = list(buf[-2:])  # get expected checksum and length
        checksum = ~sum(buf[:-2]) & 0xFF  # bitwise inverse
        # verify checksum
        if checksum != incoming_cs:
           raise IOError("Checksum mismatch reading from BQ76942.")
        # success
        if length <= 0:
            length = 32
        else:
            if length > 32:
                length = 32
            else:
                pass
        return buf[:length]



    #----------------------------------------------------------------------------------------------
    # calibration helpers

    def _helper_parameter_to_dict(self, data: bytes | bytearray, target: OrderedDict | dict) -> OrderedDict:
        if len(data) == 0:
            return target  # nothing to do
        if isinstance(data, dict) or isinstance(data, OrderedDict):
            # transfer into local dict
            for k,v in data.items():
                if k in target:
                    target[k] = v
                else:
                    pass  # ignore unknown keys
        elif isinstance(data, tuple) or isinstance(data, list):
            if isinstance(data[0], (tuple, list)):
                if len(data[0]) != 2:
                    raise ValueError("If data is a list of key-value pairs, each element must have exactly 2 items.")
                # elements are key-value pairs: ('keystr', value)
                for k,v in data:
                    if k in target:
                        target[k] = v
                    else:
                        pass  # ignore unknown keys
            else:
                # simple list of values: transfer them as they come
                if len(data) > len(target):
                    raise ValueError(f"Data tuple/list must have at most {len(target)} elements.")
                keys = list(target.keys())
                for i in range(len(data)):
                    if not isinstance(data[i], (int, float)):
                        raise TypeError("If data is a simple tuple/list of values, each element must be int or float.")
                    target[keys[i]] = data[i]
        else:
            raise TypeError("Data must be a dict, OrderedDict, tuple or list.")

        return target


    def read_calibration_flash_data(self) -> OrderedDict:
        """Get calibration information from the calibration data flash class.

        Returns:
            OrderedDict: Calibration information.
        """

        self._calibration_buf = self.read_dataflash_class(104)
        buf = self._calibration_buf
        self.calibration_data = OrderedDict({
            "cc_gain": self._flash_f4_to_float(unpack_from(">L", buf, 0)[0]),  # need to convert from TI float stunt...
            "cc_delta": self._flash_f4_to_float(unpack_from(">L", buf, 4)[0]),  # need to convert from TI float stunt...
            "cc_offset": unpack_from(">h", buf, 8)[0],
            "board_offset": unpack_from(">b", buf, 10)[0],
            "int_temperature_offset": unpack_from(">b", buf, 11)[0],
            "ext_temperature_offset": unpack_from(">b", buf, 12)[0],
            "voltage_divider": unpack_from(">H", buf, 14)[0],
        })
        return self.calibration_data


    def write_calibration_flash_data(self, data: dict | OrderedDict | Tuple = None) -> bool:
        """Write calibration information to the calibration data flash class.

        Args:
            data (dict | OrderedDict | Tuple): Calibration information to write.

        Returns:
            bool: True if successful, False otherwise.
        """

        if self.calibration_data is None:
            self.read_calibration_flash_data()  # make sure we have the dict with all keys

        if data is None:
            #if self.calibration_data is None:
            #    raise ValueError("No calibration data available to write.")
            data = self.calibration_data
        self.calibration_data = self._helper_parameter_to_dict(data, self.calibration_data)

        buf = bytearray(32)
        pack_into(">L", buf, 0, self._float_to_flash_f4(self.calibration_data.get("cc_gain", 4.684778213500977)))
        pack_into(">L", buf, 4, self._float_to_flash_f4(self.calibration_data.get("cc_delta", 5589155.0)))
        pack_into(">h", buf, 8, self.calibration_data.get("cc_offset", -1432))
        pack_into(">b", buf, 10, self.calibration_data.get("board_offset", -12))
        pack_into(">b", buf, 11, self.calibration_data.get("int_temperature_offset", 0))
        pack_into(">b", buf, 12, self.calibration_data.get("ext_temperature_offset", 0))
        pack_into(">H", buf, 14, self.calibration_data.get("voltage_divider", 5031))
        return self.write_dataflash_class(104, data=buf)


    #----------------------------------------------------------------------------------------------


    def read_powerconfig_flash_data(self) -> OrderedDict:
        """Get power configuration information from the power configuration data flash class.

        Returns:
            OrderedDict: Power configuration information.
        """

        self._powerconfig_buf = self.read_dataflash_class(68)
        buf = self._powerconfig_buf
        self.powerconfig_data = OrderedDict({
            "flash_update_ok_cell_volt": unpack_from(">h", buf, 0)[0],
            "sleep_current": unpack_from(">h", buf, 2)[0],
            "fs_wait": unpack_from(">B", buf, 11)[0],
        })
        return self.powerconfig_data


    def write_powerconfig_flash_data(self, data: dict | OrderedDict | Tuple = None) -> bool:
        """Write power configuration information to the power configuration data flash class.

        Args:
            data (dict | OrderedDict | Tuple): Power configuration information to write.

        Returns:
            bool: True if successful, False otherwise.
        """

        if self.powerconfig_data is None:
            self.read_powerconfig_flash_data()  # make sure we have the dict with all keys

        if data is None:
            # if self.powerconfig_data is None:
            #     raise ValueError("No power configuration data available to write.")
            data = self.powerconfig_data

        self.powerconfig_data = self._helper_parameter_to_dict(data, self.powerconfig_data)
        # Transfer into buffer then into GG
        buf = bytearray(32)
        pack_into(">h", buf, 0, self.powerconfig_data.get("flash_update_ok_cell_volt", 2800))
        pack_into(">h", buf, 2, self.powerconfig_data.get("sleep_current", 10))
        pack_into(">B", buf, 11, self.powerconfig_data.get("fs_wait", 10))
        return self.write_dataflash_class(68, data=buf)


    #----------------------------------------------------------------------------------------------



    def get_voltage_scale(self, force_refresh: bool = False) -> int:
        """
        This command returns the scale factor for the voltage measurement.
        When calibrate the voltage, the value used for calibration in the tool like bqStudio shall be
        the quotient of real voltage divided by the value read from this command.

        Returns:
            float: The voltage scale factor in Volts.
        """

        if not self._voltage_scale or force_refresh:
            # need to update the scale factor from battery
            data = self._read(0x20, 1)  # factor
            value = unpack("<B", data)[0]
            self._voltage_scale = value

        return self._voltage_scale


    def get_current_scale(self, force_refresh: bool = False) -> int:
        """
        This command returns the scale factor for the current flow through the sense resistor.
        When calibrate the current, the value used for calibration in the tool like bqStudio shall be
        the quotient of real current divided by the value read from this command.

        Returns:
            float: The current scale factor in Amperes.
        """

        if not self._current_scale or force_refresh:
            # need to update the scale factor from battery
            data = self._read(0x21, 1)  # factor
            value = unpack("<B", data)[0]
            self._current_scale = value

        return self._current_scale


    def get_energy_scale(self, force_refresh: bool = False) -> int:
        """
        This command returns the scale factor for the energy measurement.
        When calibrate the energy, the value used for calibration in the tool like bqStudio shall be
        the quotient of real energy divided by the value read from this command.

        Returns:
            float: The energy scale factor in Watt-hours.
        """

        if not self._energy_scale or force_refresh:
            # need to update the scale factor from battery
            data = self._read(0x22, 1)  # factor
            value = unpack("<B", data)[0]
            self._energy_scale = value

        return self._energy_scale

    #----------------------------------------------------------------------------------------------


    def _read_control(self, subcmd: int) -> Tuple[int, bytes]:
        """Read a 2-byte value from the control register.

        Args:
            cmd (int): The command/register to read from.
        Returns: int
            The read value.
        """

        # 1st: write the subcommand to the control register (0x00/0x01)
        # buf = pack("<H", subcmd)
        # for i in range(2):
        #     self.bus.writeBytes(self.address, 0x00 + i, buf[i], pec=self.pec)
        if not self.write_control_command(subcmd):
            raise IOError(f"Could not write subcommand {subcmd}")
        # 2nd: read the result as 2-byte value from the control register (0x00/0x01)
        data = self._read(0x00, 2)
        value = unpack("<H", data)[0]
        return value, data  # return also raw data


    def write_control_command(self, w: int, data: bytearray | bytes | int = None) -> bool:
        # write the subcommand to the control register (0x00/0x01)
        ok = True
        buf = pack("<H", w)
        if data:
            buf += bytearray(data)
        if 0:
            for i in range(2):
                ok = ok and self.bus.writeBytes(self.address, 0x00 + i, buf[i:i+1], use_pec=self.pec)
            return ok
        else:
            return self.bus.writeBytes(self.address, 0x00, buf, use_pec=self.pec)

    #----------------------------------------------------------------------------------------------


    def voltage(self) -> float:
        """Read the battery voltage.
        Returns:
            float: The battery voltage in Volts.
        """

        data = self._read(0x08, 2)  # reads in mv
        value = unpack("<H", data)[0]
        if self._voltage_scale:
            value = value * self._voltage_scale
        return float(value) * 1e-3  # convert to V


    def current(self) -> float:
        """Read the battery current with sign.
        Returns:
            float: The battery current in Ampere.
        """

        data = self._read(0x10, 2)  # reads in ma with sign
        value = unpack("<h", data)[0]
        if self._current_scale:
            value = value * self._current_scale
        return float(value) * 1e-3  # convert to A


    def temperature(self) -> float:
        """Read the battery temperature with sign.

        Note: Temperature selection bit [TEMPS] in Pack Configuration must be set to 1 (defualt).

        Returns:
            float: The battery temperature in Celsius.
        """

        data = self._read(0x0C, 2)  # reads in 0.1 K (unsigned)
        kelvin = unpack("<H", data)[0] * 1e-1  # convert to K
        celsius = kelvin - KELVIN_ZERO_DEGC  # convert to °C (with sign)
        return celsius


    def read_serial_number(self) -> int:
        """Get the serial number of the battery.

        Returns:
            int: The serial number.
        """

        data = self._read(0x28, 2)
        value = unpack("<H", data)[0]
        return value


    def read_charge_voltage(self) -> float:
        """Get the charge voltage of the battery.

        Returns:
            float: The charge voltage in Volts.
        """

        data = self._read(0x30, 2)  # reads in mV
        value = unpack("<H", data)[0]
        return float(value) * 1e-3  # convert to V


    def read_charge_current(self) -> float:
        """Get the charge current of the battery.

        Returns:
            float: The charge current in Ampere.
        """

        data = self._read(0x32, 2)  # reads in mA
        value = unpack("<H", data)[0]
        return float(value) * 1e-3  # convert to A


    def read_design_capacity(self) -> float:
        """Get the design capacity of the battery.

        Returns:
            float: The design capacity in Ah.
        """

        data = self._read(0x3C, 2)  # reads in mAh
        value = unpack("<H", data)[0]
        if self._current_scale:
            value = value * self._current_scale
        return float(value) * 1e-3  # convert to Ah


    def read_pack_configuration(self) -> int:
        """Get the pack configuration of the battery.

        Returns:
            int: The pack configuration value.
        """

        data = self._read(0x3A, 2)
        value = unpack("<H", data)[0]

        return value


    def read_available_energy(self) -> float:
        """Get the available energy of the battery.

        Returns:
            float: The available energy in Wh.
        """

        data = self._read(0x24, 2)  # reads in mWh
        value = unpack("<H", data)[0]
        if self._energy_scale:
            value = value * self._energy_scale
        return float(value) * 1e-3  # convert to Wh


    def read_average_power(self) -> float:
        """Get the average power of the battery.

        Returns:
            float: The average power in Watts.
        """

        data = self._read(0x26, 2)  # reads in cW with sign
        value = unpack("<h", data)[0]
        if self._energy_scale and self._current_scale:
            value = value * self._energy_scale * self._current_scale
        return float(value) * 1e-2  # convert to W



    def read_average_time_to_empty(self) -> float:
        """Get the average time to empty of the battery.

        Returns:
            float: The average time to empty in hours.
        """

        data = self._read(0x18, 2)  # reads in minutes
        value = unpack("<H", data)[0]
        return float(value) / 60  # convert to h


    def read_average_time_to_full(self) -> float:
        """Get the average time to full of the battery.

        Returns:
            float: The average time to full in hours.
        """

        data = self._read(0x1A, 2)  # reads in minutes
        value = unpack("<H", data)[0]
        return float(value) / 60  # convert to h


    def read_internal_temperature(self) -> float:
        """Get the internal temperature of the battery.

        Returns:
            float: The internal temperature in Celsius.
        """

        data = self._read(0x2A, 2)  # reads in 0.1 K with sign
        kelvin = unpack("<H", data)[0] * 1e-1  # convert to K
        celsius = kelvin - KELVIN_ZERO_DEGC  # convert to °C
        return celsius


    def read_cycle_count(self) -> int:
        """Get the cycle count of the battery.

        Returns:
            int: The cycle count.
        """

        data = self._read(0x2C, 2)
        value = unpack("<H", data)[0]
        return int(value)


    def read_soh(self) -> float:
        """Get the state of health (SOH) of the battery.

        Returns:
            float: The state of health in percent.
        """

        data = self._read(0x2E, 2)  # reads in percent
        value = unpack("<H", data)[0]
        return float(value)  # already in %


    def read_soc(self) -> float:
        """Get the state of charge (SOC) of the battery.

        Returns:
            float: The state of charge in percent.
        """

        data = self._read(0x02, 1)  # reads in percent
        value = unpack("<B", data)[0]
        return float(value)  # already in %


    def read_max_error(self) -> float:
        """Get the maximum error of the battery.

        Returns:
            float: The maximum error in percent.
        """

        data = self._read(0x03, 1)  # reads in percent
        value = unpack("<B", data)[0]
        return float(value)  # already in %

    #----------------------------------------------------------------------------------------------

    def _decode_control_status(self, buf: bytearray| bytes, hexi: bool | str | None) -> OrderedDict:
        os = unpack("<H", buf)[0]  # word expected
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "RSVD1": ((os>>15) & 1),   # Reserved
            "FAS": ((os>>14) & 1),     # Status bit that indicates the BQ34Z100-R2 is in FULL ACCESS SEALED state. Active when set.
            "SS": ((os>>13) & 1),      # Status bit that indicates the BQ34Z100-R2 is in the SEALED State. Active when set.
            "CALEN": ((os>>12) & 1),   # Status bit that indicates the BQ34Z100-R2 calibration function is active. True when set. Default is 0.
            "CCA": ((os>>11) & 1),     # Status bit that indicates the BQ34Z100-R2 Coulomb Counter Calibration routine is active. Active when set.
            "BCA": ((os>>10) & 1),     # Status bit that indicates the BQ34Z100-R2 Board Calibration routine is active. Active when set.
            "CSV": ((os>>9) & 1),      # Status bit that indicates a valid data flash checksum has been generated. Active when set.
            "RSVD2": ((os>>8) & 1),    # Reserved
            "RSVD3": ((os>>7) & 1),    # Reserved
            "RSVD4": ((os>>6) & 1),    # Reserved
            "FULLSLEEP": ((os>>5) & 1), # Status bit that indicates the BQ34Z100-R2 is in FULL SLEEP mode. True when set. The state can only be detected by monitoring the power used by the BQ34Z100-R2 because any communication will automatically clear it.
            "SLEEP": ((os>>4) & 1),    # Status bit that indicates the BQ34Z100-R2 is in SLEEP mode. True when set.
            "LDMD": ((os>>3) & 1),     # Status bit that indicates the BQ34Z100-R2 Impedance Track algorithm using constant-power mode. True when set. Default is 0 (CONSTANT CURRENT mode).
            "RUP_DIS": ((os>>2) & 1),  # Status bit that indicates the BQ34Z100-R2 Ra table updates are disabled. True when set.
            "VOK": ((os>>1) & 1),      # Status bit that indicates cell voltages are OK for Qmax updates. True when set.
            "QEN": ((os>>0) & 1),      # Status bit that indicates the BQ34Z100-R2 Qmax updates are enabled. True when set.
        })


    def read_control_status(self, hexi: bool | str | None = None) -> int:
        """Get the status register.

        Returns:
            int: The status register value.
        """

        _, buf = self._read_control(0x0000)
        # convert to bitflags field
        self._control_status = self._decode_control_status(buf, hexi)
        return self._control_status


    #----------------------------------------------------------------------------------------------


    def _decode_flags_a(self, buf: bytearray| bytes, hexi: bool | str | None) -> OrderedDict:
        os = unpack("<H", buf)[0]  # word expected
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "OTC": ((os>>15) & 1),      # Overtemperature in Charge condition is detected. True when set
            "OTD": ((os>>14) & 1),      # Overtemperature in Discharge condition is detected. True when set
            "BATHI": ((os>>13) & 1),    # Battery High bit that indicates a high battery voltage condition. Refer to the data flash Cell BH parameters for threshold settings. True when set
            "BATLOW": ((os>>12) & 1),   # Battery Low bit that indicates a low battery voltage condition. Refer to the data flash Cell BL parameters for threshold settings. True when set
            "CHG_INH": ((os>>11) & 1),  # Charge Inhibit: unable to begin charging. Refer to the data flash [Charge Inhibit Temp Low, Charge Inhibit Temp High] parameters for threshold settings. True when set
            "XCHG": ((os>>10) & 1), # Charging not allowed.
            "FC": ((os>>9) & 1),    # (Fast) charging allowed. True when set
            "CHG": ((os>>8) & 1),   # Instruction Flash Checksum Failure
            "RESET": ((os>>7) & 1), # Set when OCV Reading is taken, cleared when not in RELAX or OCV Reading Not Taken.
            "RSVD1": ((os>>6) & 1), # Reserved
            "RSVD2": ((os>>5) & 1), # Reserved
            "CF": ((os>>4) & 1),    # Condition Flag indicates that the gauge needs to run through an update cycle to optimize accuracy.
            "RSVD3": ((os>>3) & 1), # Reserved
            "SOC1": ((os>>2) & 1),  # State-of-Charge Threshold 1 reached. True when set
            "SOCF": ((os>>1) & 1),  # State-of-Charge Threshold Final reached. True when set
            "DSG": ((os>>0) & 1),   # Discharging detected. True when set
        })

    def _decode_flags_b(self, buf: bytearray| bytes, hexi: bool | str | None) -> OrderedDict:
        os = unpack("<H", buf)[0]  # word expected
        return OrderedDict({
            "block": _maybe_hexlify(buf, hexi),
            # data come little endian
            "SOH": ((os>>15) & 1),     # StateOfHealth() calculation is active.
            "LIFE": ((os>>14) & 1),    # Indicates that LiFePO4 RELAX is enabled
            "FIRSTDOD": ((os>>13) & 1),  # Set when RELAX mode is entered and then cleared upon valid DOD measurement for QMAX update or RELAX exit.
            "RSVD1": ((os>>12) & 1),   # Battery Low bit that indicates a low battery voltage condition. Refer to the data flash Cell BL parameters for threshold settings. True when set
            "RSVD2": ((os>>11) & 1),   # Charge Inhibit: unable to begin charging. Refer to the data flash [Charge Inhibit Temp Low, Charge Inhibit Temp High] parameters for threshold settings. True when set
            "DODEOC": ((os>>10) & 1),  # DOD at End-of-Charge is updated.
            "DTRC": ((os>>9) & 1),     # Indicates RemainingCapacity() has been changed due to change in temperature.
            "RSVD3": ((os>>8) & 1),    # Instruction Flash Checksum Failure
            "RSVD_BYTE": (os & 0xFF),  # Reserved Byte
        })


    def read_flags(self, hexi: bool | str | None = None) -> Tuple[OrderedDict, OrderedDict]:
        """Get the flags registers.

        Returns:
            int: The flags register value.
        """

        buf = self._read(0x0e, 2)
        self._flags_a = self._decode_flags_a(buf, hexi)
        buf = self._read(0x12, 2)
        self._flags_b = self._decode_flags_b(buf, hexi)
        return _od2t(self.flags_a), _od2t(self.flags_b)


    #----------------------------------------------------------------------------------------------

    def read_version_information(self, as_hex_str: bool = True) -> OrderedDict:
        """Get the version information of the fuel gauge.

        Returns:
            Tuple[str]: The version information.
        """

        device_type, raw = self._read_control(0x0001)
        fw_version, raw = self._read_control(0x0002)
        hw_version, raw = self._read_control(0x0003)
        chem_id, raw = self._read_control(0x0008)
        df_version, raw = self._read_control(0x000C)
        chem_checksum, raw = self._read_control(0x0017)
        return OrderedDict({
            "device_type": f"0x{device_type:04X}" if as_hex_str else device_type,
            "fw_version": f"0x{fw_version:04X}" if as_hex_str else fw_version,
            "hw_version": f"0x{hw_version:04X}" if as_hex_str else hw_version,
            "chem_id": f"0x{chem_id:04X}" if as_hex_str else chem_id,
            "df_version": f"0x{df_version:04X}" if as_hex_str else df_version,
            "chem_checksum": f"0x{chem_checksum:04X}" if as_hex_str else chem_checksum,
        })



    def reset_fuel_gauge(self) -> bool:
        """Instructs the fuel gauge to perform a full reset. This command is only available when the fuel gauge is
        UNSEALED.

        Returns:
            bool: _description_
        """
        return self.write_control_command(0x0041)


    def enable_impedance_track(self) -> bool:
        """Forces the fuel gauge to begin the Impedance Track algorithm, sets Bit 2 of UpdateStatus and causes the
        [VOK] and [QEN] flags to be set in the CONTROL STATUS register. [VOK] is cleared if the voltages are not
        suitable for a Qmax update. Once set, [QEN] cannot be cleared. This command is only available when the fuel
        gauge is UNSEALED and is typically enabled at the last step of production after the system test is completed.

        Returns:
            bool: _description_
        """
        return self.write_control_command(0x0021)


    def enable_enter_and_exit_of_calibration_mode(self) -> bool:
        """Instructs the fuel gauge to enable entry and exit to CALIBRATION mode.

        Returns:
            bool: _description_
        """
        return self.write_control_command(0x002d)



    def enter_calibration(self) -> bool:
        """Enter CALIBRATION mode.

        Returns:
            bool: _description_
        """
        return self.write_control_command(0x0081)



    def exit_calibration(self) -> bool:
        """Exit CALIBRATION mode.

        Returns:
            bool: _description_
        """
        ok = self.write_control_command(0x0080)
        return self.enter_calibration() and ok


    def reset_device(self) -> bool:
        return self.write_control_command(0x0041, data=[0x00])


    def offset_cal(self) -> bool:
        """Reports internal CC offset in CALIBRATION mode.

        Returns:
            bool: _description_
        """
        ok = self.write_control_command(0x0082)
        return self.write_control_command(0x0000) and ok


    def calibrate_cc_offset(self) -> bool:
        """Instructs the fuel gauge to calibrate the coulomb counter offset.
        During calibration the [CCA] bit is set.

        Returns:
            bool: _description_
        """
        ok = self.write_control_command(0x000a)
        return self.write_control_command(0x0000) and ok


    def calibrate_board_offset(self) -> bool:
        """Instructs the fuel gauge to calibrate board offset.
        During board offset calibration the [BCA] bit is set.

        Returns:
            bool: _description_
        """
        ok = self.write_control_command(0x0009)
        return self.write_control_command(0x0000) and ok


    def cc_offset_save(self) -> bool:
        """Instructs the fuel gauge to save the coulomb counter offset after calibration.

        Returns:
            bool: _description_
        """
        if 0:
            ok = self.write_control_command(0x000b)
            return self.write_control_command(0x0000) and ok
        else:
            return self.write_control_command(0x000b)


    def read_df_version(self) -> int:
        version, raw = self._read_control(0x000c)
        return version


    def calc_static_chem_df_checksum(self) -> int:
        chk, raw = self._read_control(0x0017)
        return chk


    def wait_cca_clear(self) -> bool:
        n = 60*2
        while n:
            cs = self.read_control_status()
            if cs["CCA"] == 0:
                return True
            sleep(0.5)
            n -= 1
        return False



    def _flash_to_float_backup(z: int) -> float:
        """This is according to an example from TI.
        You should use our versions which transform the numbers into float according to IEEE754
        and do the conversion to 32bit bytes from there.

        Args:
            z (int): _description_

        Returns:
            float: _description_
        """
        exponent = (z >> 24) - 128 - 24  # both numbers are from ??? TI
        print(hex(exponent))
        mantissa = z & 0xFFFFFF
        sign = -1 if (z & 0x800000) != 0 else 1
        mantissa = mantissa | 0x800000  # set back the hidden 1 of mantissa
        result = sign * mantissa * 2**exponent
        return result


    def _flash_f4_to_float(self, z: int) -> float:
        """
        TI stores the EXP in a different way:
        b31..b24 = EXP + 2
        b24 = sign bit
        b23..b0 = mantissa
        To convert to IEEE754 we need to subtract 2 from EXP and move the sign bit to b31

        Args:
            z (int): _description_

        Returns:
            float: _description_
        """

        n = (z & 0x7FFFFF) | (((((z >> 24) & 0xFF) - 2) & 0xFF) << 23) | ((z & 0x00800000) << 8)
        b = pack("<L", n)
        f = unpack("<f", b)
        print(hexlify(b))
        print(f)
        return f[0]


    def _float_to_flash_f4(self, value: float) -> int:
        b = pack("<f", value)
        n = unpack("<L", b)[0]
        z = (n & 0x7FFFFF) | ((((n >> 23) & 0xFF) + 2) << 24) | ((n & 0x80000000) >> 8)
        return z




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