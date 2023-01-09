"""
Provides basic ETH to SERIAL conversion handling the visa communication.
"""
from pyvisa import ResourceManager

DEBUG = 0

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
class Eth2SerialVisaDevice(object):

    def __init__(self, name_ip: str, channel: int | None):
        """
        Initialize the object with visa IP name.
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            host (str): visa IP name
        """
        self.rm = ResourceManager()          # auto decision for backend
        self.host = str(name_ip)
        if (channel != None):
            self.channel = int(channel)

    def send(self, msg: str, timeout: float = 1000) -> None:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.

        Returns:
            bool: _description_
        """
        try:
            self.session = self.rm.open_resource(self.host)            
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
            self.session.timeout = timeout
            # In case of use without channel separation
            chn = ""
            if (self.channel != None):
                chn = "CHAN " + str(self.channel) + ";"
            self.session.write(chn + msg)
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        except Exception as ex:
            _log.exception(ex)
            raise
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
        try:
            self.session = self.rm.open_resource(self.host)            
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
            self.session.timeout = timeout
            # In case of use without channel separation
            chn = ""
            if (self.channel != None):
                chn = "CHAN " + str(self.channel) + ";"
            result = self.session.query(chn + msg)
            _log.debug(f"Received: {result!r}")
        except TimeoutError as ex:
            # do NOT log, we need this exception being quiet when polling
            raise
        except Exception as ex:
            _log.exception(ex)
            raise
        finally:
            self.session.close()
        return result

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    DEBUG = 1

    tic = perf_counter()
    _log.info("Own IP: %s", OWN_PRIMARY_IP)

    #c = Eth2SerialDevice("192.168.1.90", 23)
    #c.send("Hallo Welt!")

    # ...

    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")


# END OF FILE