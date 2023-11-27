
"""
Waveshare ETH-to-UART by socket connection instead of Virtual Comport.

It is using asyncio to be compliant to the UI dialog implementation which awaits either a
barcode scanned UDI or human typed UDI or for whatever reason it is being used elsewhere in the line.

"""

from typing import Tuple
import re

from rrc.eth2serial import Eth2SerialDevice, tcp_send_and_receive_from_server
from rrc.serialport import SerialComportDevice

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

def create_barcode_scanner(resource_string: str) -> Eth2SerialDevice | SerialComportDevice:
    """Creates a RRC scanner depending on the resource string for abstraction.
    It creates either a network socket scanner or a COM port scanner.
    The Termination is set to LF only.

    Valid resource strings:

    hostname:port, e.g. "172.25.101.43:2000" for IPv4 172.25.101.43 at port 2000
    comport,baud,linesettings, e.g."COM7,9600,8N1" for COM7 with 9600 baud and 8 bits No parity, 1 stop bit

    Args:
        resource_string (str): Resource connection of the scanner.

    Returns:
        Eth2SerialDevice | SerialComportDevice: a device that can transparently being used
            by its function .request() to scan for input.

    """

    if "," in resource_string:
        dev = SerialComportDevice(resource_string, termination="\r")  # COM port
    else:
        dev = Eth2SerialDevice(resource_string, termination="\n")   # socket port
    return dev

#--------------------------------------------------------------------------------------------------

def decode_rrc_udi_label(raw: str, pcba_and_cell_udi_tuple: bool = False) -> Tuple[dict, str]:
    """Decodes a Python string for UDI information of either CELL or PCBA udi.

    If pcba_and_cell_udi_tuple set True, two UDI, separated by comma, are expected and decoded.
    e.g. 1CELL00000000505,1PCBA00000000664

    Args:
        raw (str): scanned string, converted into UTF-8 python string
        pcba_and_cell_udi_tuple (bool, optional): If true, a comma separated, combined CELL and PCBA string
                is expected and decoded both. If False, only one of both is expected. Defaults to False.

    Returns:
        Tuple[dict, list]: Dictionary of decoded information in the form:
                            { "CELL" or "PCBA": {serial_number: xxx, plant: yyy} }
    """
    global DEBUG

    _log = getLogger(__name__, DEBUG)


    def _records_to_result(records) -> dict:
        return {
            records[0]: {
                "serial_number": records[1],
                "plant": records[2],
            }
        }


    filter = re.compile(r"([\d|\w])(CELL|PCBA)([\d|\w]*)")  # only one and the first
    if pcba_and_cell_udi_tuple:
        filter = re.compile(r"([\d|\w])(CELL|PCBA)([\d|\w]*).*,.*([\d|\w])(CELL|PCBA)([\d|\w]*)")  # up to two separated by comma
    m = filter.findall(raw.strip())
    _log.debug(m)
    result = {}
    if len(m) == 1 and (len(m[0]) == 3):
        result = {
            **result,
            **_records_to_result((m[0][1], m[0][2], m[0][0]))  # type, serial, plant
        }
    elif len(m) == 1 and (len(m[0]) == 6):
        # 1st hit
        result = {
            **result,
            **_records_to_result((m[0][1], m[0][2], m[0][0]))  # type, serial, plant
        }
        # 2nd hit
        result = {
            **result,
            **_records_to_result((m[0][1+3], m[0][2+3], m[0][0+3]))  # type, serial, plant
        }
    else:
        result = {
            **result,
            **_records_to_result(("UNKNOWN", "", raw))
        }
    return result, raw

#--------------------------------------------------------------------------------------------------

