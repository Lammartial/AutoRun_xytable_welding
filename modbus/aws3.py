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
        self._wait_after_read = 0.0001
        self._wait_after_write = 0.0001
        self._wait_threshold_s = 0  # we start without having to wait before next modbus
        self._welding_waveforms = None
        self._welding_measurements = None
        self._welding_parameters = None
        self._toggle_bits = None

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
        self._toggle_bits = self._read_toggle_bits()

    def set_machine_byteorder(self, bo: int = 3) -> None:
        """
        1: Little Endian - Ascending Byte Order
        2: Big Endian (Data) - Descending Byte Order in Datum
        3: Big Endian (Registers) – Descending Byte Order in Registers (default)

        Args:
            bo (int, optional): See above. Defaults to 3.
        """
        self._sync_modbus_timing()
        self._wait_threshold_s = self._wait_after_write
        self.write_register(9999-1, bo, unit_address=3) # 3=default, 1=big


    def is_machine_ready(self) -> tuple:
        self._sync_modbus_timing()
        bits = self.read_coils(97-1, 8, unit_address=3)
        d = {
            "ready": 1 if bits[0] else 0,
            "operational_mode": 1 if bits[1] else 0,  # 0=auto, 1=step
            "reject": 1 if (bits[2] or bits[4]) else 0,  # combine both axes: either one fails
            "hfi_device_fault": 1 if bits[5] else 0,
            "ok": 1 if (bits[6] and bits[7]) else 0  # combine both axes: both need to be good
        }
        return bits[0], d


    def _read_toggle_bits(self) -> int:
        bits = self.read_coils(125-1, 2, unit_address=3)
        # create two bit pattern from the toggle bits just read
        return int(((1<<0) if bits[0] else 0) | ((1<<1) if bits[1] else 0))


    def is_toggle_bit_changed(self) -> bool:
        _n: int = self._read_toggle_bits()
        # both bits have to be changed
        changed: bool = ((self._toggle_bits ^ _n) == 0x03)
        if changed:
            self._toggle_bits = _n  # store for next round
        return changed


    def read_machine_lock_status(self) -> tuple:
        self._sync_modbus_timing()
        return self.read_coils(45-1, 1, unit_address=3)[0]

    def lock_machine_step(self) -> bool:
        self._sync_modbus_timing(next_wait_s=self._wait_after_write)
        return self.write_coil(45-1, True, unit_address=3)

    def unlock_machine_step(self) -> bool:
        self._sync_modbus_timing(next_wait_s=self._wait_after_write)
        return self.write_coil(45-1, False, unit_address=3)



    def read_machine_lock_status_x(self) -> tuple:
        response = self.read_holding_registers(208-1, 2, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        return 0 == dc.decode_32bit_int()

    def lock_machine_step_x(self) -> bool:
        ec: BinaryPayloadBuilder = self.getEncoder()
        ec.add_32bit_int(0)  # = log out
        return self.write_registers(208-1, ec.to_registers(), unit_address=3)

    def unlock_machine_step_x(self) -> bool:
        ec: BinaryPayloadBuilder = self.getEncoder()
        ec.add_32bit_int(2)  # = login ingenieur
        return self.write_registers(208-1, ec.to_registers(), unit_address=3)



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
        response = self.read_holding_registers(1-1, 2, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        return dc.decode_32bit_uint()

    def _decode_binary_ouput_hfi(self, _b) -> dict:
        return {
            "HFIReady": (_b>>0) & 1,  # Bit 0.0
            "OperationalMode": (_b>>1) & 1,  # Bit 0.1  (0 - Auto, 1 - Step)
            "Reject_Ax2": (_b>>2) & 1,  # Bit 0.2
            "CounterLimit": (_b>>3) & 1,  # Bit 0.3  (only in Mode without MFP)
            "Reject_Ax1": (_b>>4) & 1,  # Bit 0.4
            "HFIDeviceFault": (_b>>5) & 1,  # Bit 0.5
            "Ok_Ax1": (_b>>6) & 1,  # Bit 0.6
            "Ok_Ax2": (_b>>7) & 1,  # Bit 0.7

            "OutOfLimitsWeldTime_Ax1": (_b>>8) & 1,  # Bit 1.0
            "OutOfLimitsWeldTime_Ax2": (_b>>9) & 1,  # Bit 1.1
            "CounterPre-Warning": (_b>>10) & 1,  # Bit 1.2  (only in Mode without MFP)
            "ActionCounterEnd": (_b>>11) & 1,  # Bit 1.3
            "OutOfLimitsMonitoring_Ax1": (_b>>12) & 1,  # Bit 1.4
            "OutOfLimitsMonitoring_Ax2": (_b>>13) & 1,  # Bit 1.5
            "WeldEnd_Ax1": (_b>>14) & 1,  # Bit 1.6  (only in Mode without MFP)
            "WeldEnd_Ax2": (_b>>15) & 1,  # Bit 1.7  (only in Mode without MFP)

            "HomePosCylinder_Ax1": (_b>>16) & 1,  # Bit 2.0  (only in Mode without MFP)
            "HomePosCylinder_Ax2": (_b>>17) & 1,  # Bit 2.1  (only in Mode without MFP)
            "TriggerActive_Ax1": (_b>>18) & 1,  # Bit 2.2
            "TriggerActive_Ax2": (_b>>19) & 1,  # Bit 2.3

            "Reserved_(Type DC/AC)": (_b>>24) & 1,  # Bit 3.0  (Type DC/AC)
            "Reserved_(Unit Distance SI/US)": (_b>>25) & 1,  # Bit 3.1  (Unit Distance SI/US)
            "Reserved_(Unit Force SI/US)": (_b>>26) & 1,  # Bit 3.2  (Unit Force SI/US)
            "Reserved_(Unit Pressure SI/US)": (_b>>27) & 1,  # Bit 3.3  (Unit Pressure SI/US)
            "MeasurementToggleBit_Ax1": (_b>>28) & 1,  # Bit 3.4
            "MeasurementToggleBit_Ax2": (_b>>29) & 1,  # Bit 3.5
        }


    def _decode_binary_output_mfp(self, _b) -> dict:

        def _mfp_byte_0_1(b0: int, b1: int, suffix: str) -> dict:
            return {
                f"MFPReady{suffix}": (b0>>0) & 1,  # Bit 0.0
                f"HomePosition{suffix}": (b0>>1) & 1,  # Bit 0.1
                f"WaitPosition{suffix}": (b0>>2) & 1,  # Bit 0.2
                f"InterlockingCylUnlocked{suffix}": (b0>>3) & 1,  # Bit 0.3
                f"InterlockingCylLocked{suffix}": (b0>>4) & 1,  # Bit 0.4
                f"MFPControllerOn{suffix}": (b0>>5) & 1,  # Bit 0.5
                f"ErrorPart{suffix}": (b0>>6) & 1,  # Bit 0.6  (also in Mode without MFP)
                f"ErrorDisplacement{suffix}": (b0>>7) & 1,  # Bit 0.7  (also in Mode without MFP)

                f"MFPFault{suffix}": (b1>>0) & 1,  # Bit 1.0
                f"CounterPre-Warning{suffix}": (b1>>1) & 1,  # Bit 1.1
                f"CounterLimit{suffix}": (b1>>2) & 1,  # Bit 1.2
                f"SearchForceReached{suffix}": (b1>>3) & 1,  # Bit 1.3
                f"EndOfCycle{suffix}": (b1>>4) & 1,  # Bit 1.4
                f"ErrorForce/Pressure{suffix}": (b1>>5) & 1,  # Bit 1.5  (also in Mode without MFP)
            }

        return   {
            **_mfp_byte_0_1(_b>>0, _b>>8, "_Ax1"),   # bytes 0 and 1
            **_mfp_byte_0_1(_b>>16, _b>>24, "_Ax2")  # bytes 2 and 3
        }

    def read_binary_io(self) -> dict:
        self._sync_modbus_timing()
        response = self.read_holding_registers(412-1, 8, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        # expecting "dual axis mode" data
        # ommitting the inputs as the information is useless
        #   "BinaryOutputs-MFP": dc.decode_32bit_uint(),
        #   "BinaryInputs-MFP": dc.decode_32bit_uint(),
        #   "BinaryOutputs-HFI": dc.decode_32bit_uint(),
        #   "BinaryInputs-HFI": dc.decode_32bit_uint(),
        d = {}
        d["BinaryOutputs-MFP"] = self._decode_binary_output_mfp(dc.decode_32bit_uint())
        dc.decode_32bit_uint()  # ignore MFP inputs
        d["BinaryOutputs-HFI"] = self._decode_binary_ouput_hfi(dc.decode_32bit_uint())
        # ignore HFI inputs
        return d


    def _decode_measuring_values(self, dc: BinaryPayloadDecoder) -> dict:
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
            "WeldPeriods_P1-tw": dc.decode_32bit_float(),
            "Displacement_P1-s3": dc.decode_32bit_float(),
            "Force_P1-F/Pressure_P1-p": dc.decode_32bit_float(),
            "Value_P1-v": dc.decode_32bit_float(),
            "PeakCurrent_P2-Ipk": dc.decode_32bit_float(),
            "PeakVoltage_P2-Upk": dc.decode_32bit_float(),
            "EffectiveCurrent_P2-Irms": dc.decode_32bit_float(),
            "EffectiveVoltage_P2-Urms": dc.decode_32bit_float(),
            "Power_P2-P": dc.decode_32bit_float(),
            "Energy_P2-W": dc.decode_32bit_float(),
            "Resistance_P2-R": dc.decode_32bit_float(),
            "WeldTime_P2-tw": dc.decode_32bit_float(),
            "WeldPeriods_P2-tw": dc.decode_32bit_float(),
            "Displacement_P2-s3": dc.decode_32bit_float(),
            "Force_P2-F/Pressure_P2-p": dc.decode_32bit_float(),
            "Value_P2-v": dc.decode_32bit_float(),
            "PeakCurrent_P3-Ipk": dc.decode_32bit_float(),
            "PeakVoltage_P3-Upk": dc.decode_32bit_float(),
            "EffectiveCurrent_P3-Irms": dc.decode_32bit_float(),
            "EffectiveVoltage_P3-Urms": dc.decode_32bit_float(),
            "Power_P3-P": dc.decode_32bit_float(),
            "Energy_P3-W": dc.decode_32bit_float(),
            "Resistance_P3-R": dc.decode_32bit_float(),
            "WeldTime_P3-tw": dc.decode_32bit_float(),
            "WeldPeriods_P3-tw": dc.decode_32bit_float(),
            "PartRecognition_Fs-s1": dc.decode_32bit_float(),
            "PartRecognition_Fw-s1": dc.decode_32bit_float(),
            "Program": dc.decode_32bit_int(),
            "ProgramCounter": dc.decode_32bit_int(),
        }
        return d


    def read_measuring_values(self, axis: int) -> dict:
        assert (axis in [1,2])
        self._sync_modbus_timing()
        response = self.read_holding_registers(1-1, 76, unit_address=axis)
        return self._decode_measuring_values(self.getDecoder(response))


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
        #dc: BinaryPayloadDecoder = self.getDecoder(response)
        dc = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Big, wordorder=Endian.Big) # why changed endianess ??
        # read a string
        self._sync_modbus_timing()
        response2 = self.read_holding_registers(833-1, 16, unit_address=axis)
        payload_str = b"".join(pack("<H", x) for x in response2)  # need to convert strings as little endian
        #dc2 = BinaryPayloadDecoder(payload_str, byteorder=Endian.Big, wordorder=Endian.Big)
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
            #"LogExternalInfo": remove_non_ascii(swap_byte_pairs_to_string(dc2.decode_string(16*2).decode())),
            "LogExternalInfo": remove_non_ascii(payload_str.decode()),
            "StaticLoadPos0": dc.decode_32bit_float(),
            "StaticLoadPos1": dc.decode_32bit_float(),
        }
        return d


    def _decode_process_parameters(self, dc: BinaryPayloadDecoder) -> dict:
        # must be provided in little endian byte order
        d = {
            "ControlMode_P1": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Regulation Mode Pulse 1: 0 - I, 1 - U, 2 - P)
            "ControlMode_P2": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Regulation Mode Pulse 2: 0 - I, 1 - U, 2 - P)
            "Mon1LimitsMode_P1": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Monitoring Mode selectable Quantity 1 Pulse 1: 0 - Ipk,1 - Irms, 2 - Upk, 3 - Urms, 4 - P, 5 - W, 6 - R)
            "Mon2LimitsMode_P1": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Monitoring Mode selectable Quantity 2 Pulse 1: 0 - Ipk,1 - Irms, 2 - Upk, 3 - Urms, 4 - P, 5 - W, 6 - R)
            "Mon1LimitsMode_P2": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Monitoring Mode selectable Quantity 1 Pulse 2: 0 - Ipk,1 - Irms, 2 - Upk, 3 - Urms, 4 - P, 5 - W, 6 - R)
            "Mon2LimitsMode_P2": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Monitoring Mode selectable Quantity 2 Pulse 2: 0 - Ipk,1 - Irms, 2 - Upk, 3 - Urms, 4 - P, 5 - W, 6 - R)
            "MonRTLimitsMode_P1": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Real-Time Monitoring Mode Pulse 1: 0 - I, 1 - U, 2 - P, 3-W)
            "MonRTLimitsMode_P2": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Real-Time Monitoring Mode Pulse 2: 0 - I, 1 - U, 2 - P, 3-W)
            "ToolsAPC_P1": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Tools/APC Pulse 1)
            "ToolsAPC_P2": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Tools/APC Pulse 2)
            "DplMode": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Displacement Mode: 0 - abs, 1 - ref, 2 - rel)
            "RepeatPulse": dc.decode_8bit_uint(),  #  1 Byte 0xFF (Repeat Pulse 2)
            "Amplitude_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Amplitude Pulse 1)
            "Amplitude_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Amplitude Pulse 2)
            "TimeSearch/TimeClose": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Search Time 1..9999 / Valve Closing Time 1..9999)
            "TimeSqueeze": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Squeeze Time 1..9999)
            "TimeUp_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Up-Slope Time Pulse 1 0.1..620)
            "TimeWeld_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Weld Time Pulse 1 0.1..620)
            "TimeDown_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Down-Slope Time Pulse 1 0.1..620)
            "TimeCool": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Cool-Down Time 1..9999)
            "TimeUp_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Up-Slope Time Pulse 2 0.1..620)
            "TimeWeld_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Weld Time Pulse 2 0.1..620)
            "TimeDown_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Down-Slope Time Pulse 2 0.1..620)
            "TimeHold": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Hold Time 1..9999)
            "LimitMon1Upper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit selectable monitoring Quantity 1 Pulse 1)
            "LimitMon1Lower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit selectable monitoring Quantity 1 Pulse 1)
            "LimitMon2Upper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit selectable monitoring Quantity 2 Pulse 1)
            "LimitMon2Lower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit selectable monitoring Quantity 2 Pulse 1)
            "LimitTwUpper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Weld Time Pulse 1)
            "LimitTwLower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Weld Time Pulse 1)
            "LimitFUpper_P1/LimitPrsUpper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Force/Pressure Pulse 1)
            "LimitFLower_P1/LimitPrsLower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Force/Pressure Pulse 1)
            "LimitMon1Upper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit selectable monitoring Quantity 1 Pulse 2)
            "LimitMon1Lower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit selectable monitoring Quantity 1 Pulse 2)
            "LimitMon2Upper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit selectable monitoring Quantity 2 Pulse 2)
            "LimitMon2Lower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit selectable monitoring Quantity 2 Pulse 2)
            "LimitTwUpper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Weld Time Pulse 2)
            "LimitTwLower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Weld Time Pulse 2)
            "LimitFUpper_P2/LimitPrsUpper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Force/Pressure Pulse 2)
            "LimitFLower_P2/LimitPrsLower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Force/Pressure Pulse 2)
            "LimitRTMonUpper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Real-Time monitoring Quantity Pulse 1)
            "TbegRTMonUpper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Begin Interval Upper Limit Real-Time monitoringQuantity Pulse 1)
            "TendRTMonUpper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (End Interval Upper Limit Real-Time monitoring QuantityPulse 1)
            "LimitRTMonLower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Real-Time monitoring Quantity Pulse 1)
            "TbegRTMonLower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Begin Interval Lower Limit Real-Time monitoringQuantity Pulse 1)
            "TendRTMonLower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (End Interval Lower Limit Real-Time monitoring QuantityPulse 1)
            "LimitRTMonUpper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Real-Time monitoring Quantity Pulse 2)
            "TbegRTMonUpper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Begin Interval Upper Limit Real-Time monitoringQuantity Pulse 2)
            "TendRTMonUpper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (End Interval Upper Limit Real-Time monitoring QuantityPulse 2)
            "LimitRTMonLower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Real-Time monitoring Quantity Pulse 2)
            "TbegRTMonLower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Begin Interval Lower Limit Real-Time monitoringQuantity Pulse 2)
            "TendRTMonLower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (End Interval Lower Limit Real-Time monitoring QuantityPulse 2)
            "LimitS1Upper": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Part Recognition)
            "LimitS1Lower": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Part Recognition)
            "PosS2WeldTo_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Current Switch-Off Position Pulse 1)
            "PosS2WeldTo_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Current Switch-Off Positon Pulse 2)
            "LimitS3Upper_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Displacement Pulse 1)
            "LimitS3Lower_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Displacement Pulse 1)
            "LimitS3Upper_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Upper Limit Displacement Pulse 2)
            "LimitS3Lower_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Lower Limit Displacement Pulse 2)
            "ForceSearch": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Search Force)
            "ForceWeld_P1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Weld Force Pulse 1)
            "ForceWeld_P2": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Weld Force Pulse 2)
            "ForceHold": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Hold Force)
            "WaitFollowUp/PressureClose": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Wait Time Apply Follow-Up Force / Closing Pressure)
            "TimeFollowUp/PressureWeld": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Duration Apply Follow-Up Force / Weld Pressure)
            "PosWait": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Wait Position)
            "PosSearch": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Search Position)
            "OffsetS1": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Offset S1)
            "DplTimeCool": dc.decode_16bit_uint(),  #  2 Byte 0xFFFF (Cooling Time for measuring s3)
            "TimeRepeat": dc.decode_32bit_float(),  #  4 Byte 0x80000000 (Repeat Time Pulse 2 0..9999)
        }
        return d


    def read_process_parameters(self, axis: int) -> dict:
        assert (axis in [1,2])
        n = 123  # 123 holdings -> 246 bytes
        self._sync_modbus_timing()
        response = self.read_holding_registers(5001 - 1, n, unit_address=axis)
        payload = b"".join(pack("<H", x) for x in response)
        dc: BinaryPayloadDecoder = BinaryPayloadDecoder(payload, byteorder=Endian.Little, wordorder=Endian.Little)
        return self._decode_process_parameters(dc)


    def read_waveform_data(self, axis: int, selection: tuple = ("I","U","P","s3","F","p")) -> dict:
        """Read selected waveform data points.

        Note that each waveform needs about 500ms to select and then read.
        If less points are stored this time reduces.

        Args:
            axis (int): _description_
            selection (tuple, optional): _description_. Defaults to ("I","U","P","s3","F","p").

        Returns:
            dict: Read waveform data in following struct:
                     {
                        "selector": {
                            "WaveformPoints": int, 1-250
                            "WaveformResolution": float, scaler
                            "WaveformSampleTime": int, in ms
                            "points": List[float]
                        },
                        ...
                     }
        """
        global DEBUG
        _log = getLogger(__name__, DEBUG)
        _all = ((19,"I"), (20,"U"), (3,"P"), (7,"s3"), (8,"F"), (9,"p"))
        d = {}
        for c, u in [_t for _t in _all if _t[1] in selection]:
            _log.debug(f"Activate Waveform {u}")
            self.write_register(1001-1, c, unit_address=axis)
            self._sync_modbus_timing(next_wait_s=self._wait_after_write)
            response = self.read_holding_registers(1002-1, 6, unit_address=axis)
            dc: BinaryPayloadDecoder = self.getDecoder(response)
            d[u] = {
                "WaveformSampleTime": dc.decode_32bit_uint(),
                "WaveformPoints": dc.decode_32bit_uint(),
                "WaveformResolution": dc.decode_32bit_float(),
                "points": [],
            }
            p = d[u]["WaveformPoints"]*2  # two registers per point
            m = ()
            k: int = 0
            while k < p:
                r = min(120, p - k)  # the new manual doc says: 60 measurement points (float, 32bits) => 120 holdings
                self._sync_modbus_timing()
                response = self.read_holding_registers(1008 - 1 + k, r, unit_address=axis)
                z = min(len(response), r)
                dc: BinaryPayloadDecoder = self.getDecoder(response)
                for n in range(int(z/2)):
                    m = m + (dc.decode_32bit_float(),)
                k += z
            _log.debug(f"Data Points: {len(m)}")
            d[u]["points"] = list(m)
        return d


    def read_ext_measurement_status(self, axis: int) -> dict:
        # New docu says: 93 holdings, not 13; delivers ALWAYS 93 holdings!
        self._sync_modbus_timing()
        response = self.read_holding_registers(4001-1, 93, unit_address=axis)
        # as the endianess does not depend on the network transmission, we cannot rely on .fromRegisters() method of BinaryPayloadDecoder
        # instead, we need to convert little endian words to bytes
        #payload = b"".join(pack("<H", x) for x in response[:13])
        payload = b"".join(pack("<H", x) for x in response)
        dc = BinaryPayloadDecoder(payload, byteorder=Endian.Little, wordorder=Endian.Little)
        d1 = {
            "TimeStamp_Year": dc.decode_8bit_uint(),  # (Offset beginning from Year 2000)
            "TimeStamp_Month": dc.decode_8bit_uint(),
            "TimeStamp_Day": dc.decode_8bit_uint(),
            "TimeStamp_Hour": dc.decode_8bit_uint(),
            "TimeStamp_Minute": dc.decode_8bit_uint(),
            "TimeStamp_Second": dc.decode_8bit_uint(),
            "TimeStamp_0.01s": dc.decode_8bit_uint(),
            "Measurement_Status": dc.decode_8bit_uint(),
            "OutOfEnvelope/OutOfRealTimeLimits": dc.decode_8bit_uint(),
            "Weld_Current_Abort": dc.decode_8bit_uint(),
            "QuanityRealTimeLimitPulse_1": dc.decode_8bit_uint(),
            "QuanityRealTimeLimitPulse_2": dc.decode_8bit_uint(),
            "QuanityEnvelope_1_Monitoring": dc.decode_8bit_uint(),
            "QuanityEnvelope_2_Monitoring": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_Ipk": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_Irms": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_Upk": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_Urms": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_P": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_W": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_R": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_tw": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_s1": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_s3": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_F": dc.decode_8bit_uint(),
            "MeasurementSpecificStatus_p": dc.decode_8bit_uint(),
        }
        # add also the rest of measuring values by standard decoder
        #d2 = self._decode_measuring_values(self.getDecoder(response[13:]))
        d2 = self._decode_measuring_values(dc)
        return {**d1, **d2}


    def read_program_name(self, axis: int) -> str:
        assert (axis in [1,2])
        n = 8
        self._sync_modbus_timing()
        response = self.read_holding_registers(801-1, n, unit_address=axis)
        payload_str = b"".join(pack("<H", x) for x in response)  # need to convert strings as little endian
        return remove_non_ascii(payload_str.decode())


    def read_name(self) -> str:
        """Read name of Machine.

        Returns:
            str: _description_
        """
        n = 16  # guess'd
        self._sync_modbus_timing()
        response = self.read_holding_registers(801-1, n, unit_address=3)
        payload_str = b"".join(pack("<H", x) for x in response)  # need to convert strings as little endian
        return remove_non_ascii(payload_str.decode())

     #----------------------------------------------------------------------------------------------

    def fetch_welding_parameters(self) -> dict:
        self._welding_parameters = {
            "name": self.read_name(),
            "parameters": self.read_parameters(),
            "program_name": {
                1: self.read_program_name(1),
                2: self.read_program_name(2),
            },
            # The global parameters have the counters which
            # yield into ongoing change of hash
            # -> commented out
            # "global_parameters": {
            #     1: self.read_global_parameters(1),
            #     2:  self.read_global_parameters(2),
            # },
            "process_parameters": {
                1: self.read_process_parameters(1),
                2: self.read_process_parameters(2),
            },
        }
        return self._welding_parameters


    def fetch_welding_measurements(self) -> dict:
        self._welding_measurements = {
            "binary_io": self.read_binary_io(),
            "measuring_values": {
                1: self.read_measuring_values(1),
                2: self.read_measuring_values(2),
            },
            "extended_measurement_status": {
                1: self.read_ext_measurement_status(1),
                2: self.read_ext_measurement_status(2),
            },
        }
        return self._welding_measurements


    def fetch_welding_waveforms(self) -> dict:
        self._welding_waveforms = {
            "waveform_data": self.read_waveform_data(1)  # only axis 1 useful
        }
        return self._welding_waveforms

