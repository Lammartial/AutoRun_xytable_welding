#import unittest
from typing import Tuple
from time import sleep
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster, BusMasterPetaPatch
from rrc.chipsets import BQ40Z50R1, PetaliteChipset
from rrc.relayboard_i2c_corepack import CorePackRelayBoard
from rrc.temperature_sts21 import STS21
from rrc.barcode_scanner import create_barcode_scanner
from rrc.feasa import FEASA_CH9121
from rrc.hioki import Hioki_BT3561A
from rrc.itech import M3900

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

def rack_test(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3900, bt: Hioki_BT3561A) -> None:
    psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    psu.configure_current_rise_times(pos="DEF", neg="DEF")

    gpio.switch_to_psu_measurement()
    sleep(0.5)
    psu.set_output_state(0)
    sleep(0.5)
    # verify that PSU does not trigger battery protection
    print("PSU Output on")
    #psu.configure_supply(12.0, 0.080, 50, 0)
    psu.configure_cc_mode(0.05, 10.8*1.15, (10.8*1.15) * 0.8, 50, 1)
    sleep(1.5)  # wakeup battery
    print(bat.current())
    print("PSU", psu.get_all_measurements())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)
    print("PSU Output off")
    psu.set_output_state(0)
    sleep(0.5)
    #print("RESET ERRORS", bat.reset_errors())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)
    print("PSU - sense connected", psu.get_all_measurements())

    bat.set_fet_control(True)


    print("Check HIOKI battery tester")
    gpio.switch_to_battery_tester_measurement()

    sleep(1.3)
    print("PSU - sense on BT", psu.get_all_measurements())

    # toggle Relay several times and check measurements
    for i in range(5):
        gpio.switch_to_battery_tester_measurement()
        sleep(0.5)
        a = bt.measure()
        print("HIOKI", type(a), a)
        gpio.switch_to_psu_measurement()
        sleep(0.5)
        print("PSU", psu.get_all_measurements())
        print("INP2", gpio.read_input(2))