def decode_rrc_product_serial_label(raw: str | bytes | bytearray) -> Tuple[dict, list]:
    """Converts an RRC specific barcode reading string into data record set.

    Args:
        raw (str | bytes | bytearray): _description_

    Returns:
        Tuple[dict, list]: The dictionary contains the decoded information, the 2nd part of the tuple contains the raw data as list.
    """

    _EOT = b"\x04" if isinstance(raw, (bytes | bytearray)) else "\x04"
    _RS = b"\x1e" if isinstance(raw, (bytes | bytearray)) else "\x1e"
    _GS = b"\x1d" if isinstance(raw, (bytes | bytearray)) else "\x1d"
    # EOT terminates the scan, GS and RS separates the pieces
    records = [n for n in [[gs for gs in rs.split(_GS) if gs != ""] for rs in raw.split(_EOT)[0].split(_RS)] if len(n)>0]
    # decode the data
    result = {}
    for r in records:
        for g in r:
            if "[)>" in g[:3]:
                continue
            if "1P" in g[:2]:
                # Part number
                result["part_number"] = g[2:]
            elif "30P" in g[:3]:
                # something
                result["part_name"] = g[3:]
            elif "10D" in g[:3]:
                result["date_code"] = g[3:]
            elif "S" in g[:1]:
                # serial number
                result["serial_number"] = g[1:]
            else:
                pass
    return result, records


#--------------------------------------------------------------------------------------------------

def test_general(resource_str: str, timeout: float = 20.0):
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    print(f"Please scan something...(timeout in {timeout}s)")
    try:
        dev = create_barcode_scanner(resource_str)
        s = dev.request(None, timeout=timeout, encoding=None)
        print(s)
    except TimeoutError:
        _log.info("Timeout!")



def test_rrc_udi_label(resource_str: str, timeout: float = 20.0):
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    print(f"Please scan RRC UDI label...(timeout in {timeout}s)")
    try:
        dev = create_barcode_scanner(resource_str)
        s = dev.request(None, timeout=timeout, encoding="utf-8")
        print("RAW:", s)
        r = decode_rrc_udi_label(s)
        print("RECORDS:", r)
    except TimeoutError:
        _log.info("Timeout!")



def test_rrc_serial_label(resource_str: str, timeout: float = 20.0):
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    print(f"Please scan RRC serial label...(timeout in {timeout}s)")
    try:
        dev = create_barcode_scanner(resource_str)
        s = dev.request(None, timeout=timeout, encoding="utf-8")
        print("RAW:", s)
        r = decode_rrc_product_serial_label(s)
        print("RECORDS:", r)
    except TimeoutError:
        _log.info("Timeout!")


def test_udi_decoder():
    global DEBUG

    _log = getLogger(__name__, DEBUG)

    print("Test the UDI decoder")
    print(decode_rrc_udi_label("1CELL00000000505"))
    print(decode_rrc_udi_label("1PCBA00000000664"))
    print(decode_rrc_udi_label("1CELL00000000505,1PCBA00000000664", pcba_and_cell_udi_tuple=True))
    print(decode_rrc_udi_label("1PCBA00000000664,1CELL00000000505", pcba_and_cell_udi_tuple=True))
    print(decode_rrc_udi_label("1CELL00000000505,1PCBA00000000664", pcba_and_cell_udi_tuple=False))  # SHOULD FAIL!


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter, strftime, localtime
    from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    print(f"Start: {strftime('%H:%M:%S', localtime())}")
    RESOURCE_STR = "COM3,9600,8N1"
    #RESOURCE_STR = "172.25.101.43:2000"  # VN Line 1 EOL
    RESOURCE_STR = "172.21.101.31:2000"  # HOM Line Corepack

    #test_udi_decoder()
    #test_general(RESOURCE_STR)
    test_rrc_serial_label(RESOURCE_STR)
    #test_rrc_udi_label(RESOURCE_STR)

    toc = perf_counter()
    _log.info(f"Need {toc - tic:0.4f} seconds")
    #print(f"End: {strftime('%H:%M:%S', localtime())}")
    _log.info("DONE.")

# END OF FILE