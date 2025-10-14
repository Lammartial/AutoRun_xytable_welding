import socket
from datetime import datetime, timedelta
from rrc.eth2serial.base import Eth2SerialDevice, get_ipv4


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



class Eth2SerialSimulationDevice(Eth2SerialDevice):

    def __init__(self, resource_str: str,
                 termination: str = "\r\n",
                 open_connection: bool = True,
                 pause_on_retry: int | None = 10,
                 simulated_requests: dict = None,
                 simulated_incomming: list = None,
                 ):
        """Initializes an simulation object, which is able to send either a given sample response list in dedicated intervals
        or send prepared answers on given requests, based on a given dictionary.

        Args:
            resource_str (str): String of url form '{hostname or IPv4 address}:{port number}'
            termination (str, optional): Defines the line termination. Defaults to '\r\n'
            open_connection (bool, optional): If True, the connection is opened once on creation and never actively closed.
                If False, the connection is opened on each send/request. Defaults to True.
            pause_on_retry (int, optional): If retries is > 1 on send/request, the pause in milliseconds is held before next try. Defaults to 10.

        """

        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
        self.simulated_requests = simulated_requests
        self.simulated_incomming = simulated_incomming
        self.incomming_index = 0
        self.last_incomming_ts = datetime.now()  # this ensures that the first entry's time delay is depending on creation time
        self.socket = -1
        self.last_sent = None
        self.last_sent_ts = 0


    def __str__(self) -> str:
        return f"SIMULATION bridge"

    def __repr__(self) -> str:
        return f"Eth2SerielSimulationDevice('no_host:no_port', termination='{self.termination}')"

    #----------------------------------------------------------------------------------------------


    def connect_socket(self, timeout: float | None = None) -> socket:
        self.socket = -1
        return self.socket


    def close_connection(self, force: bool = False) -> None:
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
             retries: int = 1) -> bool:
        """_summary_

        Args:
            msg (str): message string to send. Line teminator will be added.
            timeout (float, optional): _description_. Defaults to 1.0.
            encoding (str, optional): will be passed to write() function.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            bool: _description_
        """

        self.last_sent = msg
        self.last_sent_ts = datetime.now()
        return True

    #----------------------------------------------------------------------------------------------

    def _simultate_receive(self) -> str:
        received: str = None
        if self.last_sent and (self.last_sent in self.simulated_requests):
            received = self.simulated_requests[self.last_sent] + self.termination
            self.last_sent = None
            return received

        # scheduled messages
        _td = (datetime.now() - self.last_incomming_ts)
        _dt_ms = _td / timedelta(milliseconds=1)
        _delay, _incomming_msg = self.simulated_incomming[self.incomming_index]
        if (_dt_ms > _delay):
            self.last_incomming_ts = datetime.now()
            # pause reached, send the entry if any
            if _incomming_msg:
                received = _incomming_msg + self.termination
            # proceed to next
            self.incomming_index += 1
            if self.incomming_index >= len(self.simulated_incomming):
                self.incomming_index = 0  # round robin
        return received

    #----------------------------------------------------------------------------------------------

    def request(self, msg: str | None,
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

        if msg:
            if msg not in self.simulated_requests:
                raise ValueError(f"{msg} is not mapped in simulated_requests.")
            result = self.simulated_requests[msg]
        else:
            # we use the incomming simulation which gives us timed round robin messages
            result = self._simultate_receive()
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

        return self.request(message, limit=limit, encoding=encoding)


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    _log.info("Own IP: %s", get_ipv4())

    _log.info("Simulate receive of bytes with given list")
    c = Eth2SerialSimulationDevice(None,
        simulated_requests={
            "*idn?": "HALLO WELT!",
        },
        simulated_incomming=[
            (3000, None),   # Pause
            (2000, "1CELL1234567890"),
            (2000, "1PCBA1234567890"),
            (2000, "SCHROTT"),
        ],
        termination="\n")

    r = c.request("*idn?", timeout=20)

    print("RESULT:", r.replace("\r", "\n"))

    while True:
        _incomming = c.request(None)
        if _incomming:
            print("INCOMMING:", _incomming)

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE
