"""
Provides basic ETH to SERIAL conversion handling the socket communication.
"""
import socket
import asyncio


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



#--------------------------------------------------------------------------------------------------

def get_ipv4():
    """
    Helper function that determines the own IPv4 address on the primary interface.
    Falls back to localhost if no IP available.

    Returns:
        str: IPv4 address
    """
    _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _s.settimeout(0)
    try:
        # doesn't even have to be reachable
        _s.connect(('10.254.254.254', 1))
        _ip = _s.getsockname()[0]
    except Exception:
        _ip = "127.0.0.1"
    finally:
        _s.close()
    return _ip

# initialize on load
OWN_PRIMARY_IP = get_ipv4()

# --------------------------------------------------------------------------- #

class Eth2Serial_SockSingleConnection_Device(object):
    # !!!!! IMPORTANT !!!!!!
    # For normal operation HIOKI SW1001 must stay connected via socket

    #def __init__(self, host: str, port: int, termination: str = "\r\n"):
    def __init__(self, resource_str: str, termination: str = "\r\n"):
        """Initialize the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{hostname or IPv4 address}:{port number}'
            termination (str, optional): Defines the line termination. Defaults to '\r\n'

        """
        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
        lst = resource_str.split(":")
        self.host = lst[0]          # string
        self.port = int(lst[1])     # int

    def __str__(self) -> str:
        return f"ETH to UART bridge (single con) at {self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"Eth2Serial_SockSingleConnection_Device({self.host}, {self.port}, termination={self.termination})"

    #----------------------------------------------------------------------------------------------

    def open_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)
        self.socket.connect((self.host, self.port))

    def close_socket(self):
        self.socket.close()

    def __enter__(self):
        self.open_socket()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.socket.close()

    def send(self, msg: str, timeout: float = 3.0) -> None:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.
        """
        try:
            self.socket.sendall(bytes(msg, "utf-8") + self._termination_as_bytes)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        except Exception as ex:
            #_log.exception(ex)
            # we have exception handler to log this install in custom_logging
            raise ex

    def request(self, msg: str | None, timeout: float = 3.0, limit: int = 0, encoding: str = "utf-8") -> str:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 5.0.
            limit (int, optional): _description_. Defaults to 0.

        Returns:
            str: _description_
        """
        _log = getLogger(__name__, DEBUG)
        try:
            if msg:
                self.socket.sendall(bytes(msg, "utf-8") + self._termination_as_bytes)
            # now read data until termination or timeout
            rcvdata = b""
            while True:
                _chunk = self.socket.recv(1024)
                if not _chunk:
                    break
                rcvdata += _chunk
                if (limit) and (len(rcvdata) > limit):
                    rcvdata = rcvdata[:limit]  # slice the received data
                    break
                if (rcvdata.rfind(self._termination_as_bytes) >= 0):
                    break
            result = rcvdata.decode(encoding=encoding)
            _log.debug(f"Received: {result!r}")
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     #_log.exception(ex)

        #     raise ex
        return result

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class Eth2SerialDevice(object):

    def __init__(self, resource_str: str, termination: str = "\r\n"):
        """Initialize the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{hostname or IPv4 address}:{port number}'
            termination (str, optional): Defines the line termination. Defaults to '\r\n'

        """
        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
        lst = resource_str.split(":")
        self.host = lst[0]          # string
        self.port = int(lst[1])     # int

    def __str__(self) -> str:
        return f"ETH to UART bridge at {self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"Eth2SerialDevice('{self.host}:{self.port}', termination='{self.termination}')"

    #----------------------------------------------------------------------------------------------

    def send(self, msg: str, timeout: float = 3.0, encoding: str | None = "utf-8") -> None:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.
             encoding (str, optional): will be passed to write() function.

        Returns:
            bool: _description_
        """

        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _s.settimeout(timeout)
            _s.connect((self.host, self.port))
            _s.sendall(bytes(msg, encoding) + self._termination_as_bytes)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     _log.exception(ex)
        #     raise
        finally:
            _s.close()

    #----------------------------------------------------------------------------------------------

    def request(self, msg: str | None, timeout: float | None = 3.0, limit: int = 0, encoding: str | None = "utf-8") -> str:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 5.0.
            limit (int, optional): _description_. Defaults to 0.
            encoding (str, optional): if given will be used to decode() result from bytes. If None, bytes will be returned. Defaults to utf-8.

        Returns:
            str: _description_
        """
        global DEBUG

        _log = getLogger(__name__, DEBUG)
        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if timeout:
                _s.settimeout(timeout)
            _s.connect((self.host, self.port))
            if msg:
                _s.sendall(bytes(msg, "utf-8") + self._termination_as_bytes)
            # now read data until termination or timeout
            rcvdata = b""
            while True:
                _chunk = _s.recv(1024)
                if not _chunk:
                    break
                rcvdata += _chunk
                if (limit) and (len(rcvdata) > limit):
                    rcvdata = rcvdata[:limit]  # slice the received data
                    break
                if (rcvdata.rfind(self._termination_as_bytes) >= 0):
                    break
            if encoding:
                result = rcvdata.decode(encoding=encoding)
            else:
                result = rcvdata
            _log.debug(f"Received: {result!r}")
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     _log.exception(ex)
        #     raise
        finally:
            _s.close()
        return result

    #----------------------------------------------------------------------------------------------

    async def request_async(self,  message: str | None, limit: None | str | bytes | int = None, encoding: str | None = "utf-8") -> str:
        """_summary_

        Args:
            message (str | None): _description_
            limit (None | str | bytes | int, optional): None=use class defined termination bytes,
                                str=use readline() function, bytes=uses this termination, int=use this number of characters to read.
                                Defaults to None.
            encoding (str, optional): if given will be used to decode() result from bytes. If None, bytes will be returned. Defaults to utf-8.

        Returns:
            str: _description_
        """
        global DEBUG

        async def xchange(reader, writer):
            _log = getLogger(__name__, DEBUG)
            if message:
                _log.debug(f'Send: {message!r}')
                writer.write(message.encode())
                await writer.drain()
            if limit is None:
                rcvdata = await reader.readuntil(separator=self._termination_as_bytes)
                rcvdata = rcvdata[:-len(self._termination_as_bytes)]
            elif isinstance(limit, int):
                #rcvdata = await reader.read()  # read until limit bytes or EOF
                rcvdata = bytes()
                while chunk := await reader.read(512):
                    # read until limit bytes or EOF
                    if not chunk:
                        break
                    rcvdata += chunk
                    if len(rcvdata) >= limit:
                        rcvdata = rcvdata[:limit]
                        break
            elif isinstance(limit, bytes):
                rcvdata = await reader.readuntil(separator=limit)  # read until function parameter defined termination bytes
                rcvdata = rcvdata[:-len(limit)]
            else:
                rcvdata = await reader.readline()  # read until \n or \r\n using library functions
            if encoding:
                result = rcvdata.decode(encoding=encoding)
            else:
                result = rcvdata
            _log.debug(f"Received: {result!r}")
            return result

        data = None
        # do NOT catch the exception for timeout here, propagate to the caller!
        #reader, writer = await asyncio.wait_for(asyncio.open_connection(_IP, _PORT), timeout/2)
        reader, writer = await asyncio.open_connection(self.host, self.port)

        # Wait for at most 1 second (which is also the pause time for this loop)
        try:
            #data = await asyncio.wait_for(xchange(reader, writer), timeout)
            data = await xchange(reader, writer)
        except asyncio.exceptions.TimeoutError:
            pass
        finally:
            # Close the connection
            writer.close()
            await writer.wait_closed()

        return data

