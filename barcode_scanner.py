
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

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

def create_barcode_scanner(resource_string: str) -> Eth2SerialDevice | SerialComportDevice:
    if "," in resource_string:
        dev = SerialComportDevice(resource_string, termination="\n")  # COM port
    else:
        dev = Eth2SerialDevice(resource_string, termination="\n")   # socket port
    return dev

#--------------------------------------------------------------------------------------------------

def decode_rrc_udi_label(raw: str | bytes | bytearray) -> Tuple[dict, list]:
    #1CELL00000000505,1PCBA00000000664
    filter = re.compile(r"(.*)(CELL|PCBA)(.*)")
    m = filter.findall(raw.strip())
    print(m)
    pass

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

def test_general(resource_str: str):
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    print("Please scan something...")
    try:
        dev = create_barcode_scanner(resource_str)
        s = dev.request(None, timeout=20.5, encoding=None)
        print(s)
    except TimeoutError:
        _log.info("Timeout!")


def test_rrc_serial_label(resource_str: str):
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    print("Please scan RRC serial label...")
    try:
        dev = create_barcode_scanner(resource_str)
        s = dev.request(None, timeout=20.5, encoding="utf-8")
        print("RAW:", s)
        r = decode_rrc_product_serial_label(s)
        print("RECORDS:", r)
    except TimeoutError:
        _log.info("Timeout!")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter
    from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    RESOURCE_STR = "COM27,9600,8N1"
    #RESOURCE_STR = "172.25.101.43:2000"

    #test_general(RESOURCE_STR)
    test_rrc_serial_label(RESOURCE_STR)

    toc = perf_counter()
    _log.info(f"Need {toc - tic:0.4f} seconds")
    _log.info("DONE.")

# END OF FILE