#--------------------------------------------------------------------------------------------------

class AWS3Modbus_DUMMY(object):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:
        self.client = "SIMULATION"
        self.machine_name = "DUMMY"
        self.program_no = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_identification_str(self) -> str:
        return f"{self.machine_name}@{self.client}"

    def close(self):
        pass

    def setup_device(self):
        pass

    def set_machine_byteorder(self, bo: int = 3):
        pass

    def is_toggle_bit_changed(self) -> bool:
        return True

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
        return -1

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

    def read_process_parameters(self, axis: int) -> dict:
        return {}

    def read_waveform_data(self, axis: int) -> dict:
        return {}

    def read_ext_measurement_status(self, axis: int) -> dict:
        pass

    def read_program_name(self, axis: int) -> str:
        return "DUMMY"

    def read_name(self) -> str:
        pass

    def read_name(self) -> str:
        return "DUMMY-MACHINE"

    #----------------------------------------------------------------------------------------------

    def fetch_welding_parameters(self) -> dict:
        return {}

    def fetch_welding_measurements(self) -> dict:
        return {}

    def fetch_welding_waveforms(self) -> dict:
        return {}

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
def test_basic_communication(dev: AWS3Modbus):
    m = {}

    d = dev.write_program_no(6)
    d = dev.read_program_no()
    print(f"PROGRAM: {d}")

    d = dev.read_name()
    print("NAME: ", d)
    m["name"] = d
    d = dev.read_machine_lock_status()
    print("LOCK STATUS:", d)
    d = dev.is_machine_ready()
    print("MACHINE READY: ", d)
    d = dev.read_axis_counter(1)
    print("AXIS1 COUNTER:", d)
    m["counter_ax1"] = d
    d = dev.read_axis_counter(2)
    print("AXIS2 COUNTER:", d)
    m["counter_ax2"] = d
    d = dev.read_binary_io()
    print("BINARY IO:", d)
    m["binary_io"] = d
    d = dev.read_parameters()
    print("PARAMETERS:", d)
    m["parameters"] = d

    m["axis"] = {}
    for axis in (1,2):
        a = m["axis"][axis] = {}
        d = dev.read_program_name(axis)
        print(f"PROGRAM NAME AXIS {axis}: ", d)
        a["program_name"] = d
        d = dev.read_global_parameters(axis)
        print(f"GLOBAL PARAMETERS AXIS {axis}: ", d)
        a["global_parameters"] = d

        t0 = perf_counter()
        d = dev.read_process_parameters(axis)
        t = perf_counter()-t0
        print(f"PROCESS PARAMETERS AXIS {axis}: ", d)
        a["process_parameters"] = d
        print("-->TIME:", t)

        # t0 = perf_counter()
        # d = dev.read_program_parameters(axis)
        # t = perf_counter()-t0
        # print(f"PROGRAM PARAMETERS AXIS {axis}: ", d)
        # a["program_parameters"] = d
        # print("-->TIME:", t)

        t0 = perf_counter()
        d = dev.read_measuring_values(axis)
        t = perf_counter()-t0
        print(f"MEASURING AXIS {axis}: ", d)
        a["measuring_values"] = d
        print("-->TIME:", t)

        t0 = perf_counter()
        d = dev.read_ext_measurement_status(1)
        t = perf_counter()-t0
        print(f"EXT MEASUREMENT STATUS {axis}:", d)
        a["extended_measurement_status"] = d
        print("-->TIME:", t)

        t0 = perf_counter()
        d = dev.read_waveform_data(axis)
        t = perf_counter()-t0
        print(f"WAVEFORM DATA AXIS {axis}:", d)
        a["waveform_data"] = d
        print("-->TIME:", t)

    return m


