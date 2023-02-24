"""
Provides basic ETH to SERIAL conversion handling the visa communication.
"""
from pyvisa import ResourceManager
from time import sleep

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 0
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #



#--------------------------------------------------------------------------------------------------
class AdhocVisaDevice(object):

    def __init__(self, resource_str: str, read_termination: str | None = None, write_termination: str | None = None, pause_on_retry: int | None = 10):
        """Initialize the object with visa resource string (IP name).
        
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
            read_termination (str | None, optional): If None, default setting of PyVISA is used. Defaults to None.
            write_termination (str | None, optional): If None, default setting of PyVISA is used. Defaults to None.
        """
        self.rm = ResourceManager()  # auto decision for backend
        self.resource_str = str(resource_str)
        self.read_termination = read_termination
        self.write_termination = write_termination
        self.pause_on_retry = None
        if pause_on_retry:
            self.pause_on_retry = pause_on_retry/1000
    
    def __str__(self) -> str:
        return f"VISA Device at {self.resource_str}"

    def __repr__(self) -> str:
        return f"AdhocVisaDevice({self.resource_str},read_termination={self.read_termination},write_termination={self.write_termination},pause_on_retry={self.pause_on_retry})"

    #----------------------------------------------------------------------------------------------

    def send(self, msg: str, pause_after_write: int | None = None, timeout: int = 1500, retries: int = 1) -> None:
        """_summary_

        Args:
            msg (str): _description_
            pause_after_write (int, optional):  Timeout after writing the command for a request in milliseconds, None disables it. Defaults to 10.
            timeout (float, optional): Timeout to wait for send complete in milliseconds. Defaults to 1500ms

        Returns:
            bool: _description_
        """
        session = None
        while retries > 0:
            try:
                if not session:
                    session = self.rm.open_resource(self.resource_str)
                if self.read_termination:
                    session.read_termination = self.read_termination
                if self.write_termination:
                    session.write_termination = self.write_termination
                session.timeout = timeout
                session.write(msg)
                if pause_after_write:
                    sleep(pause_after_write/1000)
                break
            except Exception:
                # two types of exceptions seen VisaIOError and TimeOutError ... 
                # do NOT log, we need this exception being quiet when polling
                retries -= 1
                if retries <= 0:
                    raise
                if self.pause_on_retry:
                    sleep(self.pause_on_retry)
            finally:
                if session:
                    session.close()
                    session = None


    def request(self, msg: str, pause_after_write: int | None = None, timeout: int = 3000, retries: int = 1) -> str:
        """_summary_

        Args:
            msg (str): _description_
            pause_after_write (int, optional):  Timeout after writing the command for a request in milliseconds, None disables it. Defaults to 10.
            timeout (int, optional):  Timeout to wait for send and receive result in milliseconds. Defaults to 3000.
            retries (int, optional): _description_. Defaults to 3.

        Returns:
            str: result
        """

        #_log = getLogger(__name__, DEBUG)
        session = None
        while retries > 0:
            try:
                if not session:
                    session = self.rm.open_resource(self.resource_str)
                if self.read_termination:
                    session.read_termination = self.read_termination
                if self.write_termination:
                    session.write_termination = self.write_termination
                session.write(msg)
                if pause_after_write:
                    sleep(pause_after_write/1000)
                result = session.read()
                #_log.debug(f"Received: {result!r}")
                break
            except Exception:
                # two types of exceptions seen VisaIOError and TimeOutError ...
                # do NOT log, we need this exception being quiet when polling
                retries -= 1
                if retries <= 0:
                    raise
                if self.pause_on_retry:
                    sleep(self.pause_on_retry)
            finally:
                if session:
                    session.close()
                    session = None
        return result


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    
    # ...

    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")


# END OF FILE