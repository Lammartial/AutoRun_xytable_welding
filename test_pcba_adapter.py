#import unittest
from typing import Tuple
from time import sleep
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1
from rrc.relayboard_i2cio4r4xdpdt import RelayBoard4Relay4GPIO
from rrc.cell_voltage_simulation import CellVoltageSimulation
from rrc.calibration_storage import CalibrationStorage
from rrc.temperature_sts21 import STS21
from rrc.barcode_scanner import create_barcode_scanner
from rrc.feasa import FEASA_CH9121
from rrc.itech import M3400

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

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

    
def psu_test(bat: BQ40Z50R1, gpio: RelayBoard4Relay4GPIO, psu: M3400) -> None:

    print("Voltage slew rates:")
    print(psu.request("VOLTAGE:SLEW:NEG?"))
    print(psu.request("VOLTAGE:SLEW:POS?"))
    print("Current slew rates:")
    print(psu.request("CURRENT:SLEW:NEG?"))
    print(psu.request("CURRENT:SLEW:POS?"))

    # Device need to be configured for CV mode to change V slopes
    #psu.configure_voltage_rise_times(pos="MIN", neg="MIN")
    #print(psu.read_system_error())
    #print("Voltage slew rates:")
    #print(psu.request("VOLTAGE:SLEW:NEG?"))
    #print(psu.request("VOLTAGE:SLEW:POS?"))
    
    psu.set_output_state(0)
    print("PSU", psu.get_all_measurements())    
    psu_print_error_queue(psu)

    # check PSU charge mode
    print("PSU Output on")
    psu.configure_supply(10.8, 0.08, 10, 1)
    #psu.configure_cc_mode(0.3, 6.9*1.15, 6.9*0.80, 50, 1)
    print("PSU", psu.get_all_measurements())
    psu_print_error_queue(psu)
    sleep(1)
    print("PSU", psu.get_all_measurements())
    #print("PSU Output off")
    #psu.send(f"CURRENT:LIM:NEG 0.00")
    #psu.send(f"CURRENT:LIM:POS 0.00")
    #psu.send(f"CURR 0.0")
    #psu.send(f"VOLT 0.0")
    
    #psu.send(f"VOLTAGE:LIM:LOW 13.00")
    #psu.send(f"VOLTAGE:LIM:HIGH 13.00")
    psu.set_output_state(0)

    # #psu.configure_charge_mode(0.25, 12.55, 10.0, 50, 1)
    # psu.configure_supply(12.6, 0.7, 50, 1)
    # psu_print_error_queue(psu)
    # print("PSU", psu.get_all_measurements())
    # sleep(1)
    # print("PSU", psu.get_all_measurements())
    # #print("PSU Output off")
    # psu.set_output_state(0)
    # sleep(0.5)
    # psu.configure_sink(-0.3, 5.0, 5.0, 12.6, 1.0, 1)
    # psu_print_error_queue(psu)
    # sleep(1)
    # print("PSU", psu.get_all_measurements())
    # print("PSU Output off")
    # psu.set_output_state(0)

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


def rack_test(bat: BQ40Z50R1, gpio: RelayBoard4Relay4GPIO, 
              vsim: CellVoltageSimulation, calib: CalibrationStorage, 
              feasa: FEASA_CH9121, 
              psu1: M3400, psu2: M3400) -> None:
    #psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    #psu.configure_current_rise_times(pos="DEF", neg="DEF")
    
    # verify that PSU does not trigger battery protection
    print("PSU Output on")
    psu2.configure_supply(10.8, 0.080, 50, 1)
    #su.configure_cc_mode(0.05, 10.8*1.15, (10.8*1.15) * 0.8, 50, 1)

    sleep(1.5)  # wait PSU powered up
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    #print("Safety Status:", bat.get_safety_status())
    #print("Safety Status details:", bat._safety_status)
    #print("PSU Output off")
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    vsim.set_cell_n_voltage(4, 3.6)
    
    psu1.configure_supply(10.8, 0.080, 50, 1)
    sleep(1.5)
    print("PSU1", psu1.get_all_measurements())

    print(bat.isReady())
    print(bat.current())
    
    print("Test LEDs ON")
    print(bat.set_led_onoff(1))
    print(bat.set_led_display(1))

    print("Issue capture command...")
    print(feasa.capture_pwm())
    # "getRGBI##" command
    print("getRGBI##0")
    print(feasa.get_rgbi_num(0))
    print("getRGBI##3")
    print(feasa.get_rgbi_num(3))

    print("Test LEDs OFF")
    print(bat.set_led_onoff(0))
    print(bat.set_led_display(0))
    
    print("Issue capture command...")
    print(feasa.capture_pwm())
    # "getRGBI##" command
    print("getRGBI##0")
    print(feasa.get_rgbi_num(0))
    print("getRGBI##3")
    print(feasa.get_rgbi_num(3))


    psu1.set_output_state(0)
    psu2.set_output_state(0)
    vsim.initialize()


def test_feasa_only(feasa: FEASA_CH9121):
    print("Issue capture command...")
    print(feasa.capture_pwm())
    # "getRGBI##" command
    print("getRGBI##0")
    print(feasa.get_rgbi_num(0))
    print("getRGBI##3")
    print(feasa.get_rgbi_num(3))


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    #LINE_NETWORK = "172.25.101"  # VN line 1
    LINE_NETWORK = "172.21.101"  # HOM Warehouse

    feasa = FEASA_CH9121(f"{LINE_NETWORK}.31:3000")  # PCBA test, socket 0
    #feasa = FEASA_CH9121(f"{LINE_NETWORK}.33:3000")  # PCBA test, socket 1
    #feasa = FEASA_CH9121(f"{LINE_NETWORK}.35:3000")  # PCBA test, socket 2

    #test_feasa_only(feasa)
    #exit()

    i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101") # socket 0
    #i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101") # socket 1
    #i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101") # socket 2

    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())

    calib = CalibrationStorage(I2CMuxedBus(i2cbus, mux, 1))
    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 2), retry_limit=7, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)
    gpio = RelayBoard4Relay4GPIO(I2CMuxedBus(i2cbus, mux, 3))
    vsim = CellVoltageSimulation(I2CMuxedBus(i2cbus, mux, 4))
    vsim.initialize()

    #sleep(0.5)
    psu1 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=1)  # socket 0, 1, and 2 share
    psu2 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=2)  # socket 0, 1, and 2 share
    #psu1 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=3)
    #psu2 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=4)
    #psu1 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=5)
    #psu2 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=6)
    psu1.set_output_state(0)
    psu2.set_output_state(0)

    
    #psu_test(bat, gpio, psu2)
    #psu_test(bat, gpio, psu1)
    rack_test(bat, gpio, vsim, calib, feasa, psu1, psu2)
    

# END OF FILE
