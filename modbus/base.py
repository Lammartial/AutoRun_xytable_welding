"""
Modbus client base module. Defines abstract base class for all modbus clients.

"""

from typing import Any, List
from pymodbus import version as modbus_version
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian, Defaults
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# ----------------------------------------------------------------------- #
# This will send the error messages in the specified namespace to a file.
# The available namespaces in pymodbus are as follows:
# ----------------------------------------------------------------------- #
# * pymodbus.*          - The root namespace
# * pymodbus.server.*   - all logging messages involving the modbus server
# * pymodbus.client.*   - all logging messages involving the client
# * pymodbus.protocol.* - all logging messages inside the protocol layer
# ----------------------------------------------------------------------- #
logging.getLogger("pymodbus.client").setLevel(logging.INFO)
logging.getLogger("pymodbus.protocol").setLevel(logging.INFO)
logging.getLogger("pymodbus").setLevel(logging.INFO)

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


# -------------------------------------------------
# Generic error handling, to avoid duplicating code
# -------------------------------------------------

def _check_call(rr):
    """Check modbus call worked generically."""
    assert not isinstance(rr, ExceptionResponse), rr      # Device rejected request
    assert not rr.isError(), "Error in MODBUS response"   # test that call was OK    
    return rr

#--------------------------------------------------------------------------------------------------
def log_modbus_version():
    _log.info(f"PyModbus version: {modbus_version.version.short()}")

#--------------------------------------------------------------------------------------------------
def extract_c_string(bytes_array):
    s = bytes_array[:bytes_array.index(b'\x00')] # find the first \0 (termination char in C)
    return s.decode("utf-8") # convert it to python string

#--------------------------------------------------------------------------------------------------
class ModbusClient:
    """
    Connection string is
        tcp:host:port[,timeout_ms(default=1000)][:unit_id]                            -> modbus over TCP
        rtu:port:baud[,lineparams(default=8N1)][,timeout_ms(default=1000)][:unit_id]  -> modbus over Serial line

    """

    _connection_dict = {} # to keep track of all different modbus connections:
                          # group them by the host interface and port to work with typical modbus gateways
    _connection_open = {}

    def __init__(self, connection_str: str, unit_address: int | None = 0,
                 group_by_gateway: bool = True, byte_order: str = Endian.Big, word_order: str = Endian.Big) -> None:
        """_summary_

        Args:
            connection_str (str): _description_
            group_by_gateway (bool, optional): _description_. Defaults to True.
            byte_order (str, optional): _description_. Defaults to Endian.Big.
            word_order (str, optional): _description_. Defaults to Endian.Big.

        """

        self.byte_order = byte_order
        self.word_order = word_order
        self.group_by_gateway = group_by_gateway

        # check, which kind of connection we have:
        # tcp:host:port:unit
        # rtu:lineparameter:unit (unused here!)
        cna = connection_str.lower().split(":")
        assert (len(cna) > 2), f"connection setting wrong {connection_str}"
        assert (cna[0] in ["tcp", "rtu"]), f"Connection type {cna[0]} not supported {connection_str}"

        self.unit_address = int(cna.pop()) if len(cna) == 4 else unit_address
        if cna[0] == "tcp":
            self.host = cna[1]
            # check if we got a timeout parameter with port
            param = cna[2].split(",")
            self.timeout = int(param[1])/1000 if len(param) == 2 else Defaults.Timeout
            self.port = int(cna[2])
            #self.gateway_str = ":".join(cna[:3])
            self.gateway_str = ":".join([*cna[0:2], str(self.port)]) # this to sort all connection by gateways later on (exclude the timeout!)
            self.baudrate = None
            self.serial_line_param = None
        else:  # must be "rtu"
            self.port = cna[1]
            # split parameters
            param = cna[2].split(",")
            self.timeout = int(param[2])/1000 if len(param) == 3 else Defaults.Timeout
            self.baudrate = int(param[0]) if len(param) > 0 else int(9600)
            self.serial_line_param = str(param[1]).upper() if len(param) > 1 else "8N1"  # a string like "8N1"
            self.gateway_str = ":".join([ *cna[0:2], ",".join([str(self.baudrate), self.serial_line_param])]) # this to sort all connection by gateways later on (exclude the timeout!)
            self.host = None
        if (not group_by_gateway) or (self.gateway_str not in self.connection_dict):
            # need to create a new connection
            if cna[0] == "tcp":
                self.client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)  # create a new connection
            else:
                self.client = ModbusSerialClient(method="rtu",
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=int(self.serial_line_param[0]),
                    parity=self.serial_line_param[1],
                    stopbits=int(self.serial_line_param[2]),
                    timeout=self.timeout)  # create a new connection
        if group_by_gateway:
            if self.gateway_str in self.connection_dict:
                self.client = self.connection_dict[self.gateway_str]  # reuse the existing connection
            else:
                self.connection_dict[self.gateway_str] = self.client
                self.connection_open[self.gateway_str] = 0
        _log.debug("GATEWAY: %s", self.gateway_str)
        _log.debug("UNIT: %s", self.unit_address)

    # to provide the with ... statement protector
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def connection_dict(self) -> dict:
        return type(self)._connection_dict

    @property
    def connection_open(self) -> dict:
        return type(self)._connection_open

    # ---------------------------------------------
    def open(self):
        self.connection_open[self.gateway_str] += 1
        self.client.connect() # checks for already open connections -> can be called even if connection was already opened

    def close(self):
        self.connection_open[self.gateway_str] -= 1
        if self.connection_open[self.gateway_str] == 0:
            self.client.close()

    #--------------------------------------------------------------------------------------------------
    # easier to use interface
    def read_discrete_inputs(self, address: int, count: int, unit_address: int | None = None) -> ReadInputRegistersResponse | Any:
        readResponse = _check_call(self.client.read_discrete_inputs(address, count, slave=unit_address if unit_address is not None else self.unit_address))
        return readResponse.registers
    
    def read_input_registers(self, address: int, count: int, unit_address: int | None = None) -> ReadInputRegistersResponse | Any:
        readResponse = _check_call(self.client.read_input_registers(address, count, slave=unit_address if unit_address is not None else self.unit_address))
        return readResponse.registers

    def read_holding_registers(self, address: int, count: int, unit_address: int | None = None) -> ReadHoldingRegistersResponse | Any:
        readResponse = _check_call(self.client.read_holding_registers(address, count, slave=unit_address if unit_address is not None else self.unit_address))
        return readResponse.registers

    def write_register(self, address: int, value: int | float | str, unit_address: int | None = None) -> WriteMultipleRegistersResponse | Any:
        writeResponse = _check_call(self.client.write_register(address, value, slave=unit_address if unit_address is not None else self.unit_address))
        return writeResponse
    
    def write_registers(self, address: int, values: List[int | float | str], unit_address: int | None = None) -> WriteMultipleRegistersResponse | Any:
        writeResponse = _check_call(self.client.write_coils(address, values, slave=unit_address if unit_address is not None else self.unit_address))
        return writeResponse

    def write_coil(self, address: int, value: bool, unit_address: int | None = None) -> WriteMultipleRegistersResponse | Any:
        writeResponse = _check_call(self.client.write_coil(address, value, slave=unit_address if unit_address is not None else self.unit_address))
        return writeResponse
    
    def write_coils(self, address: int, values: List[bool], unit_address: int | None = None) -> WriteMultipleRegistersResponse | Any:
        writeResponse = _check_call(self.client.write_coils(address, values, slave=unit_address if unit_address is not None else self.unit_address))
        return writeResponse

#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    from time import sleep 

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