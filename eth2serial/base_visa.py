"""
Provides basic ETH to SERIAL conversion handling the visa communication.
"""
from pyvisa import ResourceManager

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



#--------------------------------------------------------------------------------------------------
class Eth2SerialVisaDevice(object):

    def __init__(self, resource_str: str, channel: int):
        """
        Initialize the object with visa resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
        """
        self.rm = ResourceManager()          # auto decision for backend
        self.resource_str = str(resource_str)
        self.channel = int(channel)

    def __str__(self) -> str:
        return f"ETH to VISA bridge at {self.resource_str}:{self.channel}"

    def __repr__(self) -> str:
        return f"Eth2SerialVisaDevice({self.resource_str}, {self.channel})"

    #----------------------------------------------------------------------------------------------

    def send(self, msg: str, timeout: float = 1000) -> None:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.

        Returns:
            bool: _description_
        """
        try:
            self.session = self.rm.open_resource(self.resource_str)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
            self.session.timeout = timeout
            # In case of use without channel separation
            chn = ""
            if (self.channel != 0):
                chn = "CHAN " + str(self.channel) + ";"
            self.session.write(chn + msg)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     _log.exception(ex)
        #     raise
        finally:
            self.session.close()

    def request(self, msg: str, timeout: float = 2000) -> str:
        """_summary_

        Args:
            msg (str): command
            timeout (float, optional): Defaults to 5.0.

        Returns:
            str: result
        """

        _log = getLogger(__name__, DEBUG)
        try:
            self.session = self.rm.open_resource(self.resource_str)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
            self.session.timeout = timeout
            # In case of use without channel separation
            chn = ""
            if (self.channel != 0):
                chn = "CHAN " + str(self.channel) + ";"
            result = self.session.query(chn + msg)
            _log.debug(f"Received: {result!r}")
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        # we have exception handler to log this install in custom_logging
        # except Exception as ex:
        #     _log.exception(ex)
        #     raise
        finally:
            self.session.close()
        return result

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    #_log.info("Own IP: %s", OWN_PRIMARY_IP)

    #c = Eth2SerialDevice("192.168.1.90", 23)
    #c.send("Hallo Welt!")

    # ...

    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")


# END OF FILE