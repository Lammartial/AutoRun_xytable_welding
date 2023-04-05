#import unittest
from typing import Tuple
from time import sleep
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.relayboard_i2c_corepack import CorePackRelayBoard
from rrc.temperature_sts21 import STS21

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    i2cbus = I2CPort("172.25.101.50:2101")  # socket 0

    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())

    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))
    for i in range(10):
        gpio.switch_to_battery_tester_measurement()
        sleep(0.5)
        gpio.switch_to_psu_measurement()
        sleep(0.5)

    temp = STS21(I2CMuxedBus(i2cbus, mux, 3))
    print(temp.start_measurement_no_hold())


# END OF FILE
