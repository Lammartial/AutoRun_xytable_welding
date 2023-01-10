""" Smart Battery implementation.
    Data according SMBus Spec v2.0 with Smart Battery Data
    Specialized data can be found in IcSpecData section below.
"""
__author__ = "Markus Ruth"
__version__ = "0.5.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

import errno
from time import sleep, monotonic_ns
from binascii import hexlify
from struct import pack
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from rrc.battery_errors import BatteryError


# allowed command set for the battery
class Cmd:
    MANUFACTURER_ACCESS = 0x00
    REMAINING_CAPACITY_ALARM = (0x01)
    REMAINING_TIME_ALARM = (0x02)
    BATTERY_MODE = (0x03)
    AT_RATE = (0x04)
    AT_RATE_TIME_TO_FULL = (0x05)
    AT_RATE_TIME_TO_EMPTY = (0x06)
    AT_RATE_OK = (0x07)
    TEMPERATURE = (0x08)
    VOLTAGE = (0x09)
    CURRENT = (0x0A)
    AVERAGE_CURRENT = (0x0B)
    MAX_ERROR = (0x0C)
    RELATIVE_STATE_OF_CHARGE = (0x0D)
    ABSOLUTE_STATE_OF_CHARGE = (0x0E)
    REMAINING_CAPACITY = (0x0F)
    FULL_CHARGE_CAPACITY = (0x10)
    RUN_TIME_TO_EMPTY = (0x11)
    AVERAGE_TIME_TO_EMPTY = (0x12)
    AVERAGE_TIME_TO_FULL = (0x13)
    CHARGING_CURRENT = (0x14)
    CHARGING_VOLTAGE = (0x15)
    BATTERY_STATUS = (0x16)
    CYCLE_COUNT = (0x17)
    DESIGN_CAPACITY = (0x18)
    DESIGN_VOLTAGE = (0x19)
    SPECIFICATION_INFO = (0x1A)
    MANUFACTURE_DATE = (0x1B)
    SERIAL_NUMBER = (0x1C)
    MANUFACTURER_NAME = (0x20)
    DEVICE_NAME = (0x21)
    DEVICE_CHEMISTRY = (0x22)
    MANUFACTURER_DATA = (0x23)

    # TI related extensions
    AUTHENTICATE = (0x2F)

    CELL1_VOLTAGE = (0x3F)
    CELL2_VOLTAGE = (0x3E)
    CELL3_VOLTAGE = (0x3D)
    CELL4_VOLTAGE = (0x3C)

    MANUFACTURER_BLOCK_ACCESS = (0x44)

    OPERATION_STATUS = 0x54

    # RRC special extension
    SPEC_SOH = (0x4f00)


# -------------------------------------------------------------------------------------------
class SpecSOHData:
    def __init__(self, battery, command: int, value: int = None):
        self._battery = battery
        self._cmd = command
        self.read = value

    def update(self) -> bool:
        dsc = self._battery.design_capacity()[0]
        fcc = self._battery.full_charge_capacity()[0]
        if dsc is not None and fcc is not None:
            self.read = round((fcc / dsc) * 100, 1) if dsc != 0 else None
            return True
        return False

    @property
    def value(self) -> int:
        if self.read is None: self.update()
        return self.read


# Standard data representation classes
class WordData:
    def __init__(self, battery, command: int, value: int = None):
        self._battery = battery
        self._cmd = command
        self.read = value

    def update(self):
        v, ok = self._battery.readWordVerified(self._cmd)  # try to update the value
        # v, ok = self._battery.readWord(self._cmd) # try to update the value
        if ok: self.read = v  # update
        return ok

    @property
    def value(self) -> int:
        if self.read is None: self.update()
        # self.update() # always update!
        return self.read
    # has NO setter as we do not allow writing - only for special words, see below
    # @value.setter
    # def value(self, value):
    #    self.read = value
    # @value.deleter
    # def value(self):
    #    del self.read


class StringData:
    def __init__(self, battery, command: int, value: str | bytes | bytearray = None):
        self._battery = battery
        self._cmd = command
        self.read = value

    def update(self) -> bool:
        v, ok = self._battery.readStringVerified(self._cmd)  # try to update the value
        if ok: self.read = v  # update
        return ok

    @property
    def value(self) -> str | bytes | bytearray:
        if self.read is None: self.update()  # only update once as this is constant data
        return self.read


