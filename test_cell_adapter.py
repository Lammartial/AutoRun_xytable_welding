#import unittest
from typing import Tuple
from time import sleep
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1
from rrc.chipsets.cipher import decrypt
from rrc.relayboard_i2c_corepack import CorePackRelayBoard
from rrc.temperature_sts21 import STS21
from rrc.itech import M3400

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    #LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.25.102"  # VN line 2
    LINE_NETWORK = "172.21.101"  # HOM Warehouse


    i2cbus = I2CPort(f"{LINE_NETWORK}.20:2101") # socket 0

    mux = BusMux(i2cbus, address=0x77)
    print(i2cbus.i2c_bus_scan())

    # smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    # bat = BQ40Z50R1(smbus, pec=False)

    # temp = STS21(I2CMuxedBus(i2cbus, mux, 3))
    # print(temp.start_measurement_no_hold())

    # print("nothing")
    # for i in range(5):
    #     #print(bat.isReady())
    #     sleep(0.5)
    #     print(bat.battery_status())
    #     #print(bat.device_name())

    # # print("switch SENSE")
    # gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))
    # gpio.switch_to_psu_measurement()
    # print("INP2", gpio.read_input(2))
    # print(bat.isReady())
    # #gpio.switch_to_battery_tester_measurement()
    # #print(bat.isReady())

    # # for i in range(50):
    # #     gpio.switch_to_battery_tester_measurement()
    # #     sleep(5)
    # #     gpio.switch_to_psu_measurement()
    # #     sleep(5)
    # #     print("INP2", gpio.read_input(2))
    # #     sleep(0.5)
    # # exit(1)


    # psu = M3400(f"{LINE_NETWORK}.51:30000")

    # #psu_test(bat, gpio, psu)
    # #test_sha1_key_change(bat, gpio, psu)
    # test_change_device_name(bat, gpio, psu)

# END OF FILE
