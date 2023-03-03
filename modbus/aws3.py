from typing import Any, List
from struct import pack, unpack, unpack_from
from enum import Enum
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

class AWS3Modbus(ModbusClient):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:
        super().__init__(connection_str, group_by_gateway=group_by_gateway, unit_address=None,
                        byte_order=Endian.Big, word_order=Endian.Little)
        self.machine_name = None

    def __str__(self) -> str:
        return f"AWS3 Welder Modbus connection on {repr(self.client)}"

    def __repr__(self) -> str:
        return f"AWS3Modbus({self._connection_str}, group_by_gateway={self.group_by_gateway}"

    #----------------------------------------------------------------------------------------------
    def setup_device(self):
        self.set_machine_byteorder()  # switch byte order to default
        self.machine_name = self.read_name().strip()

    def get_identification_str(self) -> str:
        return f"{self.machine_name}@{self._connection_str}"

    def set_machine_byteorder(self, bo: int = 3) -> None:
        self.write_register(9999-1, bo, unit_address=3) # 3=default, 1=big

    def is_machine_ready(self) -> tuple:
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
        return self.read_coils(45-1, 1, unit_address=3)[0]

    def lock_machine_step(self) -> bool:
        return self.write_coil(45-1, True, unit_address=3)

    def unlock_machine_step(self) -> bool:
        return self.write_coil(45-1, False, unit_address=3)

    def write_program_no(self, number):
        #ec: BinaryPayloadBuilder = self.getEncoder()
        #ec.add_16bit_uint(number)
        #self.write_registers(200-1, ec.to_registers(), unit_address=3)
        #self.write_register(200-1, pack(">H", number), unit_address=3)
        self.write_register(200-1, number, unit_address=3)

    def read_program_no(self) -> int:
        response = self.read_holding_registers(200-1, 1, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)#
        return dc.decode_16bit_uint()

    def read_axis_counter(self, axis: int) -> int:
        assert (axis in [1,2])
        response1 = self.read_holding_registers(1-1, 2, unit_address=axis)
        dc1: BinaryPayloadDecoder = self.getDecoder(response1)
        response2 = self.read_holding_registers(73-1, 4, unit_address=axis)
        dc2: BinaryPayloadDecoder = self.getDecoder(response2)
        d = {
            "counter": dc1.decode_32bit_uint(),
            "program": dc2.decode_32bit_int(),
            "program_counter": dc2.decode_32bit_int(),
        }
        return d


    def read_binary_io(self) -> dict:
        response = self.read_holding_registers(412-1, 8, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        d = {
            "BinaryOutputs-MFP": dc.decode_32bit_uint(),
            "BinaryInputs-MFP": dc.decode_32bit_uint(),
            "BinaryOutputs-HFI": dc.decode_32bit_uint(),
            "BinaryInputs-HFI": dc.decode_32bit_uint(),
        }
        return d


    def read_measuring_values(self, axis: int):
        assert (axis in [1,2])
        response = self.read_holding_registers(1-1, 76, unit_address=axis)
        return response


    def read_parameters(self):
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
        response1 = self.read_holding_registers(301-1, 120, unit_address=axis)

        response2 = self.read_holding_registers(420-1, 120, unit_address=axis)
        pc1 = self.read_holding_registers(446-1, 2, unit_address=axis)
        return response1 + response2 + ["COUNTER "] + pc1

    def read_global_parameters(self, axis: int) -> dict:
        assert (axis in [1,2])
        response = self.read_holding_registers(601-1, 24, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        # read a string
        self.set_machine_byteorder(1)
        response2 = self.read_holding_registers(833-1, 16, unit_address=axis)
        self.set_machine_byteorder()
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
            "LogExternalInfo": remove_non_ascii(dc2.decode_string(16*2).decode()),
            "StaticLoadPos0": dc.decode_32bit_float(),
            "StaticLoadPos1": dc.decode_32bit_float(),
        }
        return d

    def read_system_parameters(self):
        response = self.read_holding_registers(501-1, 125, unit_address=3)
        return response

    def read_program_name(self, axis: int) -> str:
        assert (axis in [1,2])
        n = 16
        self.set_machine_byteorder(1)
        response = self.read_holding_registers(801-1, n, unit_address=axis)
        self.set_machine_byteorder()
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return remove_non_ascii(b.decode())

    def read_name(self) -> str:
        n = 32  # guessed
        self.set_machine_byteorder(1)
        response = self.read_holding_registers(801-1, n, unit_address=3)
        self.set_machine_byteorder()
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return remove_non_ascii(b.decode())

    def read_ext_status(self, axis: int) -> dict:
        n = 2
        #self.set_machine_byteorder(1)
        #response = self.read_input_registers(101-1, n, unit_address=1)
        response = self.read_holding_registers(101-1, n, unit_address=1)
        return response


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

#--------------------------------------------------------------------------------------------------
def test_basic_communication(dev: AWS3Modbus):
    d = dev.read_machine_lock_status()
    print(d)
    d = dev.read_name()
    # print(d)
    # d = dev.read_program_name(1)
    # print(d)
    # d = dev.read_program_name(2)
    # print(d)
    #d = dev.read_ext_status(1)
    #print(d)
    #d = dev.read_ext_status(2)
    #print(d)
    d = dev.is_machine_ready()
    print(d)
    return

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
    d = dev.read_global_parameters(1)
    print("GLOBAL PARAMETERS AXIS 1:", d)
    d = dev.read_global_parameters(2)
    print("GLOBAL PARAMETERS AXIS 1:", d)
    d = dev.read_measuring_values(1)
    print("MEASURING AXIS 1: ", d)
    d = dev.read_measuring_values(2)
    print("MEASURING AXIS 2: ",d)
    d = dev.read_program_parameters(1)
    print("PROGRAM PARAMETERS AXIS 1: ",d)
    d = dev.read_program_parameters(2)
    print("PROGRAM PARAMETERS AXIS 1: ", d)




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