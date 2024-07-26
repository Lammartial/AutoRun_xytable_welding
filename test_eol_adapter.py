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

    gpio.switch_to_psu_measurement()
    sleep(0.75)
    print("INP2", gpio.read_input(2))

    print("Test PSU:")

    psu_print_error_queue(psu)

    print("Voltage slew rates:")
    print(psu.request("VOLTAGE:SLEW:NEG?"))
    print(psu.request("VOLTAGE:SLEW:POS?"))
    print("Current slew rates:")
    print(psu.request("CURRENT:SLEW:NEG?"))
    print(psu.request("CURRENT:SLEW:POS?"))


    # wakeup the battery by current
    #psu.configure_cc_mode(0.1, None, 10.8, 10.8*0.1, 50, set_output=1)
    psu.configure_supply(10.8, 0.1, 50, set_output=1)


    sleep(0.75)
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
    sleep(0.75)

    psu.configure_sink(-2.0, 5.0, -2.0*1.1, 10.8, -100, 1)
    sleep(1.5)
    print("sink", psu.get_all_measurements())
    psu_print_error_queue(psu)
    print(bat.current())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)


    psu.set_output_state(0)



def test_sha1_key_change(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3400):
    psu.configure_supply(10.8, 0.1, 50, set_output=1)

    #_old = decrypt("Tl9SBaHNYtJim7U4mx9UxWoMuZK0tXgLzNhg/GaY+giMH5nykWOFeuU9gkMNli0GMNWa8rS42IA9iXZUoNCI7yOT+YoDzIaURHVgpA9ShXU=", 7)
    #print(bat.change_authentication_key(_old))  # old
    _new = decrypt("CPPFqb90MIiM8T2FjVdV/w9kXEE8tIdPr0UCTGu+XHq5qwfV7V8W4Te5iLajWcIGUZXmyvr+IV+PAKc5sLDMHAvo4+FqD0ClJtKzN0ZTPPg=", 4)
    #print(bat.authenticate(_new))
    print(bat.change_authentication_key(_new))  # new
    #print(bat.authenticate(_new))

    #print(bat.change_authentication_key_cipher("Tl9SBaHNYtJim7U4mx9UxWoMuZK0tXgLzNhg/GaY+giMH5nykWOFeuU9gkMNli0GMNWa8rS42IA9iXZUoNCI7yOT+YoDzIaURHVgpA9ShXU=", 7))  # standard RRC
    print(bat.change_authentication_key_cipher("CPPFqb90MIiM8T2FjVdV/w9kXEE8tIdPr0UCTGu+XHq5qwfV7V8W4Te5iLajWcIGUZXmyvr+IV+PAKc5sLDMHAvo4+FqD0ClJtKzN0ZTPPg=", 4))  # new key
    

#--------------------------------------------------------------------------------------------------


def test_change_device_name(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3400):
    #psu.configure_supply(10.8, 0.1, 50, set_output=1)
    #psu.configure_cc_mode(-0.5,2.0,10.8,0,-50,1)
    psu.configure_cc_mode(+0.5,2.0,10.8,0,50,1) 
    print(bat.is_sealed())
    bat.enable_full_access()
    print(bat.read_device_name_block()) # original
    print(bat._maybe_hexlify(bat.read_flash_block_verified(0x4085, 21), True))  # original hex code
    bat.write_device_name_block("RRC2020B-HLM")
    print(bat.read_device_name_block())
    print(bat._maybe_hexlify(bat.read_flash_block_verified(0x4085, 21), True))  # hex code
    print("Check DeviceName():", bat.device_name())

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    #LINE_NETWORK = "172.25.101"  # VN line 1
    LINE_NETWORK = "172.25.102"  # VN line 2
    #LINE_NETWORK = "172.21.101"  # HOM Warehouse


    #_old = decrypt("Tl9SBaHNYtJim7U4mx9UxWoMuZK0tXgLzNhg/GaY+giMH5nykWOFeuU9gkMNli0GMNWa8rS42IA9iXZUoNCI7yOT+YoDzIaURHVgpA9ShXU=", 7)
    #_new = decrypt("CPPFqb90MIiM8T2FjVdV/w9kXEE8tIdPr0UCTGu+XHq5qwfV7V8W4Te5iLajWcIGUZXmyvr+IV+PAKc5sLDMHAvo4+FqD0ClJtKzN0ZTPPg=", 4)
    #print(_old, _new)
    #exit()

    i2cbus = I2CPort(f"{LINE_NETWORK}.50:2101") # socket 0

    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())

    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus, pec=False)

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
    gpio.switch_to_psu_measurement()
    print("INP2", gpio.read_input(2))
    print(bat.isReady())
    #gpio.switch_to_battery_tester_measurement()
    #print(bat.isReady())

    # for i in range(50):
    #     gpio.switch_to_battery_tester_measurement()
    #     sleep(5)
    #     gpio.switch_to_psu_measurement()
    #     sleep(5)
    #     print("INP2", gpio.read_input(2))
    #     sleep(0.5)
    # exit(1)


    psu = M3400(f"{LINE_NETWORK}.51:30000")

    #psu_test(bat, gpio, psu)
    #test_sha1_key_change(bat, gpio, psu)
    test_change_device_name(bat, gpio, psu)

# END OF FILE