class BlockData:
    def __init__(self, battery, command: int, value: bytes | bytearray = None):
        self._battery = battery
        self._cmd = command
        self.read = value
        self.written = None

    def update(self) -> bool:
        v, ok = self._battery.readBlockVerified(self._cmd)  # try to update the value(s)
        if ok: self.read = v  # update
        return ok

    @property
    def value(self):
        self.update()  # always update!
        return self.read

    @value.setter
    def value(self, value: int | bytes | bytearray):
        if isinstance(value, int):  # we do a graceful convert from integer to bytes here
            if value > 0xFFFFFFFF:
                value = pack("<Q", value)  # unsigned long long, 8 bytes
            elif value > 0xFFFF:
                value = pack("<L", value)  # unsigned long, 4 bytes
            else:
                value = pack("<H", value)  # unsigned short, 2 bytes
        elif not isinstance(value, bytes) and not isinstance(value, bytearray):
            raise ValueError(
                "Write block-data accepts only integer, bytes or byte arrays. Given was {}".format(type(value)))
        else:
            pass
        ok = self._battery.writeBlock(self._cmd, value)  # NO verification!
        if ok: self.written = value


# -------------------------------------------------------------------------------------------
# These classes are for special commands.
# Some include writing but all have special data representations.

class BatteryStatus:
    def __init__(self, battery, command: int, value: int = None):
        self._battery = battery
        self._cmd = command
        self._set_v(value)

    def _set_v(self, v: int):
        self._v = v
        if v is None:
            self.error_code = \
                self.fully_discharged = \
                self.fully_charged = \
                self.discharging = \
                self.initialized = \
                self.remaining_time_alarm = \
                self.remaining_capacity_alarm = \
                self.terminate_discharge_alarm = \
                self.over_temperature_alarm = \
                self.terminate_charge_alarm = \
                self.overcharged_alarm = None
        else:
            self.error_code = (v & 0x0f)  # EC3, ... , EC0
            self.fully_discharged = (v >> 4) & 1  # FD
            self.fully_charged = (v >> 5) & 1  # FC
            self.discharging = (v >> 6) & 1  # DSG
            self.initialized = (v >> 7) & 1  # INIT
            self.remaining_time_alarm = (v >> 8) & 1  # RTA
            self.remaining_capacity_alarm = (v >> 9) & 1  # RCA
            self.terminate_discharge_alarm = (v >> 11) & 1  # TDA
            self.over_temperature_alarm = (v >> 12) & 1  # OTA
            self.terminate_charge_alarm = (v >> 14) & 1  # TCA
            self.overcharged_alarm = (v >> 15) & 1  # OCA

    @property
    def text(self) -> str:
        return "EC:{},FD:{},FC:{},DSG:{},INIT:{},RTA:{},RCA:{},TDA:{},OTA:{},TCA:{},OCA{}".format(
            self.error_code,
            self.fully_discharged,
            self.fully_charged,
            self.discharging,
            self.initialized,
            self.remaining_time_alarm,
            self.remaining_capacity_alarm,
            self.terminate_discharge_alarm,
            self.over_temperature_alarm,
            self.terminate_charge_alarm,
            self.overcharged_alarm)

    @property
    def error(self) -> tuple(int, str):
        txt = ['OK', 'Busy', 'Reserved Command', 'Unsupported Command', 'AccessDenied',
               'Overflow/Underflow', 'BadSize', 'UnknownError']
        ec = self._v & 0x0f
        if ec > 7:
            return 'UndefinedError'
        else:
            return ec, txt[ec]

    def update(self) -> bool:
        v, ok = self._battery.readWordVerified(self._cmd)  # try to update the value
        if ok: self._set_v(v)  # update
        return ok

    @property
    def value(self) -> int:
        if self._v is None: self.update()
        return self._v

    @value.setter
    def value(self, value: int):
        self._set_v(value)


# -------------------------------------------------------------------------------------------
class BatteryMode:
    def __init__(self, battery, command: int, value: int = None):
        self._battery = battery
        self._cmd = command
        self._set_v(value)

    def _set_v(self, value):
        self._v = value
        if self._v is None:
            self.has_internal_charge_controller = \
                self.has_primary_battery_support = \
                self.conditioning_cycle_requested = \
                self.charge_controller_enabled = \
                self.primary_battery = \
                self.no_alarm_broadcasting = \
                self.no_charger_mode_broadcasting = \
                self.capacity_in_10milliwatts_not_milliamps = None
        else:
            self.has_internal_charge_controller = (self._v >> 0) & 1
            self.has_primary_battery_support = (self._v >> 1) & 1
            self.conditioning_cycle_requested = (self._v >> 7) & 1
            self.charge_controller_enabled = (self._v >> 8) & 1
            self.primary_battery = (self._v >> 9) & 1
            self.no_alarm_broadcasting = (self._v >> 13) & 1
            self.no_charger_mode_broadcasting = (self._v >> 14) & 1
            self.capacity_in_10milliwatts_not_milliamps = (self._v >> 15) & 1

    def update(self):
        v, ok = self._battery.readWordVerified(self._cmd)  # try to update the value
        if ok: self._set_v(v)  # update
        return ok

    @property
    def value(self):
        if self._v is None: self.update()
        return self._v

    @value.setter
    def value(self, value):
        self._set_v(value)
        #
        # TODO: WRITE BIT FUNCTION
        #


# -------------------------------------------------------------------------------------------
class BatterySpecification:
    def __init__(self, battery, command: int, value: int = None):
        self._battery = battery
        self._cmd = command
        self._set_v(value)

    def _set_v(self, value):
        self._v = value
        if self._v is None:
            self.revision = \
                self.version = \
                self.v_scale = \
                self.ip_scale = None
        else:
            self.revision = (self._v >> 0) & 0x0f
            self.version = (self._v >> 4) & 0x0f
            self.v_scale = (self._v >> 8) & 0x0f
            self.ip_scale = (self._v >> 12) & 0x0f

    def update(self):
        v, ok = self._battery.readWordVerified(self._cmd)  # try to update the value
        if ok: self._set_v(v)  # update
        return ok

    @property
    def value(self):
        if self._v is None: self.update()
        return self._v


# -------------------------------------------------------------------------------------------
class ManufacturerAccess:
    def __init__(self, battery, command: int , value: int = None):
        self._battery = battery
        self._cmd = command
        self.read = value
        self.written = None

    def update(self):
        v, ok = self._battery.readWord(self._cmd)  # includes use of multiple read+compare strategy
        if ok: self.read = v  # update
        return ok

    @property
    def value(self):
        self.update()  # always update!
        return self.read

    @value.setter
    def value(self, value):
        ok = self._battery.writeWord(self._cmd, value)  # single write, NO read-back verification as
        # battery provides different data to read
        # after writing at this address.
        if ok: self.written = value


# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

