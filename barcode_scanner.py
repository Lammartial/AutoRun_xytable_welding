
"""
Waveshare ETH-to-UART by socket connection instead of Virtual Comport.

It is using asyncio to be compliant to the UI dialog implementation which awaits either a
barcode scanned UDI or human typed UDI or for whatever reason it is being used elsewhere in the line.

"""

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
        dev = SerialComportDevice(resource_string, termination="\r")  # COM port
    else:
        dev = Eth2SerialDevice(resource_string, termination="\r\n")   # socket port
        
    return dev

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter
    from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    # test the client send and receive:
    #asyncio.run(tcp_send_and_receive_from_server(message="Hallo Welt!", timeout=2.0))
    #asyncio.run(tcp_send_and_receive_from_server(None, limit=10, timeout=25.0))
    try:
        #dev = create_barcode_scanner("COM24,9600,8N1")
        dev = create_barcode_scanner("172.21.101.35:2000")
        s = dev.request(None, timeout=10.5)
        print(s)
    except TimeoutError:
        _log.info("Timeout!")

    toc = perf_counter()
    _log.info(f"Need {toc - tic:0.4f} seconds")
    _log.info("DONE.")

# END OF FILE