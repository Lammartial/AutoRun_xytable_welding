
"""
Waveshare ETH-to-UART by socket connection instead of Virtual Comport.

It is using asyncio to be compliant to the UI dialog implementation which awaits either a
barcode scanned UDI or human typed UDI or for whatever reason it is being used elsewhere in the line.

"""

import asyncio
from rrc.eth2serial.base import Eth2SerialDevice

DEBUG = 0

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

# --------------------------------------------------------------------------- #

#
# this is the ETH-to-UART bridge's IP address
# set it static in production situation
#
UART_BRIDGE_IP = "192.168.1.120"
UART_PORT = 2000 # UART1=2000, UART2=3000 # Industrial Scanner 23

#--------------------------------------------------------------------------------------------------
async def tcp_send_and_receive_from_server(message: str, timeout=1.0, limit: str | bytes | int = b'\n') -> str:
    """
    Connects to the ETH to UART bridge at the port 23 on the fixed IP UART_BRIDGE_IP.
    It sends some message if given and afterwards it waits for incoming with limit timeout.

    Args:
        message (str): message
        timeout (float, optional): Timeout for open, wait send and receive in seconds.
            timeout/2 is for open, rest for send/receive. Defaults to 1.0.
        limit (bytes, str or int, optional): Defines if the read function used:
            if limit is of bytes, it uses stream.readuntil(separator=limit)) so that the line
                termination can be set freely. Note that the terminator is stripped from data.
            if limit is of string, it uses stream.readline(). Note that the line terminator
                is NOT stripped from data.
            if limit is of integer, is uses stream.read(limit) so that the user can set the
                limit of bytes to be read. Note that at EOF the function returns even if less
                bytes than limit have been read.
            Defaults to b"\n".

    Returns:
        str: received data or None on timeout.
    """

    global UART_BRIDGE_IP, UART_PORT

    async def xchange(reader, writer):
        if message:
            if DEBUG:
                print(f'Send: {message!r}')
            writer.write(message.encode())
            await writer.drain()
        if isinstance(limit, int):
            rcvdata = await reader.read(limit)  # read until limit bytes or EOF
        elif isinstance(limit, bytes):
            rcvdata = await reader.readuntil(separator=limit)  # read until \n or \r\n
        else:
            rcvdata = await reader.readline()  # read until \n or \r\n
        if DEBUG:
            print(f'Received: {rcvdata.decode()!r}')
        return rcvdata.decode()

    data = None
    # do NOT catch the exception for timeout here, propagate to the caller!
    reader, writer = await asyncio.wait_for(asyncio.open_connection(UART_BRIDGE_IP, UART_PORT), timeout=timeout/2)

    # Wait for at most 1 second (which is also the pause time for this loop)
    try:
        data = await asyncio.wait_for(xchange(reader, writer), timeout=timeout/2)
    except asyncio.TimeoutError:
        pass
    finally:
        # Close the connection
        writer.close()
        await writer.wait_closed()
    return data

#--------------------------------------------------------------------------------------------------
def poll(timeout = 2.5):
    dev = Eth2SerialDevice(UART_BRIDGE_IP, UART_PORT)
    #dev.send("Hallo Welt!", timeout=timeout)
    s = dev.request(None, timeout=timeout)
    print(s)

#--------------------------------------------------------------------------------------------------

def create_from_resource(resource_string: str) -> Eth2SerialDevice:
    _IP, _PORT = resource_string.split(":")
    return Eth2SerialDevice(_IP, _PORT)

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter
    from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV

    DEBUG = 1
    tic = perf_counter()

    cfg = StationConfiguration(filename=CONF_FILENAME_DEV)
    #_IP = cfg._CONFIG["test_sockets"]["1"]["resource_strings"]["scanner"]
    _IP, _PORT = cfg.get_resource_strings_for_socket(1)[0].split(":")
    _IP, _PORT = "169.254.36.1:2000".split(":")
    print(_IP, _PORT)

    # test the client send and receive:
    #asyncio.run(tcp_send_and_receive_from_server(message="Hallo Welt!", timeout=2.0))
    #asyncio.run(tcp_send_and_receive_from_server(None, limit=10, timeout=25.0))
    try:
        dev = Eth2SerialDevice(_IP, int(_PORT))
        s = dev.request(None, limit=34, timeout=10.5)
        print(s)
    except TimeoutError:
        _log.info("Timeout!")

    toc = perf_counter()
    _log.info(f"Need {toc - tic:0.4f} seconds")
    _log.info("DONE.")

# END OF FILE