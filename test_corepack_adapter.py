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
from rrc.barcode_scanner import create_barcode_scanner
from rrc.feasa import FEASA_CH9121
from rrc.hioki import Hioki_BT3561A
from rrc.itech import M3900

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    i2cbus = I2CPort("172.25.101.40:2101") # socket 0
    #i2cbus = I2CPort("172.25.101.42:2101") # socket 1

    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())

    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))
    # for i in range(50):
    #     gpio.switch_to_battery_tester_measurement()
    #     sleep(5)
    #     gpio.switch_to_psu_measurement()
    #     sleep(5)
    #     print("INP2", gpio.read_input(2))
    #     sleep(0.5)
    gpio.switch_to_psu_measurement()
    #gpio.switch_to_battery_tester_measurement()
    sleep(1)
    # temp = STS21(I2CMuxedBus(i2cbus, mux, 3))
    # print(temp.start_measurement_no_hold())

    # print("test scanner, please do a UDI scan:")
    # try:
    #     dev = create_barcode_scanner("172.25.101.41:2000")
    #     s = dev.request(None, timeout=20.5)
    #     print(s)
    # except TimeoutError:
    #     print("Timeout!")

    print("test psu:")
    psu = M3900("TCPIP0::172.25.101.46::inst0::INSTR")
    psu.initialize_device()

    #psu.configure_supply(12.55, 2.0, 50, set_output=1)
    #sleep(1)
    #print("supply", psu.get_all_measurements())    
    #psu.set_output_state(0)    
    sleep(1)
    psu.configure_charge_mode(2.0, 12.55, 12.55, 50, True)    
    sleep(1)
    print("chargemode", psu.get_all_measurements())    
    psu.set_output_state(0)    
    pass

    # print("test Hioki bt:")
    # bt = Hioki_BT3561A("172.25.101.44:23", termination="\r\n")
    # print(bt.self_test())
    # print(bt.init())

    # gpio.switch_to_battery_tester_measurement()
    # print("test FEASA:")
    # led = FEASA_CH9121("172.25.101.41:3000", termination="\r\n")
    # for i in range(1):
    #     print("capture", i, led.capture_pwm())
    # print(led.get_rgbi_num(0))
    # gpio.switch_to_psu_measurement()

# END OF FILE
