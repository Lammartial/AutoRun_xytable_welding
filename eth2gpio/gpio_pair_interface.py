from time import sleep
from struct import pack
from rrc.eth2gpio.base import Eth2GPIODevice, API_HEADER_BYTE


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


class RemoteGPIO(Eth2GPIODevice):

    def set_output(self, value: int | bool) -> bool:
        r = self.request(b'W' + bytes([1 if value else 0]), timeout=2.0, encoding=False)
        ok = (r[0] == API_HEADER_BYTE)
        return ok

    def get_input(self) -> int:
        r = c.request(b'R', timeout=2.0, encoding=False)
        if (r[0] != API_HEADER_BYTE):
            raise Exception(f"Could not get value for INPUT: {r|r}")
        return int(r[1])


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter
    from binascii import hexlify

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    _log.info("Test remote GPIO:")
    c = RemoteGPIO("192.168.69.77:9003")

    r = c.set_output(1)
    print(f"RESULT: {r}")
    r = c.get_input()
    print(f"RESULT: {r}")
    r = c.set_output(0)
    print(f"RESULT: {r}")
    r = c.get_input()
    print(f"RESULT: {r}")

    toc = perf_counter()
    print(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE