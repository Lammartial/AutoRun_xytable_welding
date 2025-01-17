import asyncio
import serial_asyncio
import serial

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


#--------------------------------------------------------------------------------------------------

class SerialComportDevice(object):

    def __init__(self, resource_str: str, termination: str = "\r\n", trim_termination: bool = False, xonxff: bool = False) -> None:
        """Serial line communication the object with IP address and port number given by URL style resource string.

        Args:
            resource_str (str): String of url form '{portname},{baudrate},{line settings in the form 8N1}'
            termination (str, optional): Defines the line termination. Defaults to '\r\n'
            trim_termination (bool, ooptional): If True the termination chars on incomming responses will be trimmed, otherwise unchanged. Defaults to False.
            xonxff (bool, optional): True enables Xon/Xoff handshake protocoll, False disables it. Defaults to False.

        """
        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
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
        # self.bytesize = int(_line[0])
        # self.parity = int(_line[1])
        # self.stopbits = int(_line[2])

    def __str__(self) -> str:
        return f"Serial comport device at {self.comport},{self.baudrate},{self.linesettings}"

    def __repr__(self) -> str:
        return f"SerialComportDevice({self._resource_str}, termination={self.termination})"

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

        _s = serial.Serial(self.comport, self.baudrate, xonxoff=self.xonxoff,
                            bytesize=int(self.linesettings[0]), parity=self.linesettings[1], stopbits=int(self.linesettings[2]),
                            timeout=timeout)
        try:
            _s.write(bytes(msg, encoding) + self._termination_as_bytes)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
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
        _s = serial.Serial(self.comport, self.baudrate, xonxoff=self.xonxoff,
                           bytesize=int(self.linesettings[0]), parity=self.linesettings[1], stopbits=int(self.linesettings[2]),
                           timeout=timeout)
        try:
            if msg:
                _s.write(bytes(msg, encoding) + self._termination_as_bytes)
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
                if (rcvdata.rfind(self._termination_as_bytes) >= 0):
                    break
            if self.trim_termination:
                _t = rcvdata.rfind(self._termination_as_bytes)
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
async def test_async_request():
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