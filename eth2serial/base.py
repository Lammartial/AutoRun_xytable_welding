"""
Provides basic ETH to SERIAL conversion handling the socket communication.
"""

import socket
import errno
import asyncio
import time
from binascii import hexlify
from typing import Tuple, List

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

## initialize on load
#OWN_PRIMARY_IP = get_ipv4()


#--------------------------------------------------------------------------------------------------


def is_socket_closed(sock: socket.socket) -> bool:
    """Returns True if the remote side did close the connection."""
    try:
        buf = sock.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
        if buf == b'':
            return True
    except BlockingIOError as exc:
        if exc.errno != errno.EAGAIN:
            # Raise on unknown exception
            raise
    return False


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class Eth2SerialDevice(object):

    def __init__(self, resource_str: str, termination: str | Tuple[str, str] | List[str, str] = "\r\n", trim_termination: bool = True, open_connection: bool = True, pause_on_retry: int | None = 10) -> None:
        """Initialize the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{hostname or IPv4 address}:{port number}'
            ermination (str | Tuple[str, str], optional): Defines the line termination for both directions if string otherwise
                if tuple first is termination for send and second for receive. Defaults to '\r\n'.
            trim_termination (bool, ooptional): If True the termination chars on incomming responses will be trimmed, otherwise unchanged. Defaults to True.
            open_connection (bool, optional): If True, the connection is opened once on creation and never actively closed.
                If False, the connection is opened on each send/request. Defaults to True.
            pause_on_retry (int, optional): If retries is > 1 on send/request, the pause in milliseconds is held before next try. Defaults to 10.

        """

        if isinstance(termination, (tuple, list)):
            # different send and receive termination
            self._send_termination = termination[0]
            self._receive_termination = termination[1]
        else:
            # using the same termination for send and receive (default usage for all manufacturing devices until 2026)
            self._send_termination = termination
            self._receive_termination = termination
        # need them also as bytes
        self._send_termination_as_bytes = bytes(self._send_termination, "utf-8")
        self._receive_termination_as_bytes = bytes(self._receive_termination, "utf-8")
        self.trim_termination = trim_termination
        self._resource_str = resource_str  # for debug information in __repr__
        lst = resource_str.split(":")
        self.host = lst[0]          # string
        self.port = int(lst[1])     # int
        self.pause_on_retry = pause_on_retry
        self.socket = None
        self._keep_connection_open = open_connection
        if open_connection:
            self.connect_socket()

    def __str__(self) -> str:
        return f"ETH to SERIAL bridge at {self.host}:{self.port}"

    def __repr__(self) -> str:
        _t_str = f"S:{hexlify(self._send_termination_as_bytes).decode()},R:{hexlify(self._receive_termination_as_bytes).decode()}" if self._send_termination != self._receive_termination else hexlify(self._send_termination_as_bytes).decode()
        return f"Eth2SerialDevice('{self.host}:{self.port}', termination='{_t_str}', trim_termination={self.trim_termination}, open_connection={self._keep_connection_open}, pause_on_retry={self.pause_on_retry})"


    #----------------------------------------------------------------------------------------------


    def connect_socket(self, timeout: float | None = None) -> socket:
        # setting self._keep_connection_open to True leaves the connection
        # open as long as the instance lives
        if self._keep_connection_open and self.socket: # and not is_socket_closed(self.socket):
            if timeout:
                self.socket.settimeout(timeout)  # modifies the timeout also for following use !!
            return self.socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if timeout:
            self.socket.settimeout(timeout)
        self.socket.connect((self.host, self.port))
        return self.socket


    def close_connection(self, force: bool = False) -> None:
        if not force and self._keep_connection_open:
            return  # block closing the connection
        try:
            # shutdown parameter:
            # Both 2
            #   Disables a Socket for both sending and receiving. This field is constant.
            # Receive 0
            #   Disables a Socket for receiving. This field is constant.
            # Send 1
            #   Disables a Socket for sending. This field is constant.
            #self.socket.shutdown(2)
            self.socket.close()
        except AttributeError:
            # self.socket could be None
            pass
        self.socket = None


    def __enter__(self, timeout: float = None) -> object:
        self.connect_socket(timeout=timeout)
        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close_connection(force=True)


    #----------------------------------------------------------------------------------------------


    def send(self, msg: str | bytes | bytearray,
             timeout: float = 3.0,
             pause_after_write: int | None = None,
             encoding: str | None = "utf-8",
             retries: int = 1) -> None:

        """Sends a message to a serial device.

        Args:
            msg (str): message string to send. Line teminator will be added.
            timeout (float, optional): _description_. Defaults to 1.0.
            pause_after_write (int, optional):  Pause after sending the command in milliseconds. Defaults to None.
            encoding (str, optional): will be passed to write() function.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            bool: _description_
        """

        try:
            self.connect_socket(timeout=timeout)
            if encoding is None:
                self.socket.sendall(bytes(msg))  # send it raw
            else:
                self.socket.sendall(bytes(msg, encoding) + self._send_termination_as_bytes)
            if pause_after_write:
                time.sleep(pause_after_write/1000)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     _log.exception(ex)
        #     raise
        finally:
            self.close_connection()


    #----------------------------------------------------------------------------------------------


    def request(self, msg: str | None,
                timeout: float | None = 3.0,
                pause_after_write: int | None = None,
                limit: int = 0,
                encoding: str | None = "utf-8",
                retries: int = 1) -> str:
        """
        Sends a message to a serial device if msg is given, then receives response from the serial device
        with given timeout.

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 5.0.
            pause_after_write (int, optional):  Pause after writing the command for a request in milliseconds,
                before reading and waiting the result. None disables it. Defaults to None.
            limit (int, optional): _description_. Defaults to 0.
            encoding (str, optional): if given will be used to decode() result from bytes. If None, bytes will be returned. Defaults to utf-8.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            str: _description_
        """
        global DEBUG

        _log = getLogger(__name__, DEBUG)
        try:
            self.connect_socket(timeout=timeout)
            if msg:
                self.socket.sendall(bytes(msg, encoding) + self._send_termination_as_bytes)
                if pause_after_write:
                    time.sleep(pause_after_write/1000)
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
                if (rcvdata.rfind(self._receive_termination_as_bytes) >= 0):
                    break
            if self.trim_termination:
                _t = rcvdata.rfind(self._receive_termination_as_bytes)
                if _t > 0:
                    rcvdata = rcvdata[:_t]
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
            self.close_connection()

        return result


    #----------------------------------------------------------------------------------------------
    # this is legacy, do not use it anymore


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
                rcvdata = await reader.readuntil(separator=self._receive_termination_as_bytes)
                rcvdata = rcvdata[:-len(self._receive_termination_as_bytes)]
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
    _log.info("Own IP: %s", get_ipv4())

    _log.info("Test synchronus receive (10s timeout):")
    #c = Eth2SerialDevice("192.168.1.90:23", termination="\n")
    #c = Eth2SerialDevice("192.168.69.77:2000", termination="\n")
    #c = Eth2SerialDevice("192.168.69.77:3000", termination="\n")
    #c = Eth2SerialDevice("192.168.69.77:2101", termination="\n")
    #c = Eth2SerialDevice("192.168.1.224:2000", termination="\n")
    c = Eth2SerialDevice("192.168.1.224:2101", termination="\n")

    #r = c.request("*help:smb?", timeout=20)
    r = c.request("*help:smb?", timeout=20)

    print("RESULT:", r.replace("\r", "\n"))
    #_log.info(r)

    #_log.info("Test asynchronus receive (CRTL-C or scan to stop):")
    #asyncio.run(test_async_request())

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE
