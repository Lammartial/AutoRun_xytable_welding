from rrc.eth2serial.base import Eth2SerialDevice, OWN_PRIMARY_IP

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

class SCPIRemoteDevice(Eth2SerialDevice):

    def __init__(self, resource_str: str, termination: str = "\n"):
        super().__init__(resource_str, termination)

    def request(self, msg: str | None, timeout: float | None = 3, limit: int = 0, encoding: str | None = "utf-8") -> str:
        return super().request(msg, timeout, limit, encoding).replace(self.termination, "")


#--------------------------------------------------------------------------------------------------


def _request(dev: SCPIRemoteDevice, command: str):
    print(f"SEND  : {command}")
    r = dev.request(command, timeout=2)
    print(f"RESULT: {r}")

def test_scpi_standard(resource_str: str) -> None:
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    _log.info("TEST Standard SCPI commands.")
    c = SCPIRemoteDevice(resource_str=resource_str)
    _cmd_lst = [ "*idn?", "*help:smb"]
    for item in _cmd_lst:
        _request(c, item)

def test_scpi_specific(resource_str: str) -> None:
    global DEBUG

    _log = getLogger(__name__, DEBUG)
    _log.info("TEST Specific SCPI commands.")
    c = SCPIRemoteDevice(resource_str=resource_str)
    _cmd_lst = [":adc", ":can", ":help", ":i2c", ":io", ":pro", ":rs232",
                ":smb", ":scpi", ":spi", ":uut", "*help:i2c", "*help:smb", "*help:scpi"]
    for item in _cmd_lst:
        _request(c, item)



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()
    _log.info("Own IP: %s", OWN_PRIMARY_IP)

    RESOURCE_STRING = "192.168.69.77:2222"

    test_scpi_standard(RESOURCE_STRING)
    test_scpi_specific(RESOURCE_STRING)

    toc = perf_counter()
    print(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE