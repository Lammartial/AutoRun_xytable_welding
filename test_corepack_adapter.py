#import unittest
from typing import Tuple
from time import sleep
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1
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
    bat = BQ40Z50R1(smbus)
    
    # print("nothing")
    # for i in range(4):
    #     print(bat.isReady())
    #     sleep(0.5)
    #     #print(bat.battery_status())
    #     #print(bat.device_name())

    gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))

    gpio.switch_to_psu_measurement()

    sleep(0.5)    

    psu = M3900("TCPIP0::172.25.101.46::inst0::INSTR")
    
    #print("PSU Output on")
    psu.configure_supply(12.0, 0.050, 50, 1)

    sleep(2.5)  # wakeup battery
    print("PSU", psu.get_all_measurements())

    print("PSU output off")
    #psu.configure_supply(12.0, 0.001, 50, 0)
    psu.set_output_state(0)
    #psu.initialize_device()

    # psu.configure_supply(0.0, 0.0, 50, 0)

    sleep(2.5)
    
    print("PSU - sense connected", psu.get_all_measurements())

    
    sleep(1.0)

    gpio.switch_to_battery_tester_measurement()
    
    sleep(1.3)
    print("PSU - sense on BT", psu.get_all_measurements())
    
    bt = Hioki_BT3561A("172.25.101.44:23", termination="\r\n")
    sleep(0.7)

    bt.init()

    sleep(5.5)
    print(bt.set_resistance_range(0.1))
    print(bt.set_voltage_range(20))
    print(bt.set_autorange(0))

    for i in range(50):
        #gpio.switch_to_battery_tester_measurement()        
        sleep(0.25)
        a = bt.measure()
        print("HIOKI", type(a), a)
        #gpio.switch_to_psu_measurement()
        sleep(0.25)
        print("PSU", psu.get_all_measurements())
        #print("INP2", gpio.read_input(2))
        #sleep(0.5)


    # gpio.switch_to_psu_measurement()
    # #gpio.switch_to_battery_tester_measurement()
    # sleep(1)

    # print("sense")
    # for i in range(10):
    #     print(bat.isReady())
    #     sleep(0.5)
    #     #print(bat.battery_status())
    #     #print(bat.device_name())

    # # temp = STS21(I2CMuxedBus(i2cbus, mux, 3))
    # # print(temp.start_measurement_no_hold())

    # # print("test scanner, please do a UDI scan:")
    # # try:
    # #     dev = create_barcode_scanner("172.25.101.41:2000")
    # #     s = dev.request(None, timeout=20.5)
    # #     print(s)
    # # except TimeoutError:
    # #     print("Timeout!")

    # print("test psu:")
   

    # #psu.configure_supply(12.55, 2.0, 50, set_output=1)
    # #sleep(1)
    # #print("supply", psu.get_all_measurements())    
    # #psu.set_output_state(0)    
    # #sleep(1)
    # psu.configure_charge_mode(0.5, 12.55, 12.55, 50, True)
    # #psu.configure_supply(12.55, 0.05, 50, set_output=True)   
    # sleep(1.0)
    # print("chargemode", psu.get_all_measurements())    
    # psu.set_output_state(0)    
    

    # # print("test Hioki bt:")
    # # bt = Hioki_BT3561A("172.25.101.44:23", termination="\r\n")
    # # print(bt.self_test())
    # # print(bt.init())

    # # gpio.switch_to_battery_tester_measurement()
    # # print("test FEASA:")
    # # led = FEASA_CH9121("172.25.101.41:3000", termination="\r\n")
    # # for i in range(1):
    # #     print("capture", i, led.capture_pwm())
    # # print(led.get_rgbi_num(0))
    # # gpio.switch_to_psu_measurement()

    # for i in range(10):
    #     print(bat.isReady())
    #     sleep(0.5)
    #     #print(bat.battery_status())
    #     #print(bat.device_name())

# END OF FILE