def test_read_to_yaml(dev: AWS3Modbus, _log_fp):
    t0 = perf_counter()
    counter = dev.read_axis_counter(1)
    d = {
        **dev.fetch_welding_parameters(),
        **dev.fetch_welding_measurements(),
        #**dev.fetch_welder_waveforms(),
    }
    t = perf_counter()-t0
    with open(_log_fp / f"aws_readings_{counter}.yaml", "wt") as file:
        file.write(dump(d, Dumper=Dumper))
    print("-->TIME:", t)

    t0 = perf_counter()
    d = dev.fetch_welding_waveforms()
    t = perf_counter()-t0
    with open(_log_fp / f"aws_waveforms_{counter}.yaml", "wt") as file:
        file.write(dump(d, Dumper=Dumper))
    print("-->TIME:", t)


def test_returned_bitio_pattern(dev: AWS3Modbus):
    pp = PrettyPrinter(indent=4)
    print("FAILED","-"*100)
    print("HFI:")
    pp.pprint(dev._decode_binary_ouput_hfi(4030841885))
    print("MFP:")
    pp.pprint(dev._decode_binary_output_mfp(8388736))
    print("GOOD", "-"*100)
    print("HFI:")
    pp.pprint(dev._decode_binary_ouput_hfi(3225535565))
    print("MFP:")
    pp.pprint(dev._decode_binary_output_mfp(8388608))


def test_program_no_timing(dev: AWS3Modbus):

    def _set_program(x: int):
        print(f"Set program no: {x}")
        t0 = perf_counter()
        d = dev.write_program_no(x)
        _t = perf_counter()-t0
        print(f"T: {_t}s")

    def _read_program():
        t0 = perf_counter()
        d = dev.read_program_no()
        _t = perf_counter()-t0
        print(f"Read program no: {d} ({_t}s)")

    print("Reset program")
    _set_program(5)

    print("Unlock machine")
    t0 = perf_counter()
    dev.unlock_machine_step()
    _t = perf_counter()-t0
    print(f"T: {_t}s")
    sleep(0.1)
    _set_program(6)
    sleep(0.1)
    _set_program(5)
    sleep(0.1)
    print("Lock machine")
    t0 = perf_counter()
    dev.lock_machine_step()
    _t = perf_counter()-t0
    print(f"T: {_t}s")
    sleep(0.1)
    _set_program(6)
    sleep(0.1)
    _set_program(5)

    sleep(0.1)
    print("Unlock machine")
    t0 = perf_counter()
    dev.unlock_machine_step()
    _t = perf_counter()-t0
    print(f"T: {_t}s")

#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from yaml import load, dump, Loader, Dumper
    from json import dumps
    from time import sleep
    from pathlib import Path
    from pprint import PrettyPrinter
    from pymodbus.exceptions import ConnectionException

    ## Initialize the logging
    _log_fp = Path(__file__).parent / "../../.." / "logs"
    logger_init(filename_base=_log_fp / "aws3")  ## init root logger with different filename
    # set the pymodbus to desired debug level
    getLogger("pymodbus.client", DEBUG)
    getLogger("pymodbus.protocol", DEBUG)
    getLogger("pymodbus.payload", DEBUG)
    getLogger("pymodbus.transaction", DEBUG)
    getLogger("pymodbus", DEBUG)

    _log = getLogger(__name__, DEBUG)

    log_modbus_version()

    dev = AWS3Modbus("tcp:172.21.101.100:502")
    if dev.open():
        # d = test_basic_communication(dev)
        #test_read_to_yaml(dev, _log_fp)
        test_program_no_timing(dev)
        dev.close()

    #test_returned_bitio_pattern(dev)

    _log.info("End test")

# END OF FILE