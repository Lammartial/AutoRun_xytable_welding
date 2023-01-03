from pymodbus import version as modbus_version
from pymodbus.client.sync import ModbusTcpClient, ModbusAsciiFramer, ModbusRtuFramer
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
# our libs
from tool_functions import filterString, createTimestamp, get_tz

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
# import logging
# _logger = logging.getLogger(__name__)
# _logger.setLevel("DEBUG")

import logging
import logging.handlers as Handlers

log = logging.getLogger()
log.setLevel(logging.DEBUG)

# ----------------------------------------------------------------------- #
# This will send the error messages in the specified namespace to a file.
# The available namespaces in pymodbus are as follows:
# ----------------------------------------------------------------------- #
# * pymodbus.*          - The root namespace
# * pymodbus.server.*   - all logging messages involving the modbus server
# * pymodbus.client.*   - all logging messages involving the client
# * pymodbus.protocol.* - all logging messages inside the protocol layer
# ----------------------------------------------------------------------- #
logging.getLogger("pymodbus.client").setLevel(logging.DEBUG)
logging.getLogger("pymodbus.protocol").setLevel(logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

RESOURCE_STR = "192.168.1.83"
PORT = 26          # waveshare module uses 23 for TCP <-> RS232 and 26 for TCP <-> RS485; standard Modbus is 502
UNIT_ADDRESS = 7   # device address on the RS485 bus, depends on fixed device setting
TIMEOUT = 0.5      # in s

BYTE_ORDER = Endian.Big
WORD_ORDER = Endian.Big
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
def test_mit_gegenstelle_1():
    global TIMEOUT, PORT, RESOURCE_STR, UNIT_ADDRESS
    with ModbusTcpClient(RESOURCE_STR, port=PORT, timeout=TIMEOUT) as client:
        #client.write_coil(0x0001, True, unit=UNIT_ADDRESS)
        #result = client.read_coils(0x0001, count=1, unit=UNIT_ADDRESS)
        #print(result.bits[0])
        encoder = BinaryPayloadBuilder(byteorder=BYTE_ORDER, wordorder=WORD_ORDER)
        encoder.add_16bit_uint(4)
        #payload = encoder.build()
        payload = encoder.to_registers()
        client.write_registers(101, payload, unit=UNIT_ADDRESS)

        # #
        # # decding the data is one by one while the decoder moves a pointer internally
        # # through the binary data field depending on the number of data bytes decoded in a step.
        # #
        # d = {}
        # payload = client.read_holding_registers(0x0000)
        # decoder = BinaryPayloadDecoder.fromRegisters(payload, byteorder=Endian.Big, wordorder=Endian.Big)
        # d["my_superstring"]  = filterString(decoder.decode_string(8))
        # d["my_superparameter"]  = decoder.decode_32bit_uint()
        # print("Dataset: {d}")

def test_mit_gegenstelle_2():
    global TIMEOUT, PORT, RESOURCE_STR, UNIT_ADDRESS
    with ModbusTcpClient(RESOURCE_STR, port=PORT, timeout=TIMEOUT) as client:
    #with ModbusTcpClient(RESOURCE_STR, port=PORT, timeout=TIMEOUT, framer=ModbusAsciiFramer) as client:
    #with ModbusTcpClient(RESOURCE_STR, port=PORT, timeout=TIMEOUT, framer=ModbusRtuFramer) as client:
        d = {}
        #regs = _check_call(client.read_holding_registers(0x0001, 7, slave=UNIT_ADDRESS))
        regs = client.read_holding_registers(0x0001, 9, unit=UNIT_ADDRESS)
        print(regs.registers)
        #decoder = BinaryPayloadDecoder.fromRegisters(regs, byteorder=BYTE_ORDER, wordorder=WORD_ORDER)
        #cc = "ascii"
        #d["run_stop"] = decoder.decode_16bit_uint()
        # d["temperature_pv"] = decoder.decode_16bit_uint()
        # d["pressure_pv"] = decoder.decode_16bit_uint()
        # d["temperature_sv"] = decoder.decode_16bit_uint()
        # d["pressure_sv"] = decoder.decode_16bit_uint()
        # d["temperature_mv"] = decoder.decode_16bit_uint()
        # d["pressure_mv"] = decoder.decode_16bit_uint()
        print(d)


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    print(f"PyModbus version: {modbus_version.version.short()}")

    tic = perf_counter()
    # for i in range(20):
    #     print(f"Write {i}...")
    #     test_mit_gegenstelle_1()
    test_mit_gegenstelle_1()
    test_mit_gegenstelle_2()
    toc = perf_counter()
    print(f"Send in {toc - tic:0.4f} seconds")
    print("DONE.")
# END OF FILE