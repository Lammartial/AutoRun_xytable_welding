"""
Modbus client base module. Defines abstract base class for all modbus clients.

"""

from typing import Any
from pymodbus import version as modbus_version
from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient, ModbusAsciiFramer, ModbusRtuFramer
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian, Defaults
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

# our libs
from .tools import filterString, createTimestamp, get_tz

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
    assert not rr.isError()  # test that call was OK
    assert not isinstance(rr, ExceptionResponse)  # Device rejected request
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

    def __init__(self, connection_str: str, unit_address: int = 0,
                 group_by_gateway: bool = True, byte_order: str = Endian.Big, word_order: str = Endian.Big) -> None:
        """_summary_

        Args:
            connection_str (str): _description_
            group_by_gateway (bool, optional): _description_. Defaults to True.
            byte_order (str, optional): _description_. Defaults to Endian.Big.
            word_order (str, optional): _description_. Defaults to Endian.Big.

        """
        self._connection_str = connection_str
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

    def __str__(self) -> str:
        return f"Modbus/TCP client at {self._connection_str}"

    def __repr__(self) -> str:
        return f"ModbusClient({self._connection_str}, unit_address={self.unit_address},\
                 group_by_gateway={self.group_by_gateway}, byte_order={self.byte_order}, word_order={self.word_order})"
    # ---------------------------------------------

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
    def readInputRegisters(self, address: int, count: int) -> Any:
        readResponse = _check_call(self.client.read_input_registers(address, count, unit=self.unit_address))
        return readResponse.registers

    def readHoldingRegisters(self, address: int, count: int) -> Any:
        readResponse = _check_call(self.client.read_holding_registers(address, count, unit=self.unit_address))
        return readResponse.registers

    def writeHoldingRegisters(self, address: int, registers: int) -> Any:
        writeResponse = _check_call(self.client.write_registers(address, registers, unit=self.unit_address, skip_encode=True))
        return writeResponse

#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    log_modbus_version()
    _log.info("End test")

# END OF FILE