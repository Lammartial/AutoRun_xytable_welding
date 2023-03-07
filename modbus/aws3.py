from typing import Any, List
from struct import pack, unpack, unpack_from
from enum import Enum
from time import perf_counter
from pymodbus import version as modbus_version
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian, Defaults
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from rrc.modbus.base import ModbusClient, log_modbus_version

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 2
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

def remove_non_ascii(string: str) -> str:
    return ''.join(char for char in string if ord(char) > 0 and ord(char) < 128)

def swap_byte_pairs_to_string(s: bytes | bytearray) -> str:
    t = list(s)
    t[::2], t[1::2] = t[1::2], t[::2]
    return ''.join(t)

#int.to_bytes(2, byteorder='big')

class AWS3Modbus(ModbusClient):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:
        super().__init__(connection_str, group_by_gateway=group_by_gateway, unit_address=None,
                        byte_order=Endian.Big, word_order=Endian.Little)
        self.machine_name = None
        self._last_modbus_access = perf_counter()
        self._wait_after_read = 0.020
        self._wait_after_write = 0.130
        self._wait_threshold_s = 0  # we start without having to wait before next modbus

    def __str__(self) -> str:
        return f"AWS3 Welder Modbus connection on {repr(self.client)}"

    def __repr__(self) -> str:
        return f"AWS3Modbus({self._connection_str}, group_by_gateway={self.group_by_gateway}"

    #----------------------------------------------------------------------------------------------

    def get_identification_str(self) -> str:
        return f"{self.machine_name}@{self._connection_str}"

    def _sync_modbus_timing(self, next_wait_s: float = None):
        """To generate a defined wait between two modbus accesses.

        Args:
            threshold_s (float, optional): Time to Wait between two modbus access in s. Defaults to 0.02.
        """
        while True:
            t0 = perf_counter()
            if t0 - self._last_modbus_access > self._wait_threshold_s:
                #print(f"P:{t0 - self._last_modbus_access}")
                break
        self._last_modbus_access = t0  # timestamp for sync of next access
        if next_wait_s:
            self._wait_threshold_s = next_wait_s
        else:  # set the standard (minimum wait)
            self._wait_threshold_s = self._wait_after_read

    def setup_device(self):
        self.set_machine_byteorder()  # switch byte order to default
        self.machine_name = self.read_name().strip()

    def set_machine_byteorder(self, bo: int = 3) -> None:
        self._sync_modbus_timing()
        self._wait_threshold_s = self._wait_after_write
        self.write_register(9999-1, bo, unit_address=3) # 3=default, 1=big


    def is_machine_ready(self) -> tuple:
        self._sync_modbus_timing()
        #return not self.read_coils(65-1, 1, unit_address=3)[0]
        #return self.read_coils(97-1, 8, unit_address=3)[0]
        bits = self.read_coils(97-1, 8, unit_address=3)
        d = {
            "ready": 1 if bits[0] else 0,
            "operational_mode": 1 if bits[1] else 0,  # 0=auto, 1=step
            "reject": 1 if bits[4] else 0,
            "hfi_device_fault": 1 if bits[5] else 0,
            "ok": 1 if bits[6] else 0
        }
        return bits[0], d

    def read_machine_lock_status(self) -> tuple:
        self._sync_modbus_timing()
        return self.read_coils(45-1, 1, unit_address=3)[0]

    def lock_machine_step(self) -> bool:
        self._sync_modbus_timing(next_wait_s=self._wait_after_write)
        return self.write_coil(45-1, True, unit_address=3)

    def unlock_machine_step(self) -> bool:
        self._sync_modbus_timing(next_wait_s=self._wait_after_write)
        return self.write_coil(45-1, False, unit_address=3)

    def write_program_no(self, number):
        self._sync_modbus_timing(next_wait_s=self._wait_after_write)
        #ec: BinaryPayloadBuilder = self.getEncoder()
        #ec.add_16bit_uint(number)
        #self.write_registers(200-1, ec.to_registers(), unit_address=3)
        #self.write_register(200-1, pack(">H", number), unit_address=3)
        self.write_register(200-1, number, unit_address=3)

    def read_program_no(self) -> int:
        self._sync_modbus_timing()
        response = self.read_holding_registers(200-1, 1, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        return dc.decode_16bit_uint()

    def read_axis_counter(self, axis: int) -> int:
        assert (axis in [1,2])
        self._sync_modbus_timing()
        response1 = self.read_holding_registers(1-1, 2, unit_address=axis)
        dc1: BinaryPayloadDecoder = self.getDecoder(response1)
        # self._sync_modbus_timing()
        # response2 = self.read_holding_registers(73-1, 4, unit_address=axis)
        # dc2: BinaryPayloadDecoder = self.getDecoder(response2)
        # d = {
        #     "counter": dc1.decode_32bit_uint(),
        #     "program": dc2.decode_32bit_int(),
        #     "program_counter": dc2.decode_32bit_int(),
        # }

        # this is optimizing modbusbus access to only the counter
        d = {
            "counter": dc1.decode_32bit_uint(),
            "program": None,
            "program_counter": None,
        }
        return d


    def read_binary_io(self) -> dict:
        self._sync_modbus_timing()
        response = self.read_holding_registers(412-1, 8, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        d = {
            "BinaryOutputs-MFP": dc.decode_32bit_uint(),
            "BinaryInputs-MFP": dc.decode_32bit_uint(),
            "BinaryOutputs-HFI": dc.decode_32bit_uint(),
            "BinaryInputs-HFI": dc.decode_32bit_uint(),
        }
        return d


    def read_measuring_values(self, axis: int) -> dict:
        assert (axis in [1,2])
        self._sync_modbus_timing()
        response = self.read_holding_registers(1-1, 76, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        d = {
            "Counter": dc.decode_32bit_uint(),
            "PeakCurrent_P1-Ipk": dc.decode_32bit_float(),
            "PeakVoltage_P1-Upk": dc.decode_32bit_float(),
            "EffectiveCurrent_P1-Irms": dc.decode_32bit_float(),
            "EffectiveVoltage_P1_Urms": dc.decode_32bit_float(),
            "Power_P1-P": dc.decode_32bit_float(),
            "Energy_P1-W": dc.decode_32bit_float(),
            "Resistance_P1-R": dc.decode_32bit_float(),
            "WeldTime_P1-tw": dc.decode_32bit_float(),
            "WeldPeriods_P1-tw~": dc.decode_32bit_float(),
            "Displacement_P1-s3": dc.decode_32bit_float(),
            "Force_P1-F/Ax1_Pressure_P1-p": dc.decode_32bit_float(),
            "Value_P1-v": dc.decode_32bit_float(),
            "PeakCurrent_P2-Ipk": dc.decode_32bit_float(),
            "PeakVoltage_P2-Upk": dc.decode_32bit_float(),
            "EffectiveCurrent_P2-Irms": dc.decode_32bit_float(),
            "EffectiveVoltage_P2-Urms": dc.decode_32bit_float(),
            "Power_P2-P": dc.decode_32bit_float(),
            "Energy_P2-W": dc.decode_32bit_float(),
            "Resistance_P2-R": dc.decode_32bit_float(),
            "WeldTime_P2-tw": dc.decode_32bit_float(),
            "WeldPeriods_P2-tw~": dc.decode_32bit_float(),
            "Displacement_P2-s3": dc.decode_32bit_float(),
            "Force_P2-F/Ax1_Pressure_P2-p": dc.decode_32bit_float(),
            "Value_P2-v": dc.decode_32bit_float(),
            "PeakCurrent_P3-Ipk": dc.decode_32bit_float(),
            "PeakVoltage_P3-Upk": dc.decode_32bit_float(),
            "EffectiveCurrent_P3-Irms": dc.decode_32bit_float(),
            "EffectiveVoltage_P3-Urms": dc.decode_32bit_float(),
            "Power_P3-P": dc.decode_32bit_float(),
            "Energy_P3-W": dc.decode_32bit_float(),
            "Resistance_P3-R": dc.decode_32bit_float(),
            "WeldTime_P3-tw": dc.decode_32bit_float(),
            "WeldPeriods_P3-tw~": dc.decode_32bit_float(),
            "PartRecognition_Fs-s1": dc.decode_32bit_float(),
            "PartRecognition_Fw-s1": dc.decode_32bit_float(),
            "Program": dc.decode_32bit_int(),
            "ProgramCounter": dc.decode_32bit_int(),
        }
        return d


    def read_parameters(self):
        self._sync_modbus_timing()
        response = self.read_holding_registers(200-1, 10, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        d = {
            "ProgramNumber": dc.decode_16bit_uint(),
            "ProgramSelection": dc.decode_8bit_uint(),
            "WeldRateOptimization": dc.decode_8bit_uint(),
            "ActualFault": {
                "FaultNumber": dc.decode_16bit_uint(),
                "ExtendedInfo": dc.decode_16bit_uint()
            },
            "HistFaultStepBack": dc.decode_16bit_uint(),
            "HistFault": dc.decode_32bit_uint(),
            "RemoteLogin": dc.decode_32bit_int(),
        }
        return d

    def read_program_parameters(self, axis: int):
        assert (axis in [1,2])
        self._sync_modbus_timing()
        response1 = self.read_holding_registers(301-1, 120, unit_address=axis)
        self._sync_modbus_timing()
        response2 = self.read_holding_registers(420-1, 120, unit_address=axis)
        self._sync_modbus_timing()
        pc1 = self.read_holding_registers(446-1, 2, unit_address=axis)
        return response1 + response2 + ["COUNTER "] + pc1

    def read_global_parameters(self, axis: int) -> dict:
        assert (axis in [1,2])
        self._sync_modbus_timing()
        response = self.read_holding_registers(601-1, 24, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        # read a string
        #self.set_machine_byteorder(1)
        self._sync_modbus_timing()
        response2 = self.read_holding_registers(833-1, 16, unit_address=axis)
        #self.set_machine_byteorder()
        dc2: BinaryPayloadDecoder = self.getDecoder(response2)
        d = {
            "CounterMode": dc.decode_8bit_uint(),
            "ElectrodeRefMode": dc.decode_8bit_uint(),
            "CounterActValue": dc.decode_32bit_uint(),
            "CounterUpLimit": dc.decode_32bit_uint(),
            "CounterUpWarning": dc.decode_32bit_uint(),
            "CounterDownStart": dc.decode_32bit_uint(),
            "CounterDownWarning": dc.decode_32bit_uint(),
            "PosRefGlob": dc.decode_32bit_float(),
            "PosHombeGlob": dc.decode_32bit_float(),
            "EnableDataLogging": dc.decode_8bit_uint(),
            "LogFileNumber": dc.decode_32bit_int(),
            "CheckReference": dc.decode_8bit_uint(),
            "LogExternalInfo": remove_non_ascii(swap_byte_pairs_to_string(dc2.decode_string(16*2).decode())),
            "StaticLoadPos0": dc.decode_32bit_float(),
            "StaticLoadPos1": dc.decode_32bit_float(),
        }
        return d

    def read_system_parameters(self):
        self._sync_modbus_timing()
        response = self.read_holding_registers(501-1, 125, unit_address=3)
        return response


    def read_ext_status(self, axis: int) -> dict:
        self._sync_modbus_timing()
        response = self.read_holding_registers(101-1, 2, unit_address=axis)
        return response

    def read_program_name(self, axis: int) -> str:
        assert (axis in [1,2])
        n = 16
        #self.set_machine_byteorder(1)
        self._sync_modbus_timing()
        response = self.read_holding_registers(801-1, n, unit_address=axis)
        #self.set_machine_byteorder()
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return remove_non_ascii(swap_byte_pairs_to_string(b.decode()))

    def read_name(self) -> str:
        n = 32  # guessed
        #self.set_machine_byteorder(1)
        self._sync_modbus_timing()
        response = self.read_holding_registers(801-1, n, unit_address=3)
        #self.set_machine_byteorder()
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return remove_non_ascii(swap_byte_pairs_to_string(b.decode()))

    def read_waveform_data(self, axis: int) -> dict:
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        _dt = [(19,"I"), (20,"U"), (3,"P"), (7,"s3"), (8,"F"), (9,"p")]
        d = {}
        for c, u in _dt:
            _log.debug(f"Activate Waveform {u}")
            self.write_register(1001-1, c, unit_address=axis)
            #self._sync_modbus_timing(next_wait_s=self._wait_after_write)
            response = self.read_holding_registers(1002-1, 6, unit_address=axis)
            dc: BinaryPayloadDecoder = self.getDecoder(response)
            d[u] = {
                "WaveformSampleTime": dc.decode_32bit_uint(),
                "WaveformPoints": dc.decode_32bit_uint(),
                "WaveformResolution": dc.decode_32bit_float(),
                "points": [],
            }
            p = d[u]["WaveformPoints"]
            m = ()
            k: int = 0
            while k < p:
                r = min(64, p - k)
                #self._sync_modbus_timing()
                response = self.read_holding_registers(1008 - 1 + k, r, unit_address=axis)
                dc: BinaryPayloadDecoder = self.getDecoder(response)
                for n in range(int(r/2)):
                    m = m + (dc.decode_32bit_float(),)
                k += r
            _log.debug(f"Data Points: {len(m)}")
            d[u]["points"] = list(m)
        return d

#--------------------------------------------------------------------------------------------------

class AWS3Modbus_DUMMY(object):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:
        self.dev = "SIMULATION"
        self.machine_name = "DUMMY"
        self.program_no = -1

    def get_identification_str(self) -> str:
        return f"{self.machine_name}@{self.dev}"

    def close(self):
        pass

    def setup_device(self):
        pass

    def set_machine_byteorder(self, bo: int = 3):
        pass

    def is_machine_ready(self) -> tuple:
        return True, {"ready": 1, "ok": 1, "reject": 0}

    def read_machine_lock_status(self) -> tuple:
        return False

    def lock_machine_step(self) -> bool:
        return True

    def unlock_machine_step(self) -> bool:
        return True

    def write_program_no(self, number):
        self.program_no = number

    def read_program_no(self) -> int:
        return self.program_no

    def read_axis_counter(self, axis: int) -> int:
        d = {
            "counter": -1,
            "program": -1,
            "program_counter": -1,
        }
        return d

    def read_binary_io(self) -> dict:
        return {}

    def read_measuring_values(self, axis: int):
        return []

    def read_parameters(self):
        return {}

    def read_program_parameters(self, axis: int):
        return []

    def read_global_parameters(self, axis: int):
        return {}

    def read_system_parameters(self):
        return []

    def read_program_name(self, axis: int) -> str:
        return "DUMMY"

    def read_name(self) -> str:
        pass

    def read_name(self) -> str:
        return "DUMMY-MACHINE"

    def read_waveform_data(self, axis: int) -> dict:
        return {}

#--------------------------------------------------------------------------------------------------
def test_basic_communication(dev: AWS3Modbus):
    import json

    d = dev.read_machine_lock_status()
    print("LOCK STATUS:", d)
    d = dev.read_ext_status(1)
    print(d)

    d = dev.read_name()
    print("NAME: ", d)
    d = dev.is_machine_ready()
    print("MACHINE READY: ", d)
    d = dev.read_axis_counter(1)
    print("AXIS1 COUNTER:", d)
    d = dev.read_axis_counter(2)
    print("AXIS2 COUNTER:", d)
    d = dev.read_binary_io()
    print("BINARY IO:", d)
    d = dev.read_parameters()
    print("PARAMETERS:", d)
    d = dev.read_system_parameters()
    print("SYSTEM PARAMETERS: ", d)

    for axis in (1,2):
        d = dev.read_program_name(axis)
        print(f"PROGRAM NAME AXIS {axis}: ", d)
        d = dev.read_global_parameters(axis)
        print(f"GLOBAL PARAMETERS AXIS {axis}: ", d)
        d = dev.read_measuring_values(axis)
        print(f"MEASURING AXIS {axis}: ", d)
        d = dev.read_program_parameters(axis)
        print(f"PROGRAM PARAMETERS AXIS {axis}: ", d)
        t0 = perf_counter()
        d = dev.read_waveform_data(1)
        with open(f"axis{axis}_waveforms.json", "wt") as file:
            file.write(json.dumps(d))
        print(f"WAVEFORM DATA AXIS {axis}:", d)
        print("TIME:", perf_counter()-t0)
    return


#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    log_modbus_version()

    with AWS3Modbus("tcp:172.21.101.100:502") as dev:
        test_basic_communication(dev)

    _log.info("End test")

# END OF FILE