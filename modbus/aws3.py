from typing import Any, List
from struct import pack, unpack, unpack_from
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

class AWS3Modbus(ModbusClient):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:
        super().__init__(connection_str, group_by_gateway=group_by_gateway, unit_address=None,
                        byte_order=Endian.Big, word_order=Endian.Little)
        response = self.write_register(9999-1, 3, unit_address=3)  # switch byte order to default

    def __str__(self) -> str:
        return f"AWS3 Welder Modbus connection on {repr(self.client)}"

    def __repr__(self) -> str:
        return f"AWS3Modbus({self._connection_str}, group_by_gateway={self.group_by_gateway}"

    #----------------------------------------------------------------------------------------------


    def is_machine_ready(self) -> tuple:
        return not self.read_coils(65-1, 1, unit_address=3)[0]

    def read_machine_lock_status(self) -> tuple:
        return self.read_coils(45-1, 1, unit_address=3)[0]

    def lock_machine_step(self):
        return self.write_coil(45-1, True, unit_address=3)

    def unlock_machine_step(self):
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

    def read_global_parameters(self, axis: int):
        assert (axis in [1,2])
        response = self.read_holding_registers(601-1, 24, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        # read a string
        response2 = self.read_holding_registers(833-1, 16, unit_address=axis)
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
            "LogExternalInfo": dc2.decode_string(16*2).decode("utf-8"),
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
        response = self.read_holding_registers(801-1, n, unit_address=axis)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return b.decode("utf8")

    def read_name(self) -> str:
        n = 32  # guessed
        response = self.read_holding_registers(801-1, n, unit_address=3)
        dc: BinaryPayloadDecoder = self.getDecoder(response)
        b = dc.decode_string(size=n*2)  # size = bytes not words
        return b.decode("utf8")


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
def test_sps_process(dev: AWS3Modbus, program_sequence: List[int] = [1,2,3,4,5]):
    print(f"Poor man's SPS machine: {dev.read_name()}, at {repr(dev)}")
    while True:
        if dev.is_machine_ready():
            counter_base_ax1 = dev.read_axis_counter(1)
            counter_base_ax2 = dev.read_axis_counter(2)
            lock_base = dev.read_machine_lock_status()
            program_no_base = dev.read_program_no()
            break
    print(f"Base counters: ", counter_base_ax1, counter_base_ax2)
    print(f"Base program no: {program_no_base}")
    #program_sequence = [1,2,3,4,5,6,7,8,9,10]  # demo
    program_step = 0
    print(f"Program step: {program_step} of {len(program_sequence)}")
    last_counter_ax1 = counter_base_ax1
    last_counter_ax2 = counter_base_ax2
    program_no = program_no_base
    next_program_no = program_sequence[program_step]
    _machine_locked = False
    while True:
        try:
            if not dev.is_machine_ready():
                continue
            # 1. lock the machine
            #dev.lock_machine_step()
            # 2. get the counters
            counter_ax1 = dev.read_axis_counter(1)
            #counter_ax2 = dev.read_axis_counter(2)
            # 3. check if we have to moved to the  next program step
            diffcount = last_counter_ax1["counter"] - counter_ax1["counter"]
            if diffcount >= 0:
                # yes we have finished a cycle -> move to next program step
                dev.lock_machine_step()
                _machine_locked = True
                program_step += 1
                if program_step >= len(program_sequence):
                    program_step = 0
                next_program_no = program_sequence[program_step]
                print(f"Move program step to {program_step} with program no {next_program_no}")
                last_counter_ax1 = counter_ax1
                #last_counter_ax2 = counter_ax2
            # 4. chek if the correct program step is set
            program_no = dev.read_program_no()
            if next_program_no != program_no:
                print(f"Set Program No: {next_program_no}")
                dev.write_program_no(next_program_no)
            else:
                #print(f"PROG NO {program_no} == NEXT NO {next_program_no}")
                #sleep(0.1)  # throttle polling loop
                pass
        except AssertionError as ex:
            print("Got Error:", ex)
        except Exception as ex:
            raise
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            if _machine_locked:
                dev.unlock_machine_step()
        sleep(0.055)  # throttle polling loop


#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    log_modbus_version()

    with AWS3Modbus("tcp:172.21.101.100:502") as dev:
        test_basic_communication(dev)
        test_sps_process(dev, program_sequence=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])

    _log.info("End test")

# END OF FILE