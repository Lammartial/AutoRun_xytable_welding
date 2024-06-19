"""
Provides basic ETH to GPIO conversion handling the socket communication.
"""
import socket
import errno
import asyncio
import time

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #





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


class Eth2GPIODevice(object):

    def __init__(self, resource_str: str, termination: str = "\r\n", open_connection: bool = True, pause_on_retry: int | None = 10):
        """Initialize the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{hostname or IPv4 address}:{port number}'
            termination (str, optional): Defines the line termination. Defaults to '\r\n'
            open_connection (bool, optional): If True, the connection is opened once on creation and never actively closed.
                If False, the connection is opened on each send/request. Defaults to True.
            pause_on_retry (int, optional): If retries is > 1 on send/request, the pause in milliseconds is held before next try. Defaults to 10.

        """
        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
        lst = resource_str.split(":")
        self.host = lst[0]          # string
        self.port = int(lst[1])     # int
        self.pause_on_retry = pause_on_retry
        self.socket = None
        self._keep_connection_open = open_connection
        if open_connection:
            self.connect_socket()

    def __str__(self) -> str:
        return f"ETH to GPIO bridge at {self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"Eth2GPIODevice('{self.host}:{self.port}', termination='{self.termination}')"

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

    def send(self, msg: str,
             timeout: float = 3.0,
             pause_after_write: int | None = None,
             encoding: str | None = "utf-8",
             retries: int = 1) -> None:
        """_summary_

        Args:
            msg (str): message string to send. Line teminator will be added.
            timeout (float, optional): _description_. Defaults to 1.0.
            encoding (str, optional): will be passed to write() function.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            bool: _description_
        """

        try:
            self.connect_socket(timeout=timeout)
            self.socket.sendall(bytes(msg, encoding) + self._termination_as_bytes)
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

    def request(self, msg: bytes | None,
                timeout: float | None = 3.0,
                pause_after_write: int | None = None,
                limit: int = 0,
                encoding: str | None = "utf-8",
                retries: int = 1) -> str:
        """_summary_

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
                self.socket.sendall(msg + self._termination_as_bytes)
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
            self.close_connection()

        return result

    #----------------------------------------------------------------------------------------------

    @staticmethod
    def calculate_checksum(data: bytes):
        """Calculates the checksum for transmissions to the NCD serial-to-I2C
        adapter. (https://ncd.io/serial-to-i2c-conversion/)
        Checksum = Sum of all the bytes inside "data" and then limit to lower 8 bits.
        """
        return sum(data) & 0xFF


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    _log.info("Test synchronus receive (10s timeout):")
    c = Eth2GPIODevice("192.168.69.77:9002")

    r = c.request(bytes([0x57, 1, 0, 17]), timeout=5, encoding=False)

    print("RESULT:", r.replace("\r", "\n"))
    #_log.info(r)

    #_log.info("Test asynchronus receive (CRTL-C or scan to stop):")
    #asyncio.run(test_async_request())

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")


# END OF FILE
