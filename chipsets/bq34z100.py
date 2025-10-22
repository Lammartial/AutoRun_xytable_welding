"""
BQ34Z100-R2 Wide Range Fuel Gauge with Impedance Track Technology.

"""

__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from typing import Tuple
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


    def write_control_command(self, w: int) -> bool:
        # write the subcommand to the control register (0x00/0x01)
        ok = True
        buf = pack("<H", w)
        if 0:
            for i in range(2):
                ok = ok and self.bus.writeBytes(self.address, 0x00 + i, buf[i:i+1], use_pec=self.pec)
            return ok
        else:
            return self.bus.writeBytes(self.address, 0x00, buf, use_pec=self.pec)


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


    def toggle_cal_enable(self) -> bool:
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
        return self.write_control_command(0x0041)


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