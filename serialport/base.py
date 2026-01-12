import asyncio
import atexit
import serial_asyncio
import serial
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

class SerialComportDevice(object):

    def __init__(self, resource_str: str, termination: str | Tuple[str, str] | List[str] = "\r\n", trim_termination: bool = True, xonxff: bool = False) -> None:
        """Serial line communication the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{portname},{baudrate},{line settings in the form 8N1}'
            termination (str | Tuple[str, str], optional): Defines the line termination for both directions if string otherwise
                if tuple first is termination for send and second for receive. Defaults to '\r\n'.
            trim_termination (bool, ooptional): If True the termination chars on incomming responses will be trimmed, otherwise unchanged. Defaults to True.
            xonxff (bool, optional): True enables Xon/Xoff handshake protocoll, False disables it. Defaults to False.

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
        _sar = resource_str.split(",")
        # [COMPORT],[BAUD],[LINE SETTINGS]
        if len(_sar) != 3:
            raise ValueError(f"Resource string for serial communication mismatch '{resource_str}' => {len([_sar])}, expected [COMPORT],[BAUD],[LINE SETTINGS]")
        _comport, _baud, _line = _sar
        self.comport = _comport
        self.baudrate = _baud
        self.xonxoff = xonxff
        self.linesettings = _line


    def __str__(self) -> str:
        return f"Serial comport device at {self.comport},{self.baudrate},{self.linesettings}"

    def __repr__(self) -> str:
        _t_str = f"S:{hexlify(self._send_termination_as_bytes).decode()},R:{hexlify(self._receive_termination_as_bytes).decode()}" if self._send_termination != self._receive_termination else hexlify(self._send_termination_as_bytes).decode()
        return f"SerialComportDevice({self._resource_str}, termination='{_t_str}', trim_termination={self.trim_termination})"


    #----------------------------------------------------------------------------------------------


    def send(self, msg: str,
             timeout: float = 3.0,
             pause_after_write: int | None = None,
             encoding: str | None = "utf-8") -> None:
        """Sends a message to a socket device.

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.

            encoding (str, optional): will be passed to write() function.

        Returns:
            bool: _description_
        """

        _s = serial.Serial(self.comport, self.baudrate, xonxoff=self.xonxoff,
                            bytesize=int(self.linesettings[0]), parity=self.linesettings[1], stopbits=int(self.linesettings[2]),
                            timeout=timeout)
        try:
            _s.write(bytes(msg, encoding) + self._send_termination_as_bytes)
            if pause_after_write:
                time.sleep(pause_after_write/1000)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        finally:
            _s.close()


    #----------------------------------------------------------------------------------------------


    def request(self, msg: str | None,
                timeout: float | None = 3.0,
                pause_after_write: int | None = None,
                limit: int = 0,
                encoding: str | None = "utf-8") -> str:
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

        Returns:
            str: _description_
        """
        global DEBUG

        _log = getLogger(__name__, DEBUG)
        _s = serial.Serial(self.comport, self.baudrate, xonxoff=self.xonxoff,
                           bytesize=int(self.linesettings[0]), parity=self.linesettings[1], stopbits=int(self.linesettings[2]),
                           timeout=timeout)
        try:
            if msg:
                _s.write(bytes(msg, encoding) + self._send_termination_as_bytes)
                if pause_after_write:
                    time.sleep(pause_after_write/1000)
            # now read data until termination or timeout
            rcvdata = b""
            while True:
                _chunk = _s.read()  # do NOT specify a size, otherwise timeout does not fire!
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
            _s.close()
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
            elif isinstance(limit, (bytes, bytearray)):
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
        reader, writer = await serial_asyncio.open_serial_connection(url=self.comport, baudrate=self.baudrate, xonxoff=self.xonxoff,
                                    bytesize=int(self.linesettings[0]), parity=self.linesettings[1], stopbits=int(self.linesettings[2]))

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


