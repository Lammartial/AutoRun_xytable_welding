"""

Step 1: Install: Python 3.10.9

Step 2: Install modules:
  python -m pip install --upgrade pip
  python -m pip install pymodbus


"""

from typing import Any, List
from time import perf_counter, sleep
from pymodbus import version as modbus_version
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian, Defaults
from pymodbus.bit_read_message import ReadCoilsResponse
from pymodbus.bit_write_message import WriteSingleCoilResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

import logging
LEVEL = logging.DEBUG    # debugging
#LEVEL = logging.INFO  # standard

logging.basicConfig()  # comment this out to disable logging at all

# ----------------------------------------------------------------------- #
# This will send the error messages in the specified namespace to a file.
# The available namespaces in pymodbus are as follows:
# ----------------------------------------------------------------------- #
# * pymodbus.*          - The root namespace
# * pymodbus.server.*   - all logging messages involving the modbus server
# * pymodbus.client.*   - all logging messages involving the client
# * pymodbus.protocol.* - all logging messages inside the protocol layer
# ----------------------------------------------------------------------- #
logging.getLogger("pymodbus").setLevel(LEVEL)
_log = logging.getLogger()
_log.setLevel(LEVEL)




# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #


class AWS3Modbus(object):

    def __init__(self, connection_str: str) -> None:
        _host, _port = connection_str.lower().split(":")

        self.client = ModbusTcpClient(_host, port=int(_port),
                    # following goes to client.params
                    retries=7,                   # default = 3
                    retry_on_empty=True,         # default = False
                    reconnect_delay=100,         # default = 100 ms
                    reconnect_delay_max=300000,  # default = 300000 ms
                )  # create a new connection


    # to provide the with ... statement protector
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # ---------------------------------------------

    def open(self) -> bool:
        return self.client.connect() # checks for already open connections -> can be called even if connection was already opened

    def close(self) -> None:
        self.client.close()

    # --- lower level

    def read_coils(self, address: int, count: int, unit_address: int | None = None) -> ReadCoilsResponse | Any:
        readResponse = self.client.read_coils(address, count, slave=unit_address if unit_address is not None else 0)
        return readResponse.bits[:count]

    def write_coil(self, address: int, value: bool, unit_address: int | None = None) -> WriteSingleCoilResponse | Any:
        writeResponse = self.client.write_coil(address, value, slave=unit_address if unit_address is not None else 0)
        return writeResponse

    def read_holding_registers(self, address: int, count: int, unit_address: int | None = None) -> ReadHoldingRegistersResponse | Any:
        readResponse = self.client.read_holding_registers(address, count, slave=(unit_address if unit_address is not None else 0))
        return readResponse.registers

    def write_register(self, address: int, value: int | float | str, unit_address: int | None = None) -> WriteMultipleRegistersResponse | Any:
        writeResponse = self.client.write_register(address, value, slave=unit_address if unit_address is not None else 0)
        return writeResponse

    # --- high level

    def read_machine_lock_status(self) -> tuple:
        return self.read_coils(45-1, 1, unit_address=3)[0]

    def lock_machine_step(self) -> bool:
        return self.write_coil(45-1, True, unit_address=3)

    def unlock_machine_step(self) -> bool:
        return self.write_coil(45-1, False, unit_address=3)

    def write_program_no(self, number):
        self.write_register(200-1, number, unit_address=3)

    def read_program_no(self) -> int:
        response = self.read_holding_registers(200-1, 1, unit_address=3)
        dc = BinaryPayloadDecoder.fromRegisters(response, byteorder=Endian.Big, wordorder=Endian.Little)
        return dc.decode_16bit_uint()

#--------------------------------------------------------------------------------------------------

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

    print(modbus_version)

    dev = AWS3Modbus("172.21.101.100:502")
    if dev.open():
        test_program_no_timing(dev)
        dev.close()

    print("End test")

# END OF FILE