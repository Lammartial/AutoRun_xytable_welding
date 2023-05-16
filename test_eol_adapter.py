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
from rrc.itech import M3400

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init


#--------------------------------------------------------------------------------------------------

def psu_print_error_queue(psu) -> None:
    last_error = None
    n = 0
    empty = False
    while not empty:
        last_error = psu.read_system_error()
        if last_error[0] == 0:
            empty = True
        else:
            n += 1
        print(last_error)
    print(f"Found number of errors: {n}")


#--------------------------------------------------------------------------------------------------

def psu_test(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3400) -> None:

    print("INP2", gpio.read_input(2))    
    print("Test PSU:")

    psu_print_error_queue(psu)

    print("Voltage slew rates:")
    print(psu.request("VOLTAGE:SLEW:NEG?"))
    print(psu.request("VOLTAGE:SLEW:POS?"))
    print("Current slew rates:")
    print(psu.request("CURRENT:SLEW:NEG?"))
    print(psu.request("CURRENT:SLEW:POS?"))

    #psu.configure_supply(12.55, 1.0, 50, set_output=1)
    psu.configure_cc_mode(1.0, 5.0, 10.8, 1, 100, set_output=1)
    sleep(1.5)
    print("supply", psu.get_all_measurements())    
    psu_print_error_queue(psu)
    print(bat.current())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)

    # for i in range(10):
    #     print(bat.isReady())
    #     sleep(0.5)
    #print(bat.battery_status())
    #print(bat.device_name())

    psu.set_output_state(0) 

    psu.configure_sink(-2.0, 5.0, -2.0*1.1, 10.8, -100, 1)
    sleep(1.5)
    print("sink", psu.get_all_measurements())
    psu_print_error_queue(psu)
    print(bat.current())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)


    psu.set_output_state(0) 


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.21.101"  # HOM Warehouse

    i2cbus = I2CPort(f"{LINE_NETWORK}.50:2101") # socket 0
   
    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())    

    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)
    
    temp = STS21(I2CMuxedBus(i2cbus, mux, 3))
    print(temp.start_measurement_no_hold())

    print("nothing")
    for i in range(1):
        print(bat.isReady())
        sleep(0.5)
        #print(bat.battery_status())
        #print(bat.device_name())

    # print("switch SENSE")
    gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))
    
    # for i in range(50):
    #     gpio.switch_to_battery_tester_measurement()
    #     sleep(5)
    #     gpio.switch_to_psu_measurement()
    #     sleep(5)
    #     print("INP2", gpio.read_input(2))
    #     sleep(0.5)
    # exit(1)

    gpio.switch_to_psu_measurement()
    
    psu = M3400(f"TCPIP0::{LINE_NETWORK}.51::inst0::INSTR")
        
    psu_test(bat, gpio, psu)

# END OF FILE