class SerialComportDevicePermanentlyOpen(SerialComportDevice):

    def __init__(self, resource_str: str,
                 termination: str | Tuple[str, str] | List[str] = "\r\n", #
                 trim_termination: bool = True,
                 xonxff: bool = False,
                 timeout: float = 3.0) -> None:
        """This version of the Seral communication class does NOT close the connection after any transmission.
        The user COULD manage the open/close but the class open automatically if not yet open on first transmission
        (send or request) and installs a closing exit handler by atexit module.

        Args:
            resource_str (str): _description_
            termination (str | Tuple[str, str] | List[str, str], optional): _description_. Defaults to "\r\n".
                if tuple or list first is send termination, second is receive termination.
            trim_termination (bool, optional): _description_. Defaults to True
            xonxff (bool, optional): _description_. Defaults to False.
            timeout (float, optional): _description_. Defaults to 3.0.
        """
        super().__init__(resource_str, termination, trim_termination, xonxff)
        self.timeout = timeout
        self._serial_instance: serial.Serial | None = None

    #------------------------------------------------------
    # these functions are context manager functions

    def __enter__(self):
        self.open()
        atexit.register(self.__exit__)
        return self

    def __exit__(self) -> None:
        self.close()

    #------------------------------------------------------
    # the user has to open and close the connection manually

    def open(self) -> None:
        self._serial_instance = serial.Serial(
            self.comport, self.baudrate, xonxoff=self.xonxoff,
            bytesize=int(self.linesettings[0]),
            parity=self.linesettings[1],
            stopbits=int(self.linesettings[2]),
            timeout=self.timeout)

    def close(self) -> None:
        if self._serial_instance and self._serial_instance.is_open:
            self._serial_instance.close()


    #----------------------------------------------------------------------------------------------

    def send(self, msg: str,
             timeout: float = 3.0,
             pause_after_write: int | None = None,
             encoding: str | None = "utf-8") -> None:
        """Sends a message to a socket device.

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.

            encoding (str, optional): will be passed to write() function.

        Returns:
            bool: _description_
        """

        # make sure the serial instance is opened
        if self._serial_instance is None or not self._serial_instance.is_open:
            self.open()
        # update the timeout if changed
        if self._serial_instance.timeout != timeout:
            self._serial_instance.timeout = timeout

        try:
            self._serial_instance.write(bytes(msg, encoding) + self._send_termination_as_bytes)
            if pause_after_write:
                time.sleep(pause_after_write/1000)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        finally:
            # do NOT close the serial instance here
            pass


    #----------------------------------------------------------------------------------------------


    def request(self, msg: str | None,
                timeout: float | None = 3.0,
                pause_after_write: int | None = None,
                limit: int = 0,
                encoding: str | None = "utf-8") -> str:
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

        Returns:
            str: _description_
        """
        global DEBUG

        _log = getLogger(__name__, DEBUG)

         # make sure the serial instance is opened
        if self._serial_instance is None or not self._serial_instance.is_open:
            self.open()
        # update the timeout if changed
        if self._serial_instance.timeout != timeout:
            self._serial_instance.timeout = timeout

        try:
            if msg:
                self._serial_instance.write(bytes(msg, encoding) + self._send_termination_as_bytes)
                if pause_after_write:
                    time.sleep(pause_after_write/1000)
            # now read data until termination or timeout
            rcvdata = b""
            while True:
                _chunk = self._serial_instance.read()  # do NOT specify a size, otherwise timeout does not fire!
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
            # do NOT close the serial instance here
            pass

        return result



#--------------------------------------------------------------------------------------------------

async def test_async_request() -> None:
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    c = SerialComportDevice("COM24,9600,8N1", termination="\r")
    r = await c.request_async(None)
    _log.info(r)


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    # _log.info("Test synchronus receive (10s timeout):")
    # c = SerialComportDevice("COM24,9600,8N1", termination="\r")
    # r = c.request(None, timeout=10)
    # _log.info(r)

    _log.info("Test asynchronus receive (CRTL-C or scan to stop):")
    asyncio.run(test_async_request())

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")


# END OF FILE