def psu_test(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3900, psu2: M3900) -> None:

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


    gpio.switch_to_battery_tester_measurement()
    sleep(0.5)
    a = bt.measure()
    print("HIOKI", type(a), a)

    gpio.switch_to_psu_measurement()
    sleep(0.5)
    psu.set_output_state(0)
    print("PSU", psu.get_all_measurements())
    psu2.set_output_state(0)
    print("PSU2", psu2.get_all_measurements())

    # check PSU charge mode
    print("PSU Output on")
    #psu.configure_supply(12.0, 0.080, 50, 1)

    psu_print_error_queue(psu)

    #psu.send("VOLT 14.5")
    #psu.send("CURR 0.5")
    #psu.send("OUTP 1")
    psu.send("REM:SENS 0")
    print(psu.request("REMote:SENSe?"))
    print(psu.request("REMote:SENSe:STATE?"))
    psu2.send("REM:SENS 0")
    print(psu2.request("REMote:SENSe?"))
    print(psu2.request("REMote:SENSe:STATE?"))
    #psu.configure_cc_mode(0.3, 6.9*1.15, 6.9*0.80, 50, 1)
    psu_print_error_queue(psu)
    psu_print_error_queue(psu2)
    psu.configure_cc_mode(0.3, 15.5, 10.0, 50, 0)
    #psu.configure_supply(15.5, 0.3, 50, 0)
    psu.set_output_state(1)
    psu_print_error_queue(psu)
    #psu2.configure_supply(15.5, 0.3, 50, 0)
    psu2.configure_cc_mode(0.3, 15.5, 10.0, 50, 0)
    psu2.set_output_state(1)
    psu_print_error_queue(psu2)

    # Device need to be configured for CC mode to change I slopes
    #psu.configure_current_rise_times(pos="MIN", neg="MIN")
    #print(psu.read_system_error())
    #psu.set_output_state(1)

    #psu_print_error_queue(psu)
    sleep(1)
    print("PSU", psu.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    #print("PSU Output off")
    #psu.send(f"CURRENT:LIM:NEG 0.00")
    #psu.send(f"CURRENT:LIM:POS 0.00")
    #psu.send(f"CURR 0.0")
    #psu.send(f"VOLT 0.0")

    #psu.send(f"VOLTAGE:LIM:LOW 13.00")
    #psu.send(f"VOLTAGE:LIM:HIGH 13.00")
    psu.set_output_state(0)
    psu.initialize_device()

    psu.configure_charge_mode(0.25, 12.55, 10.0, 50, 1)
    psu_print_error_queue(psu)
    print("PSU", psu.get_all_measurements())
    sleep(1)
    print("PSU", psu.get_all_measurements())
    #print("PSU Output off")
    psu.set_output_state(0)
    sleep(0.5)
    psu.configure_discharge_mode(-1.501, 15.55, 4.0, -50, 1)
    psu_print_error_queue(psu)
    sleep(1)
    print("PSU", psu.get_all_measurements())
    psu.configure_discharge_mode(-2.000, 15.55, 4.0, -50, 1)
    psu_print_error_queue(psu)
    sleep(1)
    print("PSU", psu.get_all_measurements())
    print("PSU Output off")
    psu.set_output_state(0)

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


def relay_test(n: int, gpio: CorePackRelayBoard, psu: M3900, bt: Hioki_BT3561A) -> None:
    for i in range(n):
        gpio.switch_to_battery_tester_measurement()
        sleep(0.5)
        a = bt.measure()
        print("HIOKI", type(a), a)
        gpio.switch_to_psu_measurement()
        sleep(0.5)
        print("PSU", psu.get_all_measurements())
        print("INP2", gpio.read_input(2))


def spinel_test(bat: BQ40Z50R1, gpio: CorePackRelayBoard, psu: M3900, bt: Hioki_BT3561A) -> None:
    print("SPINEL TEST")

    gpio.switch_to_psu_measurement()
    sleep(0.5)
    psu.configure_supply(5.0, 1.0, 50.0, 1)
    print("PSU", psu.get_all_measurements())
    print("PSU Output off")
    psu.set_output_state(0)



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

    LINE_NETWORK = "172.21.101"  # HOM Warehouse
    #LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.25.102"  # VN line 2
    #LINE_NETWORK = "172.25.103"  # VN line 3

    SOCKET = 0  # 0 or 1

    if SOCKET == 0:
        i2cbus = I2CPort(f"{LINE_NETWORK}.40:2101") # socket 0
        scan = create_barcode_scanner(f"{LINE_NETWORK}.41:2000")
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.41:3000", termination="\n")
    if SOCKET == 1:
        i2cbus = I2CPort(f"{LINE_NETWORK}.42:2101") # socket 1
        scan = create_barcode_scanner(f"{LINE_NETWORK}.43:2000")
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.43:3000", termination="\n")

    #test_feasa_only(feasa)

    print("I2C Bus scan:", i2cbus.i2c_bus_scan())
    mux = BusMux(i2cbus, address=0x77)
    for i in range(8):
        mux.setChannel(i + 1)
        print("CH:", i, i2cbus.i2c_bus_scan())

    #temp = STS21(I2CMuxedBus(i2cbus, mux, 3), i2c_address_7bit="0x4A,64")  # hidden change from STS21 to SHT25 changed i2c address from 0x4A to 0x40
    #print(temp.start_measurement_no_hold())

    #smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    #bat = BQ40Z50R1(smbus)
    #smbus = BusMasterPetaPatch(I2CMuxedBus(i2cbus, mux, 1), retry_limit=3, verify_rounds=1, pause_us=50)    
    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=3, verify_rounds=1, pause_us=50)
    bat = PetaliteChipset(smbus, pec=True)
    gpio = CorePackRelayBoard(I2CMuxedBus(i2cbus, mux, 2))    
    gpio.switch_to_psu_measurement()
    sleep(0.5)

    
    if SOCKET == 0:
        psu = M3900(f"{LINE_NETWORK}.46:30000")  # socket 0
        #psu2 = M3900(f"{LINE_NETWORK}.46:30000")  # socket 1 for PSU test function
    if SOCKET == 1:
        psu = M3900(f"{LINE_NETWORK}.47:30000")  # socket 1

    psu.set_output_state(0)
    #psu.initialize_device()

    if 0:
        #psu.configure_sink(-0.04, 500, -0.08, 30.0, -5.0, 1)
        while True:
            voltage = psu.get_voltage_rounded(ndigits=3)
            print("PSU Voltage:", voltage)
            if voltage > 16.0:
                break
            sleep(0.5)
        print("Found a battery!!")
        exit()

    psu.set_sense_state(0)
    gpio.switch_to_battery_tester_measurement()
    sleep(0.5)

    print("INIT Hioki")
    if SOCKET == 0:
        bt = Hioki_BT3561A(f"{LINE_NETWORK}.44:23", termination="\r\n")  # socket 0
    if SOCKET == 1:
        bt = Hioki_BT3561A(f"{LINE_NETWORK}.45:23", termination="\r\n")  # socket 1
    bt.init()
    bt.set_autorange(0)
    bt.set_resistance_range(0.1)
    bt.set_voltage_range(30)
    
    #print(bt.measure())

    if 0:   
        n = 0
        while True:
            n += 1
            if n & 1 == 0:
                psu.set_sense_state(1)
                gpio.switch_to_psu_measurement()
                sleep(0.5)
                voltage = psu.get_voltage_rounded(ndigits=3)
                print("PSU Voltage:", voltage)
            else:
                psu.set_sense_state(0)
                gpio.switch_to_battery_tester_measurement()
                psu.clear_output_protection()
                sleep(0.5)
                impedance, voltage = bt.measure()
                print("Hioki Measurement:", impedance, voltage)        
            #sleep(0.5)

    if 0:
        #gpio.switch_to_psu_measurement()
        #sleep(0.5)
        #psu.configure_sink(-0.04, 500, -0.08, 30.0, -5.0, 1)
        while True:
            #v = psu.get_voltage_rounded(ndigits=3)
            impedance, voltage = bt.measure()
            print("Hioki Measurement:", impedance, voltage)
            #print("PSU Voltage:", v)
            if impedance < 0.100 and voltage > 16.0:
                break
            sleep(0.5)
        print("Found a battery!!")
        exit()

    gpio.switch_to_psu_measurement()
    psu.clear_output_protection()
    psu.set_sense_state(1)
    psu.configure_supply(26.0, 2.05, 80, 0)


    if 1:
        #gpio.switch_rrc3570_tpin_open()    
        gpio.switch_rrc3570_tpin_shorted()
        sleep(1.5)
        
        # for i in range(8):
        #     mux.setChannel(i + 1)
        #     print("CH:", i, i2cbus.i2c_bus_scan())

        print(bat.device_name())
        print(bat.is_sealed())
        print(bat.is_unsealed())
        bat.enable_full_access()
        print(bat.is_sealed())
        print(bat.is_unsealed())
        bat.operation_status()
        print(bat._operation_status)
        bat.manufacturing_status()
        print(bat._manufacturing_status)
        bat.manufacturing_daqstatus1()
        print(bat._manufacturing_daqstatus1)
        bat.manufacturing_daqstatus2()    
        print(bat._manufacturing_daqstatus2)
        
        bat.write_pcba_udi_block("0PCBA012345678901")
        print(bat.read_pcba_udi_block())

        
        # for i in range(30):
        #     print("Button:", bat.pushbutton_state())    
        #     sleep(1)


        for c in range(3, 0 - 1, -1):
            print("Set LED color code:", c)
            bat.set_led_onoff(c)
            sleep(2)
            print("Is LED on?", bat.is_led_on())        
        bat.set_led_onoff(0)
        

        bat.setup_rtc()
        sleep(3)
        print(bat.read_rtc())
        print(bat.check_rtc_against_systemtime())

        
        print(bat.voltage())
        print(bat.current())
        print(bat.temperature())
        print(bat.remaining_capacity())
        print(bat.full_charge_capacity())
        fcc, unit, name, _ = bat.full_charge_capacity() 
        dc, unit, name, _ = bat.design_capacity()
        print(fcc * 100 / dc)
        print(bat.soc())
        print(bat.cell1_voltage())     
        print(bat.cell2_voltage()) 
        print(bat.cell3_voltage()) 
        print(bat.cell4_voltage())
        print(bat.cell5_voltage()) 
        print(bat.cell6_voltage())
        print(bat.cell7_voltage())

        psu.set_output_state(0)
        exit()

    #relay_test(20, gpio, psu, bt)
    #psu_test(bat, gpio, psu, psu2)
    #rack_test(bat, gpio, psu, bt)
    #spinel_test(bat, gpio, psu, bt)

    _udi = scan.request(None, timeout=10, encoding="ascii")
    print(_udi)
    records = [s.split("\x1d") for s in _udi.split("\x04")[0].split("\x1e")]
    print(records)

    #Received: '[)>\x1e06\x1d\\0000261P110282-01\x1d30PSPINEL\x1d10D2305\x1dSSPIN01R1000063\x1e\x04\r\n'
    #[)>▲06↔\0000261P110282-01↔30PSPINEL↔10D2305↔SSPIN01R1000063▲♦
    #[['[)>'], ['06', '\\0000261P110282-01', '30PSPINEL', '10D2305', 'SSPIN01R1000063'], ['']]

# END OF FILE
