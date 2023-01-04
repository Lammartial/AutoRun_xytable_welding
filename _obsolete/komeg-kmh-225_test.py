from typing import Tuple
from time import sleep
from modbus.base import log_modbus_version
from komeg import Komeg225LTemperatureChamber

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
# Fixed Configuration
#
VERSION = "0.0.1"

#--------------------------------------------------------------------------------------------------

__version__ = VERSION

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    log_modbus_version()
    tic = perf_counter()

    PORT = "COM8"
    k = Komeg225LTemperatureChamber(f"rtu:{PORT}:38400,8E1", unit_address=0)

    print("0-10:", k.read(0, 9))
    print("22-28:", k.read(22, 6))
    print("36-39:", k.read(100, 4))
    print("43:", k.read(43, 1))
    print("100-101:", k.read(100, 2))

    k.set_temperature(-10)
    print(k.read_temperature())
    k.set_humidity(0)
    print(k.read_humidity())
    #k.write_coil(11, 1)  # AUTHORIZATION
    #k.write_coil(0, 1)  # RUN
    #k.write_coil(1, 1)  # STOP
    #k.start(wait_for_execution=True)
    #k.stop(wait_for_execution=True)
    #sleep(3.0)
    #print("_RUN_", k.read_coil(0))  # RUN
    #print("_STOP_", k.read_coil(1))  # STOP
    #print("_AUTH_", k.read_coil(11))  # STOP

    print(k.read_status())

    toc = perf_counter()
    print(f"Send in {toc - tic:0.4f} seconds")
    print("DONE.")
# END OF FILE