class Battery:
    ds = {}

    def __init__(self, smbus: BusMaster, slvAddress: int = 0x0b, pec: bool = False):
        self.bus = smbus
        self.address = int(slvAddress)
        self.pec = bool(pec)
        _bat = self
        # dataset special commands
        self.ds[Cmd.BATTERY_STATUS] = BatteryStatus(_bat, Cmd.BATTERY_STATUS)
        self.ds[Cmd.BATTERY_MODE] = BatteryMode(_bat, Cmd.BATTERY_MODE)
        self.ds[Cmd.SPECIFICATION_INFO] = BatterySpecification(_bat, Cmd.SPECIFICATION_INFO)
        self.ds[Cmd.MANUFACTURER_ACCESS] = ManufacturerAccess(_bat, Cmd.MANUFACTURER_ACCESS)
        # fill the dataset with the basic command
        for c in [
            Cmd.REMAINING_CAPACITY_ALARM,
            Cmd.REMAINING_TIME_ALARM,
            Cmd.AT_RATE,
            Cmd.AT_RATE_TIME_TO_FULL,
            Cmd.AT_RATE_TIME_TO_EMPTY,
            Cmd.AT_RATE_OK,
            Cmd.TEMPERATURE,
            Cmd.VOLTAGE,
            Cmd.CURRENT,
            Cmd.AVERAGE_CURRENT,
            Cmd.MAX_ERROR,
            Cmd.RELATIVE_STATE_OF_CHARGE,
            Cmd.ABSOLUTE_STATE_OF_CHARGE,
            Cmd.REMAINING_CAPACITY,
            Cmd.FULL_CHARGE_CAPACITY,
            Cmd.RUN_TIME_TO_EMPTY,
            Cmd.AVERAGE_TIME_TO_EMPTY,
            Cmd.AVERAGE_TIME_TO_FULL,
            Cmd.CHARGING_CURRENT,
            Cmd.CHARGING_VOLTAGE,
            Cmd.CYCLE_COUNT,
            Cmd.DESIGN_CAPACITY,
            Cmd.DESIGN_VOLTAGE,
            Cmd.MANUFACTURE_DATE,
            Cmd.SERIAL_NUMBER,

            Cmd.CELL1_VOLTAGE,
            Cmd.CELL2_VOLTAGE,
            Cmd.CELL3_VOLTAGE,
            Cmd.CELL4_VOLTAGE,

            Cmd.OPERATION_STATUS,

        ]: self.ds[c] = WordData(_bat, c)
        for c in [
            Cmd.MANUFACTURER_NAME,
            Cmd.DEVICE_NAME,
            Cmd.DEVICE_CHEMISTRY
        ]: self.ds[c] = StringData(_bat, c)
        for c in [
            Cmd.MANUFACTURER_DATA,
            Cmd.AUTHENTICATE,
            Cmd.MANUFACTURER_BLOCK_ACCESS
        ]: self.ds[c] = BlockData(_bat, c)

        # specific special commands, e.g. self calcultaed SOH etc.
        self.ds[Cmd.SPEC_SOH] = SpecSOHData(_bat, Cmd.SPEC_SOH)

        # following are members to control a step-by-step times read of information from battery
        self._tcycidx = -1  # convinience getter index
        self._tupidx = -1  # execution index
        self.table = None

    # --------------------------------------------
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

    # --------------------------------------------
    def isReady(self) -> bool:
        # return self.bus.isReady(self.address)
        ok = False
        try:
            _, ok = self.bus.readWord(self.address, Cmd.BATTERY_MODE, self.pec)
        except OSError as ex:
            if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                # -> forward this exception
                raise ex
        return ok

    def waitForReady(self, timeout_ms: int = 250, invert: bool = False, throw: bool = False) -> bool:
        t0 = monotonic_ns()
        pause = int(timeout_ms * 100)  # = timeout_ms/10 * 1000
        while ((monotonic_ns() - t0) / 1000000) < timeout_ms:
            if not invert and self.isReady(): return True
            if invert and not self.isReady(): return True
            sleep(pause / 1000000)
        if throw: raise BatteryError("Timeout {}ms while waiting for battery ready.".format(timeout_ms))
        return False

    def autodetectPEC(self) -> bool:
        ok = False
        try:
            _, ok = self.bus.readWord(self.address, Cmd.BATTERY_MODE, True)
        except OSError as ex:
            # print("PEC:", ex)
            pass
        self.pec = ok  # set use of PEC for further communication
        return self.pec

    # pylint: disable=C0116,C0321
    # ------ SMBus-Protocols----------
    # convenience functions to call BusMaster
    def writeWordVerified(self, cmd, w) -> bool:
        return self.bus.vWriteWord(self.address, cmd, w, self.pec)  # VERIFIED by read-back!!!

    def writeWord(self, cmd, w) -> bool:
        return self.bus.writeWord(self.address, cmd, w, self.pec)  # NO read-back (verify)

    def readWordVerified(self, cmd):
        return self.bus.vReadWord(self.address, cmd, self.pec)  # VERIFIED by read-back!!!

    def readWord(self, cmd):
        return self.bus.readWord(self.address, cmd, self.pec)  # NO verification

    def writeBytesVerified(self, cmd, buffer) -> bool:
        return self.bus.vWriteBytes(self.address, cmd, buffer, self.pec)  # VERIFIED by read-back!!!

    def writeBytes(self, cmd, buffer) -> bool:
        return self.bus.writeBytes(self.address, cmd, buffer, self.pec)  # NO read-back (verify)

    def readBytesVerified(self, cmd, count):
        return self.bus.vReadBytes(self.address, cmd, count, self.pec)

    def readBytes(self, cmd, count):
        return self.bus.readBytes(self.address, cmd, count, self.pec)  # NO read-back (verify)

    def readStringVerified(self, cmd):
        return self.bus.vReadString(self.address, cmd, self.pec)

    def writeBlockVerified(self, cmd, buffer) -> bool:
        return self.bus.vWriteBytes(self.address, cmd, bytearray(bytes([len(buffer)]) + bytes(buffer)),
                                    self.pec)  # VERIFIED by read-back!!!

    def writeBlock(self, cmd, buffer) -> bool:
        return self.bus.writeBytes(self.address, cmd, bytearray(bytes([len(buffer)]) + bytes(buffer)),
                                   self.pec)  # NO read-back (verify)

    def readBlockVerified(self, cmd):
        return self.bus.vReadBlock(self.address, cmd, self.pec)

    def readBlock(self, cmd, byte_count=-1):
        return self.bus.readBlock(self.address, cmd, self.pec, byte_count)  # NO read-back (verify)

    # ------ SMBus-Protocols----------

    @property
    def manufacturer_access(self):
        return self.ds[Cmd.MANUFACTURER_ACCESS].value  # the data getter executes the bus command

    @manufacturer_access.setter
    def manufacturer_access(self, value):
        self.ds[Cmd.MANUFACTURER_ACCESS].value = value  # the data setter executes the bus command
        # NOTE: signature of setter needs to be (self,value) no other name for "value" is accepted !!

    @property
    def manufacturer_data(self):
        return self.ds[Cmd.MANUFACTURER_DATA].value  # the data getter executes the bus command

    @property
    def manufacturer_block_access(self):
        return self.ds[Cmd.MANUFACTURER_BLOCK_ACCESS].value  # the data getter executes the bus command

    @manufacturer_block_access.setter
    def manufacturer_block_access(self, value):
        self.ds[Cmd.MANUFACTURER_BLOCK_ACCESS].value = value  # the data setter executes the bus command

    @property
    def authenticate(self):
        return self.ds[Cmd.AUTHENTICATE].value  # the data getter executes the bus command

    @authenticate.setter
    def authenticate(self, value):
        self.ds[Cmd.AUTHENTICATE].value = value  # the data setter executes the bus command

    # --------------------------------------------
    # all following function return quadruples
    def manufacturer_access_func(self):
        c = self.ds[Cmd.MANUFACTURER_ACCESS];      return "{:04X}".format(c.value), "", "Manufacturer Access", c

    def manufacturer_data_func(self):
        c = self.ds[Cmd.MANUFACTURER_DATA];        return c.value, "", "Manufacturer Data", c

    def battery_status(self):
        c = self.ds[Cmd.BATTERY_STATUS];           return "{:04X}".format(c.value), "", "Status", c

    def status(self):
        return self.battery_status()  # trampoline

    def battery_mode(self):
        c = self.ds[Cmd.BATTERY_MODE];             return "{:04X}".format(c.value), "", "Mode", c

    def mode(self):
        return self.battery_mode()  # trampoline

    def specification_info(self):
        c = self.ds[Cmd.SPECIFICATION_INFO];       return "{:04X}".format(c.value), "", "Specification Info", c

    def specification(self):
        return self.specification_info()  # trampoline

    def remaining_capacity_alarm(self):
        c = self.ds[Cmd.REMAINING_CAPACITY_ALARM]; return c.value * 1e-3, "Ah", "Rem.Cap.Alarm", c

    def remaining_time_alarm(self):
        c = self.ds[Cmd.REMAINING_TIME_ALARM];     return c.value, "min", "Rem.Cap.Alarm", c

    def at_rate(self):
        c = self.ds[Cmd.AT_RATE];                  return c.value * 1e-3, "A", "At rate", c

    def at_rate_ok(self):
        c = self.ds[Cmd.AT_RATE_OK];               return c.value, "", "At rate ok", c

    def at_rate_time_to_full(self):
        c = self.ds[Cmd.AT_RATE_TIME_TO_FULL];     return c.value, "min", "At rate full", c

    def at_rate_time_to_empty(self):
        c = self.ds[Cmd.AT_RATE_TIME_TO_EMPTY];    return c.value, "min", "At rate empty", c

    def temperature(self):
        c = self.ds[Cmd.TEMPERATURE];              return c.value * 1e-2, "°C", "Temperature", c

    def temperature_kelvin(self):
        c = self.ds[Cmd.TEMPERATURE];              return c.value * 1e-2 + KELVIN_ZERO_DEGC, "K", "Temperature", c

    def voltage(self):
        c = self.ds[Cmd.VOLTAGE];                  return c.value * 1e-3, "V", "Voltage", c

    def current(self):
        c = self.ds[Cmd.CURRENT];                  return c.value * 1e-3, "A", "Current", c

    def average_current(self):
        c = self.ds[Cmd.AVERAGE_CURRENT];          return c.value * 1e-3, "A", "Avg.Current", c

    def max_error(self):
        c = self.ds[Cmd.MAX_ERROR];                return c.value, "%", "Max Error", c

    def relative_state_of_charge(self):
        c = self.ds[Cmd.RELATIVE_STATE_OF_CHARGE]; return c.value, "%", "SOC", c

    def soc(self):
        return self.relative_state_of_charge()  # trampoline

    def absolute_state_of_charge(self):
        c = self.ds[Cmd.ABSOLUTE_STATE_OF_CHARGE]; return c.value, "%", "Absolute SOC", c

    def remaining_capacity(self):
        c = self.ds[Cmd.REMAINING_CAPACITY];       return c.value * 1e-3, "Ah", "Remaining Capacity", c

    def capacity(self):
        return self.remaining_capacity()  # trampoline

    def full_charge_capacity(self):
        c = self.ds[Cmd.FULL_CHARGE_CAPACITY];     return c.value * 1e-3, "Ah", "Full Chg.Capacity", c

    def run_time_to_empty(self):
        c = self.ds[Cmd.RUN_TIME_TO_EMPTY];        return c.value, "min", "Time to empty", c

    def average_time_to_empty(self):
        c = self.ds[Cmd.AVERAGE_TIME_TO_EMPTY];    return c.value, "min", "Avg.Time empty", c

    def average_time_to_full(self):
        c = self.ds[Cmd.AVERAGE_TIME_TO_FULL];     return c.value, "min", "Avg.Time full", c

    def charging_current(self):
        c = self.ds[Cmd.CHARGING_CURRENT];         return c.value * 1e-3, "A", "Charge Current", c

    def charging_voltage(self):
        c = self.ds[Cmd.CHARGING_VOLTAGE];         return c.value * 1e-3, "V", "Charge Voltage", c

    def cycle_count(self):
        c = self.ds[Cmd.CYCLE_COUNT];              return c.value, "", "Cycles", c

    def cycles(self):
        return self.cycle_count()  # trampoline

    # constant stuff starts here
    def design_capacity(self):
        c = self.ds[Cmd.DESIGN_CAPACITY];          return c.value * 1e-3, "Ah", "Design Capacity", c

    def design_voltage(self):
        c = self.ds[Cmd.DESIGN_VOLTAGE];           return c.value * 1e-3, "V", "Design Voltage", c

    def manufacture_date(self):
        c = self.ds[Cmd.MANUFACTURE_DATE]
        val = c.value
        day = ((val >> 0) & 0x1f)
        month = ((val >> 5) & 0x0f)
        year = (1980 + ((val >> 9) & 0x7f))
        return "{:d}-{:02d}-{:02d}".format(year, month, day), "", "Manufacturing Date", c

    def serial_number(self):
        c = self.ds[Cmd.SERIAL_NUMBER];         return c.value, "", "S/N", c

    def manufacturer_name(self):
        c = self.ds[Cmd.MANUFACTURER_NAME];     return c.value, "", "Manufacturer", c

    def device_name(self):
        c = self.ds[Cmd.DEVICE_NAME];           return c.value, "", "Name", c

    def device_chemistry(self):
        c = self.ds[Cmd.DEVICE_CHEMISTRY];      return c.value, "", "Chemistry", c

    def soh(self):
        c = self.ds[Cmd.SPEC_SOH];              return c.value, "%", "SOH", c

    def cell1_voltage(self):
        c = self.ds[Cmd.CELL1_VOLTAGE];         return c.value * 1e-3, "V", "Cell 1 Volt.", c

    def cell2_voltage(self):
        c = self.ds[Cmd.CELL2_VOLTAGE];         return c.value * 1e-3, "V", "Cell 2 Volt.", c

    def cell3_voltage(self):
        c = self.ds[Cmd.CELL3_VOLTAGE];         return c.value * 1e-3, "V", "Cell 3 Volt.", c

    def cell4_voltage(self):
        c = self.ds[Cmd.CELL4_VOLTAGE];         return c.value * 1e-3, "V", "Cell 4 Volt.", c

    def operation_status(self):
        return int.from_bytes((self.read_mac_data(0x0054)[:2]), "little")

    def full_access_battery(self):
        UNSEAL_WORD1 = 0xFAC3
        UNSEAL_WORD2 = 0x8D21
        FA_WORD1 = 0x2CE4
        FA_WORD2 = 0x63DB
        self.writeWord(Cmd.MANUFACTURER_ACCESS, UNSEAL_WORD1)
        self.writeWord(Cmd.MANUFACTURER_ACCESS, UNSEAL_WORD2)
        self.writeWord(Cmd.MANUFACTURER_ACCESS, FA_WORD1)
        self.writeWord(Cmd.MANUFACTURER_ACCESS, FA_WORD2)

    def seal_mode(self) -> int:
        return (self.operation_status() & 0x0300) >> 8

    def is_full_access(self) -> bool:
        return self.seal_mode() == 1

    def is_unsealed(self) -> bool:
        return self.seal_mode() == 2

    def is_sealed(self) -> bool:
        return self.seal_mode() == 3

    def seal_battery(self):
        self.writeBlock(Cmd.MANUFACTURER_BLOCK_ACCESS, bytearray([0x30, 0x00]))

    def read_mac_data(self, cmd: int):
        self.writeBlock(Cmd.MANUFACTURER_BLOCK_ACCESS, cmd.to_bytes(2, "little"))
        result = self.readBlock(Cmd.MANUFACTURER_BLOCK_ACCESS)
        if result[1]:
            return result[0][2:]

    # pylint: enable=C0116,C0321

    # --------------------------------------------
    # generic read access
    # MUST be in the list of supported commands!
    def value(self, cmd):
        if cmd not in self.ds: raise ValueError
        return self.ds[cmd].value

    # --------------------------------------------
    # functions intended for processing in a loop
    # (table driven command set)

    def updateNextCmd(self, ignore_time=False):
        start = self._tupidx
        i = self._tupidx
        v = None
        while v is None:
            i += 1
            if (i >= len(self.table)) or (i < 0): i = 0  # wrap around
            if i == start: break  # sorry, we limit to one full table cycle
            ts = self.table[i][3]
            if ts is not None:
                # check deadline for refresh
                refresh = self.table[i][2]
                if refresh == 0: continue  # only ONCE to be read, find next command
                if not ignore_time:
                    deadline = ts + refresh
                    if (deadline - monotonic_ns() / 1000000) > 0: continue  # not yet to refresh find next command
            # command needs update
            cmd = self.table[i][0]
            try:
                v, _, _, o = cmd()  # need to access the object only
                o.update()  # force to read the battery data
                v = o.value  # get the updated value
                self.table[i][3] = monotonic_ns() / 1000000  # set timestamp of read
            except OSError:
                if v is None: raise  # was not able to read
                pass
            except Exception:
                raise
            s = self.table[i][1]  # after that we might have to wait a bit freeing the bus
            if s > 0: sleep(s / 1000000)
        self._tupidx = i
        return v, i

    def readAllCmdTable(self, ignore_time=False):
        for _ in self.table:
            try:
                self.updateNextCmd(ignore_time=ignore_time)
            except Exception as ex:
                # we add the function name to the exeption
                # way 1: add as string
                if not ex.args:
                    ex.args = ('',)
                ex.args = ex.args + "While read cmd " + self.table[self._tupidx].__name__
                ## way 2 add as new attribute
                # ex.trigger_function = self.table[self._tupidx].__name__
                raise ex

    def isAllCmdTableRead(self):
        r = True
        for i in range(0, len(self.table)): r = r & (self.table[i][3] is not None)
        return r

    def prevCmd(self):
        self._tcycidx -= 1
        if (self._tcycidx >= len(self.table)) or (self._tcycidx < 0):
            self._tcycidx = len(self.table) - 1
        return self.table[self._tcycidx][0]  # return only the data object

    def nextCmd(self):
        self._tcycidx += 1
        if (self._tcycidx >= len(self.table)) or (self._tcycidx < 0):
            self._tcycidx = 0
        return self.table[self._tcycidx][0]  # return only the data object

    def setupCmdTable(self):
        self._tcycidx = -1  # convinience getter index
        self._tupidx = -1  # execution index
        self.table = [  # MAKE SURE THAT ALL COMMANDS IN TABLE RETURN QUADRUPLES !
            # command                sleep(us), refresh(ms), lastread_timestamp
            [self.device_name, 50, 0, None],
            [self.voltage, 200, 1000, None],
            [self.soc, 200, 1000, None],
            [self.soh, 200, 1000, None],
            [self.capacity, 200, 1000, None],
            [self.cycles, 200, 60000, None],
            [self.temperature, 200, 1000, None],
            [self.current, 200, 1000, None],
            [self.charging_voltage, 200, 1000, None],
            [self.charging_current, 200, 1000, None],
            [self.serial_number, 200, 0, None],
            [self.manufacture_date, 200, 0, None],
            [self.device_chemistry, 200, 0, None],
            [self.design_capacity, 200, 0, None],
        ]

    def setupAllStandardCmdTable(self):
        self._tcycidx = -1  # convinience getter index
        self._tupidx = -1  # execution index
        self.table = [  # MAKE SURE THAT ALL COMMANDS IN TABLE RETURN QUADRUPLES !
            # command                      sleep(us), refresh(ms), lastread_timestamp
            [self.manufacturer_access_func, 50, 5000, None],
            [self.remaining_capacity_alarm, 50, 1000, None],
            [self.remaining_time_alarm, 50, 1000, None],
            [self.battery_mode, 50, 1000, None],
            [self.at_rate, 50, 5000, None],
            [self.at_rate_time_to_full, 50, 5000, None],
            [self.at_rate_time_to_empty, 50, 5000, None],
            [self.at_rate_ok, 50, 5000, None],
            [self.temperature, 50, 1000, None],
            [self.voltage, 50, 1000, None],
            [self.current, 50, 1000, None],
            [self.average_current, 50, 1000, None],
            [self.max_error, 50, 1000, None],
            [self.relative_state_of_charge, 50, 1000, None],
            [self.absolute_state_of_charge, 50, 1000, None],
            [self.remaining_capacity, 50, 1000, None],
            [self.full_charge_capacity, 50, 1000, None],
            [self.capacity, 50, 1000, None],
            [self.soh, 50, 1000, None],
            [self.run_time_to_empty, 50, 60000, None],
            [self.average_time_to_empty, 50, 60000, None],
            [self.average_time_to_full, 50, 60000, None],
            [self.charging_current, 50, 1000, None],
            [self.charging_voltage, 50, 1000, None],
            [self.battery_status, 50, 1000, None],
            [self.cycle_count, 50, 60000, None],
            [self.design_capacity, 50, 0, None],
            [self.design_voltage, 50, 0, None],
            [self.specification_info, 50, 60000, None],
            [self.manufacture_date, 50, 0, None],
            [self.serial_number, 50, 0, None],
            [self.manufacturer_name, 50, 0, None],
            [self.device_name, 50, 0, None],
            [self.device_chemistry, 50, 0, None],
            [self.manufacturer_data_func, 50, 5000, None],
        ]

    # --------------------------------------------

    def _get_function_list(self):
        return [self.manufacturer_name, self.device_name, self.device_chemistry,
                self.serial_number, self.manufacture_date,
                self.voltage, self.capacity, self.cycles, self.battery_status]

    def getAsDict(self, refresh=False):
        d = {}
        funcList = [r[0] for r in self.table] if self.table is not None else self._get_function_list()
        for u in funcList:
            value, _, _, obj = u()
            if refresh:
                obj.update()
                value = obj.value
            if isinstance(value, bytearray):
                value = hexlify(value).decode()
            d[str(u.__name__)] = value
        return d

    def getTableAttributesAsEmptyDict(self):
        d = {}
        funcList = [r[0] for r in self.table] if self.table is not None else self._get_function_list()
        for u in funcList:
            d[str(u.__name__)] = None
        return d

    def serializeBeautified(self, refresh=False):
        txt = ""
        funcList = [r[0] for r in self.table] if self.table is not None else self._get_function_list()
        for u in funcList:
            value, units, name, obj = u()
            if refresh:
                obj.update()
                value = obj.value
            txt += str(name) + ": " + str(value) + " " + str(units) + "\n"

        return txt

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from ncd_eth_i2c_interface import I2CPort
    from smbus import BusMaster, BusMux_PCA9548A

    ncd = I2CPort("192.168.1.149", 2101)
    #print(ncd.i2c_bus_scan())

    bus = BusMaster(ncd)
    mux = BusMux_PCA9548A(ncd, address=0x77)
    mux.setChannel(1)

    bat = Battery(bus)

    # print(bat.voltage())
    print(bat.readBlock(6))

    print(bat.device_name()[0])
    # print(bat.voltage())
    # print(f"S: {bat.is_sealed()}")
    # print(f"FA: {bat.is_full_access()}")
    # bat.full_access_battery()
    # print(f"S: {bat.is_sealed()}")
    # print(f"FA: {bat.is_full_access()}")
    # bat.seal_battery()
    # print(f"S: {bat.is_sealed()}")
    # print(f"FA: {bat.is_full_access()}")
    # sleep(0.1)
    #
    # print(bat.is_sealed())


# END OF FILE
