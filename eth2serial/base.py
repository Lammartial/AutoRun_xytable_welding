"""
Provides basic ETH to SERIAL conversion handling the socket communication.
"""
import socket

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

class Eth2SerialDevice(object):

    def __init__(self, host: str, port: int, termination: str = "\r\n"):
        """Initialize the object with IP address and port number.

        Args:
            host (str): hostname or IPv4 address
            port (int): port to use for communication
        """

        self.termination = termination
        self._termination_as_bytes = bytes(termination, "utf-8")  # need them also as bytes
        self.host = host
        self.port = port

    def send(self, msg: str, timeout: float = 1.0) -> bool:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 1.0.

        Returns:
            bool: _description_
        """

        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _s.settimeout(timeout)
            _s.connect((self.host, self.port))
            _s.sendall(bytes(msg, "utf-8") + self._termination_as_bytes)
            result = True
        except Exception as ex:
            result = ex  # could not send
        finally:
            _s.close()
        return result

    def request(self, msg: str, timeout: float = 5.0, limit: int = 0, decode: str = "ascii") -> str:
        """_summary_

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 5.0.
            limit (int, optional): _description_. Defaults to 0.

        Returns:
            str: _description_
        """

        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _s.settimeout(timeout)
            _s.connect((self.host, self.port))
            if len(msg)>0:
                _s.sendall(bytes(msg, "utf-8") + self._termination_as_bytes)
            # now read data until termination or timeout
            #rcvdata = b""
            #while True:
            #    _chunk = _s.recv(4096)
            #    if not _chunk:
            #        break
            #    rcvdata += _chunk
            #    if limit and len(rcvdata > limit):
            #        rcvdata = rcvdata[:limit]  # slice the received data
            #        break
            #
            rcvdata = _s.recv(4096)
            result = rcvdata.decode(decode) if len(rcvdata)>0 else None
            _log.debug(f"Received: {result!r}")
        except Exception as ex:
            result = ex
        finally:
            _s.close()
        return result
#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    DEBUG = 1

    tic = perf_counter()
    _log.info("Own IP: %s", OWN_PRIMARY_IP)

    c = Eth2SerialDevice("192.168.1.90", 23)
    c.send("Hallo Welt!")

    # ...

    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")


# END OF FILE
