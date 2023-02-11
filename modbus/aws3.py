from typing import Any, List
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
DEBUG = 1
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

class AWS3Modbus(ModbusClient):

    def __init__(self, connection_str: str, group_by_gateway: bool = True) -> None:           
        super().__init__(connection_str, group_by_gateway=group_by_gateway, unit_address=None,
                        byte_order=Endian.Little, word_order=Endian.Little)            
        response = self.write_register(9999-1, 1, unit_address=3)  # switch byte order to little endian
        self.byte_order=Endian.Little
        self.word_order=Endian.Little
            
    
    def read_measuring_values(self, axis: int):
        assert (axis in [1,2])
        response = self.read_holding_registers(1-1, 76, unit_address=axis)
        return response
    
    def read_parameters(self):
        response = self.read_holding_registers(200-1, 10, unit_address=3)
        return response
    
    def read_program_parameters(self, axis: int):
        assert (axis in [1,2])
        response1 = self.read_holding_registers(301-1, 120, unit_address=axis)
        response2 = self.read_holding_registers(420-1, 120, unit_address=axis)
        return response1 + response2

    def read_global_parameters(self, axis: int):
        assert (axis in [1,2])
        response = self.read_holding_registers(601-1, 24, unit_address=axis)        
        return response

    def read_system_parameters(self):
        response = self.read_holding_registers(501-1, 125, unit_address=3)
        return response

    def read_name(self) -> bytearray:        
        n = 32  # guessed 
        response = self.read_holding_registers(801-1, n, unit_address=3)
        self.decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=self.byte_order, wordorder=self.word_order)
        b = self.decoder.decode_string(size=n*2)  # size = bytes not words
        return b.decode("utf8")
    
#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from time import sleep 

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    log_modbus_version()

    #for a in range(0, 256):
    try:
        with AWS3Modbus("tcp:172.21.101.100:502") as dev:
            #encoder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            #encoder.add_16bit_uint(1)
            #payload = encoder.to_registers()
            #response = dev.write_register(9999-1, 1, unit_address=3)  # switch byte order to little endian
            #response = dev.read_input_registers(9999-1, 1, unit_address=3)
            #print(response)
           
            d = dev.read_name()
            print(d)
            d = dev.read_parameters()
            print("PARAMETERS:", d)
            d = dev.read_system_parameters()
            print("SYSTEM PARAMETERS: ", d)
            d = dev.read_measuring_values(1)
            print("MEASURING AXIS 1: ", d)
            d = dev.read_measuring_values(2)
            print("MEASURING AXIS 2: ",d)
            d = dev.read_program_parameters(1)
            print("PROGRAM PARAMETERS AXIS 1: ",d)
            d = dev.read_program_parameters(2)
            print("PROGRAM PARAMETERS AXIS 1: ", d)           
    except Exception:
        raise    

    _log.info("End test")

# END OF FILE