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
class Eth2SerialVisaDevice(object):

    def __init__(self, resource_str: str, dev_channel: int):
        """
        Initialize the object with visa resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
        """
        self.rm = ResourceManager()          # auto decision for backend
        self.resource_str = str(resource_str)
        self.dev_channel = int(dev_channel)

    def __str__(self) -> str:
        return f"ETH to VISA bridge at {self.resource_str}:{self.dev_channel}"

    def __repr__(self) -> str:
        return f"Eth2SerialVisaDevice({self.resource_str}, {self.dev_channel})"

    #----------------------------------------------------------------------------------------------

    def send(self, msg: str, timeout: int = 1500, retries: int = 3) -> None:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): Timeout to wait for send complete in milliseconds. Defaults to 1500ms

        Returns:
            bool: _description_
        """
        session = None
        while retries:
            try:
                if not session:
                    session = self.rm.open_resource(self.resource_str)
                # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
                if session.resource_name.startswith('ASRL') or session.resource_name.endswith('SOCKET'):
                    session.read_termination = '\n'
                session.timeout = timeout
                if (self.dev_channel != 0):
                    #_chn = f"CHAN {self.dev_channel};"
                    #_cmd = ";".join([_chn + p for p in msg.split(";")])
                    _cmd = f"CHAN {self.dev_channel};{msg}"
                else:
                    _cmd = msg
                session.write(_cmd)
                break
            except Exception:
                # two types of exceptions seen VisaIOError and TimeOutError ... 
                # do NOT log, we need this exception being quiet when polling
                retries -= 1
                if retries <= 0:
                    raise
                    # we have exception handler to log this install in custom_logging
                    # except Exception as ex:
                    #     _log.exception(ex)
                    #     raise
                sleep(0.05)
            finally:
                if session:
                    session.close()


    def request(self, msg: str, timeout: int = 3000, retries: int = 3) -> str:
        """_summary_

        Args:
            msg (str): _description_
            timeout (int, optional):  Timeout to wait for send and receive result in milliseconds. Defaults to 3000.
            retries (int, optional): _description_. Defaults to 3.

        Returns:
            str: result
        """

        _log = getLogger(__name__, DEBUG)
        session = None
        while retries:
            try:
                if not session:
                    session = self.rm.open_resource(self.resource_str)
                # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
                if session.resource_name.startswith('ASRL') or session.resource_name.endswith('SOCKET'):
                    session.read_termination = '\n'
                session.timeout = timeout
                if (self.dev_channel != 0):
                    #_chn = f"CHAN {self.dev_channel};"
                    #_query = ";".join([_chn + p for p in msg.split(";")])
                    _query = f"CHAN {self.dev_channel};{msg}"
                else:
                    _query = msg
                session.write(_query)
                sleep(0.010)
                result = session.read().strip()
                #result = session.query(_query).strip()
                _log.debug(f"Received: {result!r}")
                break
            except Exception:
                # two types of exceptions seen VisaIOError and TimeOutError ...
                # do NOT log, we need this exception being quiet when polling
                retries -= 1
                if retries <= 0:
                    raise
                # we have exception handler to log this install in custom_logging
                # except Exception as ex:
                #     _log.exception(ex)
                #     raise
                sleep(0.05)
            finally:
                if session:
                    session.close()
        return result

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
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