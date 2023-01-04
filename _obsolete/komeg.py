from typing import Tuple
import struct
from datetime import datetime
from time import sleep
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from modbus.base import ModbusClient, log_modbus_version
from modbus.tools import filterString, createTimestamp, get_tz

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

#--------------------------------------------------------------------------------------------------

__version__ = VERSION

#--------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------
#
#  KOMEG 36L
#
#--------------------------------------------------------------------------------------------------
class Komeg36LTemperatureChamber(ModbusClient):
    """KOMEG 36 with TEMI360 controller.

    Need to be set to MODBUS-1 mode
    (Screen tip upper left and then upper right corner, set 0 for password number)

    Args:
        ModbusClient (_type_): _description_

    Returns:
        _type_: _description_
    """
    STATUS_MODE = 101  # 1 RUN, 2 HOLD ON/OFF, 3 SEGMENT STEP, 4 STOP, 5 HOLD OFF
    OPMODE = 104  # 0 PROG MODE , 1 FIX MODE
    PWRMODE = 105  # 0 STOP, 1 COLD, 2 HOT

    #  --- functions ---
    def start(self):
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        # set fix mode
        encoder.add_16bit_uint(1)
        self.client.write_registers(self.OPMODE, encoder.to_registers(), unit=self.unit_address)
        # command start
        encoder.reset()
        encoder.add_16bit_uint(1)
        self.client.write_registers(self.STATUS_MODE, encoder.to_registers(), unit=self.unit_address)

    def stop(self):
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        # set fix mode
        encoder.add_16bit_uint(1)
        self.client.write_registers(self.OPMODE, encoder.to_registers(), unit=self.unit_address)
        encoder.reset()
        # command stop
        encoder.add_16bit_uint(4)
        self.client.write_registers(self.STATUS_MODE, encoder.to_registers(), unit=self.unit_address)

    def read(self, addr, count) -> list:
        #d = {}
        regs = self.client.read_holding_registers(addr, count, unit=self.unit_address)
        #if any(regs.registers):  # print only if result contains at least on non-zero value
        _log.debug("READ @%s:%s", addr, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        d = []
        for i in range(0, count):
            d.append(decoder.decode_16bit_uint())
        return d

    def write(self, addr, value) -> list:
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_uint(value)
        _log.debug("WRITE %s", encoder.to_registers())
        self.client.write_registers(addr, encoder.to_registers(), unit=self.unit_address)

    def _decode_now_sts(self, w) -> dict:
        return {
            "value": w,
            "RESET": ((w>>0) & 0x01),
            "FIX_RUN": ((w>>1) & 0x01),
            "PROG_RUN": ((w>>2) & 0x01),
            "PROG_HOLD": ((w>>3) & 0x01),
            "PROG_WAIT": ((w>>4) & 0x01),
            "TEMP_AT": ((w>>5) & 0x01),
            "HUMI_AT": ((w>>6) & 0x01),
        }

    def read_cv(self) -> dict:
        d = {}
        regs = self.client.read_holding_registers(1, 16, unit=self.unit_address)
        #_log.debug(regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        d["temperature"] = decoder.decode_16bit_int() / 100
        d["temperature_setpoint"] = decoder.decode_16bit_int() / 100
        d["wet_npv"] = decoder.decode_16bit_int() / 100
        d["wet_nsp"] = decoder.decode_16bit_int() / 100
        d["humidity"] = decoder.decode_16bit_int() / 10
        d["humidity_setpoint"] = decoder.decode_16bit_int() / 10
        d["temp_mvout"] = decoder.decode_16bit_int()
        d["humi_mvout"] = decoder.decode_16bit_int()
        d["c_pidno"] = decoder.decode_16bit_uint()
        d["now_sts"] = decoder.decode_16bit_uint()
        d["_reserved_1"] = decoder.decode_16bit_uint() # 11
        d["is_sts"] = decoder.decode_16bit_uint()  # inner signal
        d["ts_sts"] = decoder.decode_16bit_uint()  # time signal
        d["al_sts"] = decoder.decode_16bit_uint()  # alarm status
        d["sys_err_sts"] = decoder.decode_16bit_uint()
        d["uo_sts"] = self._decode_now_sts(decoder.decode_16bit_uint())  # relay status

        _log.debug(d)
        return d

    def _decode_status_mode(self, w) -> dict:
        return {
            "value": w,
            "state": (["unknown", "RUN", "HOLD", "STEP", "STOP", "HOLD"][w]) if (w >= 0) and (w < 6) else "out_of_scope"
        }

    def _decode_op_mode(self, w: int) -> dict:
        return {
            "value": w,
            "state": (["PROG", "FIX"][w]) if (w >= 0) and (w < 2) else "out_of_scope"
        }

    def _decode_pwr_mode(self, w: int) -> dict:
        return {
            "value": w,
            "state": (["STOP", "COLD", "HOT"][w]) if (w >= 0) and (w < 3) else "out_of_scope"
        }

    def read_settings(self) -> dict:
        d = {}
        regs = self.client.read_holding_registers(101, 5, unit=self.unit_address)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        d["STATUS_MODE"] = self._decode_status_mode(decoder.decode_16bit_uint())
        d["_reserved_1"] = decoder.decode_16bit_uint() # 2
        d["_reserved_2"] = decoder.decode_16bit_uint() # 3
        d["OP_MODE"] = self._decode_op_mode(decoder.decode_16bit_uint())
        d["PWR_MODE"] = self._decode_pwr_mode(decoder.decode_16bit_uint())
        _log.debug(d)
        return d

    def set_program_no(self, pno):
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_uint(pno)
        self.client.write_registers(100, encoder.to_registers(), unit=self.unit_address)

    def set_temperature(self, celsius: float):
        """Set temperature fixrun setpoint (FIX_TEMP_SP) in °C

        Args:
            celsius (float): _description_
        """

        v = int(round(celsius * 100, 0))
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_int(v)
        _log.debug("SET FIX TEMP %s, %s", v, encoder.to_registers())
        self.client.write_registers(102, encoder.to_registers(), unit=self.unit_address)



    def set_humidity(self, percent: float):
        """Set humidity fixrun setpoint (FIX_HUMI_SP) in percent.

        Args:
            percent (float): _description_
        """

        # limit percent to [0; 100]
        v = 0 if percent < 0 else (100 if percent > 100 else percent)
        b = int(round(v * 10, 0))
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_int(b)
        _log.debug("SET FIX HUMI %s, %s", b, encoder.to_registers())
        self.client.write_registers(103, encoder.to_registers(), unit=self.unit_address)


    def read_temperature(self) -> float:
        """Read current temperature measurement and setpoint in °C.
        (TEMP_NPV, TEMP_NSP)

        Returns:
            float: °C

        """

        # read measurement (TEMP_NPV) and setpoint TEMP_NSP)
        regs = self.client.read_holding_registers(1, 2, unit=self.unit_address)
        #_log.debug("READ TEMP @%s:%s", 1, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        _pv = decoder.decode_16bit_int()/100
        _sp = decoder.decode_16bit_int()/100
        return _pv, _sp

    def read_wet_temperature(self) -> float:
        """Read current WET temperature measurement and WET setpoint in °C.
        (WET_NPV, WET_NSP)

        Returns:
            float: °C

        """

        # read measurement (WET_NPV) and setpoint WET_NSP)
        regs = self.client.read_holding_registers(3, 2, unit=self.unit_address)
        #_log.debug("READ TEMP @%s:%s", 1, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        _pv = decoder.decode_16bit_int()/100
        _sp = decoder.decode_16bit_int()/100
        return _pv, _sp

    def read_humidity(self) -> float:
        """
        Reads current humidity measurement and setpoint in %.
        (WET_NPV, WET_NSP)

        Returns:
            float: % relative air humidity
        """

        regs = self.client.read_holding_registers(5, 2, unit=self.unit_address)
        #_log.debug("READ TEMP @%s:%s", 3, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        _pv = decoder.decode_16bit_int()/10
        _sp = decoder.decode_16bit_int()/10
        return _pv, _sp


    def _reg_to_datetime(self, r) -> datetime:
        """Helper function to convert 5 registers to YYYY-MM-DD hh:mm (datetime

        Args:
            r (registers): five 16bit registers

        Returns:
            datetime: converted datetime object.
        """

        decoder = BinaryPayloadDecoder.fromRegisters(r, byteorder=self.byte_order, wordorder=self.word_order)
        _y = decoder.decode_16bit_uint()
        _m = decoder.decode_16bit_uint()
        _d = decoder.decode_16bit_uint()
        _h = decoder.decode_16bit_uint()
        _n = decoder.decode_16bit_uint()
        return datetime(_y,_m,_d, hour=_h, minute=_n)

    def read_datetime_now(self) -> datetime:
        regs = self.client.read_holding_registers(201, 5, unit=self.unit_address)
        return self._reg_to_datetime(regs.registers)

    def read_datetime_run(self) -> datetime:
        regs = self.client.read_holding_registers(206, 5, unit=self.unit_address)
        return self._reg_to_datetime(regs.registers)


    def set_datetime(self, dt: datetime) -> None:
        """Set the date and time of chamber to the given datetime object's YYYY-MM-DD hh:mm

        Args:
            dt (datetime): _description_
        """

        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_uint(dt.year)
        encoder.add_16bit_uint(dt.month)
        encoder.add_16bit_uint(dt.day)
        encoder.add_16bit_uint(dt.hour)
        encoder.add_16bit_uint(dt.minute)
        self.client.write_registers(211, encoder.to_registers(), unit=self.unit_address)

#--------------------------------------------------------------------------------------------------
#
#  KOMEG 225L
#
#--------------------------------------------------------------------------------------------------
class Komeg225LTemperatureChamber(ModbusClient):
    """KOMEG 225L with TT-5166 controller.

    Has fixed RS485 line settings: 38400,8,E,1
    Has fixed unit address: 0

    Args:
        ModbusClient (_type_): _description_

    Returns:
        _type_: _description_
    """

    def read(self, addr, count) -> list:
        #d = {}
        regs = self.client.read_holding_registers(addr, count, unit=self.unit_address)
        #if any(regs.registers):  # print only if result contains at least on non-zero value
        _log.debug("READ @%s:%s", addr, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        d = []
        for i in range(0, count):
            d.append(decoder.decode_16bit_uint())
        return d

    def write_coil(self, addr: int, value: int):
        self.client.write_coil(addr, value, unit=self.unit_address)

    def read_coil(self, addr: int) -> int:
        regs = self.client.read_coils(addr, count=1, unit=self.unit_address)
        return regs.bits

    #  --- functions ---
    def start(self, wait_for_execution: bool=False):
        self.client.write_coil(0, 1, unit=self.unit_address)
        if wait_for_execution:
            while self.client.read_coils(0, count=1, unit=self.unit_address).bits[0]:
                pass  # wait until coil bit is reset

    def stop(self, wait_for_execution: bool=False):
        self.client.write_coil(1, 1, unit=self.unit_address)
        if wait_for_execution:
            while self.client.read_coils(1, count=1, unit=self.unit_address).bits[0]:
                pass  # wait until coil bit is reset

    def auth(self, wait_for_execution: bool=False):
        self.client.write_coil(11, 1, unit=self.unit_address)
        if wait_for_execution:
            while self.client.read_coils(11, count=1, unit=self.unit_address).bits[0]:
                pass  # wait until coil bit is reset

    def read_status(self) -> dict:
        """Read current machine status

        Returns:
            dict: ...

        """

        regs = self.client.read_holding_registers(23, 5, unit=self.unit_address)
        _log.info("READ STATUS: %s", regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        return {
            "run_state": decoder.decode_16bit_int(),
            "reserved_1": decoder.decode_16bit_uint(),
            "program_state": [decoder.decode_8bit_uint(), decoder.decode_8bit_uint()],
            "reserved_2": decoder.decode_16bit_uint(),
            "fault_info": decoder.decode_16bit_uint(),
        }

    def set_temperature(self, celsius: float):
        """Set temperature fixrun setpoint (FIX_TEMP_SP) in °C

        Args:
            celsius (float): _description_
        """

        v = int(round(celsius * 10, 0))
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_int(v)
        _log.debug("SET FIX TEMP %s, %s", v, encoder.to_registers())
        self.client.write_registers(38, encoder.to_registers(), unit=self.unit_address)

    def read_temperature(self) -> Tuple[float, float, float]:
        """Read current temperature measurement and setpoint in °C.

        Returns:
            float: °C

        """

        # read measurement (TEMP_NPV) and setpoint TEMP_NSP)
        regs = self.client.read_holding_registers(0, 3, unit=self.unit_address)
        #_log.debug("READ TEMP @%s:%s", 1, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        _pv = decoder.decode_16bit_int()/100
        _sp = decoder.decode_16bit_int()/10
        _or = decoder.decode_16bit_int()/10
        return _pv, _sp, _or


    def set_humidity(self, percent: float):
        """Set humidity fixrun setpoint (FIX_HUMI_SP) in percent.

        Args:
            percent (float): _description_
        """

        # limit percent to [0; 100]
        v = 0 if percent < 0 else (100 if percent > 100 else percent)
        b = int(round(v * 100, 0))
        encoder = BinaryPayloadBuilder(byteorder=self.byte_order, wordorder=self.word_order)
        encoder.add_16bit_int(b)
        _log.debug("SET FIX HUMI %s, %s", b, encoder.to_registers())
        self.client.write_registers(39, encoder.to_registers(), unit=self.unit_address)

    def read_humidity(self) -> Tuple[float, float, float]:
        """
        Reads current humidity measurement and setpoint in %.
        (WET_NPV, WET_NSP)

        Returns:
            float: % relative air humidity
        """

        regs = self.client.read_holding_registers(3, 3, unit=self.unit_address)
        #_log.debug("READ TEMP @%s:%s", 3, regs.registers)
        decoder = BinaryPayloadDecoder.fromRegisters(regs.registers, byteorder=self.byte_order, wordorder=self.word_order)
        _pv = decoder.decode_16bit_int()/10
        _sp = decoder.decode_16bit_int()/10
        _or = decoder.decode_16bit_int()/10
        return _pv, _sp, _or



#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    log_modbus_version()
    tic = perf_counter()

    # ...

    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")

# END OF FILE