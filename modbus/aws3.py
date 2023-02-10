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


#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from time import sleep 

    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    log_modbus_version()

    #for a in range(0, 256):
    try:
        with ModbusClient("tcp:172.21.101.100:502", unit_address=None, byte_order=Endian.Little, word_order=Endian.Little) as dev:
            #encoder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            #encoder.add_16bit_uint(1)
            #payload = encoder.to_registers()
            response = dev.write_register(9999-1, 1, unit_address=3)  # switch byte order to little endian
            #response = dev.read_input_registers(9999-1, 1, unit_address=3)
            #print(response)
            response = dev.read_holding_registers(200-1, 2, unit_address=3)
            print(response)
            decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Little, wordorder=Endian.Little)
            d = decoder.decode_32bit_int()
            print(d)
            response = dev.read_holding_registers(208-1, 2, unit_address=3)
            print(response)
            decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Little, wordorder=Endian.Little)
            d = decoder.decode_32bit_int()
            print(d)
            #for i in range(100):
            response = dev.read_holding_registers(0, 2, unit_address=1)
            print(response)
            decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Little, wordorder=Endian.Little)
            d = decoder.decode_32bit_uint()
            print(d)
            #sleep(0.2)
            response = dev.read_holding_registers(501-1, 1, unit_address=3)            
            print(response)
            decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Little, wordorder=Endian.Little)
            d = decoder.decode_8bit_uint()
            print(d)
            #sleep(0.2)
            response = dev.read_holding_registers(801-1, 10, unit_address=3)
            print(response)
            decoder = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Little, wordorder=Endian.Little)
            cc = "ascii"
            d = decoder.decode_string(size=8)
            print(d)
    except Exception:
        raise    

    _log.info("End test")

# END OF FILE