#--------------------------------------------------------------------------------------------------

async def tcp_send_and_receive_from_server(resource_string: str, message: str | None, limit: str | bytes | int = b'\n') -> str:
    """
    Connects to the destination socket at IP:PORT.
    It sends some message if given and afterwards it waits for incoming without timeout.

    Args:
        message (str): message
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
        str: received data.
    """
    global DEBUG

    _IP, _PORT = resource_string.split(":")

    async def xchange(reader, writer):
        if message:
            if DEBUG:
                print(f'Send: {message!r}')
            writer.write(message.encode())
            await writer.drain()
        if isinstance(limit, int):
            #rcvdata = await reader.read()  # read until limit bytes or EOF
            rcvdata = bytes()
            while chunk := await reader.read(512):
                # read until limit bytes or EOF
                if not chunk:
                    break
                rcvdata += chunk
                if len(rcvdata) >= limit:
                    rcvdata = rcvdata[:limit]
                    break
        elif isinstance(limit, bytes):
            rcvdata = await reader.readuntil(separator=limit)  # read until \n or \r\n
        else:
            rcvdata = await reader.readline()  # read until \n or \r\n
        if DEBUG:
            print(f'Received: {rcvdata.decode()!r}')
        return rcvdata.decode()

    data = None
    # do NOT catch the exception for timeout here, propagate to the caller!
    #reader, writer = await asyncio.wait_for(asyncio.open_connection(_IP, _PORT), timeout/2)
    reader, writer = await asyncio.open_connection(_IP, _PORT)

    # Wait for at most 1 second (which is also the pause time for this loop)
    try:
        #data = await asyncio.wait_for(xchange(reader, writer), timeout)
        data = await xchange(reader, writer)
    except asyncio.exceptions.TimeoutError:
        pass
    finally:
        # Close the connection
        writer.close()
        await writer.wait_closed()

    return data

#--------------------------------------------------------------------------------------------------
async def test_async_request():
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    c = Eth2SerialDevice("192.168.1.90:23", termination="\r")
    r = await c.request_async(None)
    _log.info(r)

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    _log.info("Own IP: %s", OWN_PRIMARY_IP)

    _log.info("Test synchronus receive (10s timeout):")
    #c = Eth2SerialDevice("192.168.1.90:23", termination="\n")
    c = Eth2SerialDevice("192.168.69.77:2101", termination="\n")
    #c = Eth2SerialDevice("192.168.1.224:2000", termination="\n")
    #c = Eth2SerialDevice("192.168.1.224:2101", termination="\n")
    r = c.request(None, timeout=10)
    _log.info(r)

    #_log.info("Test asynchronus receive (CRTL-C or scan to stop):")
    #asyncio.run(test_async_request())

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE
