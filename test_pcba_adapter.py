#import unittest
from typing import Tuple
from time import sleep
from pathlib import Path
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1, BQStudioFileFlasher
from rrc.relayboard_i2cio4r4xdpdt import RelayBoard4Relay4GPIO
from rrc.cell_voltage_simulation import CellVoltageSimulation
from rrc.calibration_storage import CalibrationStorage
from rrc.temperature_sts21 import STS21
from rrc.barcode_scanner import create_barcode_scanner
from rrc.feasa import FEASA_CH9121
from rrc.itech import M3400
from rrc.keysight import DAQ970A

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
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:
    #psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    #psu.configure_current_rise_times(pos="DEF", neg="DEF")

    # verify that PSU does not trigger battery protection
    print("PSU Output on")
    psu1.configure_supply(10.8, 0.080, 50, 0)
    psu2.configure_supply(10.8, 0.080, 50, 0)
    #psu2.configure_cc_mode(0.05, 10.8*1.15, (10.8*1.15) * 0.8, 50, 1)

    sleep(1.5)  # wait PSU powered up
    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())
    #print("Safety Status:", bat.get_safety_status())
    #print("Safety Status details:", bat._safety_status)
    #print("PSU Output off")
    vsim.enable_all_cell_channels()
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    #vsim.set_cell_n_voltage(4, 3.6)

    #psu1.configure_supply(10.8, 0.080, 50, 1)
    psu2.set_output_state(1)
    sleep(0.5)
    psu1.set_output_state(1)
    sleep(2.0)
    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())

    print("DAQ - channel 11", daq.get_VDC(11))
    print("DAQ - channel 12", daq.get_VDC(12))
    print("DAQ - channel 14", daq.get_VDC(14))
    print("DAQ - channel 10", daq.get_VDC(10))
    print("DAQ - channel 15", daq.get_VDC(15))

    print(bat.waitForReady(timeout_ms=2000))  # this isued in wakeup
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


def psu_mode_test(bat: BQ40Z50R1, gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation, calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:
    #psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    #psu.configure_current_rise_times(pos="DEF", neg="DEF")

    # verify that PSU does not trigger battery protection
    print("PSU Output on")
    psu2.configure_supply(10.8, 2.4, 50, 1)
    sleep(1.0)  # wait PSU powered up
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    #print("Safety Status:", bat.get_safety_status())
    #print("Safety Status details:", bat._safety_status)
    #print("PSU Output off")
    vsim.enable_all_cell_channels()
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    psu1.configure_supply(10.8, 0.05, 50, 1)
    sleep(2.5)
    print(bat.isReady())
    psu1.set_output_state(0)
    psu1.configure_sink(-2.0, 5, -2,2, -80, 0)
    sleep(0.5)
    bat.reset_errors()
    bat.set_fet_control(False)
    bat.set_chg_fet(True)
    bat.set_dsg_fet(True)
    bat.operation_status()
    print(bat._operation_status)
    psu1.set_output_state(1)
    print("PSU1", psu1.get_all_measurements())


    psu1.set_output_state(0)
    psu2.set_output_state(0)
    vsim.initialize()

#--------------------------------------------------------------------------------------------------

def bat_flash_test(bat: BQ40Z50R1, psu1: M3400, psu2: M3400) -> None:
    from time import perf_counter, strftime, localtime

    print("PSU Output on")
    psu2.configure_supply(10.8, 0.1, 50, 1)
    sleep(1.0)  # wait PSU powered up
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    #print("Safety Status:", bat.get_safety_status())
    #print("Safety Status details:", bat._safety_status)
    #print("PSU Output off")
    vsim.enable_all_cell_channels()
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    psu1.configure_supply(10.8, 0.08, 50, 1)
    sleep(2.5)
    print(bat.isReady())
    psu1.set_output_state(0)
    sleep(0.5)

    filestore = Path("C:/Production/Battery-PCBA-Test/filestore")

    recover = BQStudioFileFlasher(bat, firmware_file=filestore / "SCD_3412036-02_B_Tansanit-B_RRC2040_Recovery.bq.fs", show_progressbar=True, test_socket=0)

    #flasher = BQStudioFileFlasher(bat, firmware_file=filestore / "BQFS_3411842-05_A_Ametrie_RRC2040-2S.bq.fs", show_progressbar=True, test_socket=0)
    # Need 63.0579 seconds @100kHz with OLIMEX
    # Need 59.1005 seconds @100kHz with NCD.io

    flasher = BQStudioFileFlasher(bat, firmware_file=filestore / "DFFS_3411842-05_A_Ametrie_RRC2040-2S.df.fs", show_progressbar=True, test_socket=0)
    # Need 13.0589 seconds @100kHz with OLIMEX
    # Need 13.1763 seconds @100kHz with NCD.io

    #flasher = BQStudioFileFlasher(bat, firmware_file=filestore / "SCD_3411863-05_A_Jade_RRC2054_BMS_Files.df.fs", show_progressbar=True, test_socket=0)
    #flasher = BQStudioFileFlasher(bat, firmware_file=filestore / "SCD_3411863-05_A_Jade_RRC2054_BMS_Files.bq.fs", show_progressbar=True, test_socket=0)

    tic = perf_counter()
    print(f"Start: {strftime('%H:%M:%S', localtime())}")

    #res = recover.recover_fw_file()
    res = flasher.program_fw_file()

    toc = perf_counter()
    print(f"Need {toc - tic:0.4f} seconds")
    print("FLASH:", res)


    psu1.set_output_state(0)
    psu2.set_output_state(0)
    vsim.initialize()



def bat_flash_test_debug(bat: BQ40Z50R1) -> None:
    from time import perf_counter, strftime, localtime

    #filestore = Path("C:/Production/Battery-PCBA-Test/filestore")
    filestore = Path("../../Battery-PCBA-Test/filestore")

    recover = BQStudioFileFlasher(bat, firmware_file=filestore / "SCD_3412036-02_B_Tansanit-B_RRC2040_Recovery.bq.fs", show_progressbar=True, test_socket=0)
    tic = perf_counter()
    print(f"Start: {strftime('%H:%M:%S', localtime())}")
    #res = recover.recover_fw_file()
    for i in range(0x4000, 0x6000, 32):
        #res = bat.read_flash_block(i)
        #data, ok = bat.readBlock(0x44)
        data = bat.bus.i2c.readfrom_mem(0x0b, 0x12, 32)
        print(len(data))
        #length = bat.bus.i2c.writeto(0x0b, data)
    res = True
    toc = perf_counter()
    print(f"Need {toc - tic:0.4f} seconds")
    print("FLASH:", res)



#--------------------------------------------------------------------------------------------------



def test_feasa_only(feasa: FEASA_CH9121):
    print("Issue capture command...")
    print(feasa.capture_pwm())
    # "getRGBI##" command
    print("getRGBI##0")
    print(feasa.get_rgbi_num(0))
    print("getRGBI##3")
    print(feasa.get_rgbi_num(3))

#--------------------------------------------------------------------------------------------------

def test_calibration_storage_only(calib: CalibrationStorage):
    print("Read calibration EEPROM values")
    print("Inventory Number: ", calib.load_inventory_number())
    print("Shunt Resistance: ", calib.load_shunt_resistance_ohm())
    [print(f"Leakage Current: {i}# {calib.load_leakcurrent_amps(i)}") for i in range(3)]


def test_relay_only(gpio: RelayBoard4Relay4GPIO):
    gpio.set_gpio_n_as_output(7)
    for i in range(3):
        gpio.set_gpio_n_high(7)
        sleep(0.5)
        gpio.set_gpio_n_low(7)
        sleep(0.5)



#--------------------------------------------------------------------------------------------------


def test_lvl2_heater(bat: BQ40Z50R1, gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation, calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:


    print("PSU Cell Output ON")
    psu2.configure_supply(10.8, 0.080, 50, 1)
    #psu2.configure_cc_mode(0.08, None, 10.8, 1.0, 50, 1)
    print("PSU Pack Output ON")
    psu1.configure_supply(10.8, 0.080, 50, 1)
    sleep(1.5)  # wait PSUs
    vsim.enable_all_cell_channels()
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    #vsim.set_cell_n_voltage(4, 3.6)

    print("PSU pack", psu1.get_all_measurements())
    print("PSU cell", psu2.get_all_measurements())
    #print("PSU Output off")

    gpio.disable_relay_n(1) # short-GND
    gpio.disable_relay_n(2) # 8.2kOhm-GND
    gpio.disable_relay_n(4) # Vaux

    print("Check battery:")
    if not bat.isReady():
        print("no battery found, stop test")
        psu2.set_output_state(0)
        vsim.power_down_all_cell_channels()
        return

    print("PSU Pack Output OFF")
    psu1.set_output_state(0)

    # # flash firmware
    # fp_filestore = Path("./Battery-PCBA-Test/filestore")
    # f1 = BQStudioFileFlasher(bat, fp_filestore / "BQFS_3411842-05_A_Ametrie_RRC2040-2S.bq.fs" )
    # f2 = BQStudioFileFlasher(bat, fp_filestore / "DFFS_3411842-05_A_Ametrie_RRC2040-2S.df.fs" )
    # f1.validate_and_program_fw_file()
    # f2.validate_and_program_fw_file()

    print(bat.battery_status())
    print(bat.device_name())
    print("Safety Status:", bat.get_safety_status())
    print("Safety Status details:", bat._safety_status)

    bat.set_fet_control(False) # OFF
    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 10.8
    print(f"Heater: {daq.get_VDC_rounded(7,3)}V")

    vsim.enable_aux_dac_channel()
    vsim.set_aux_voltage(4.5)
    sleep(0.5)
    gpio.enable_relay_n(4) # Vaux
    sleep(1.0)
    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 0 - 1.2V
    gpio.disable_relay_n(4) # Vaux
    sleep(1.0)
    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 10.8

    print("PSU Pack Output ON")
    psu1.configure_supply(10.8, 0.080, 50, 1)
    sleep(1.5)  # wait PSUs

    #bat.set_fet_control(False) # OFF
    bat.set_chg_fet(True)
    bat.set_dsg_fet(True)
    _ = bat.operation_status()
    print(bat._operation_status)
    _ = bat.manufacturing_status()
    print(bat._manufacturing_status)
    print("PSU Pack Output OFF")
    psu1.set_output_state(0)
    print(f"Pack: {daq.get_VDC_rounded(4,3)}V") # 10.8
    bat.set_chg_fet(False)
    bat.set_dsg_fet(False)
    sleep(2.5)
    print(f"Pack: {daq.get_VDC_rounded(4,3)}V") # 10.8
    psu2.set_output_state(0)
    vsim.power_down_all_cell_channels()


#--------------------------------------------------------------------------------------------------


def test_fuse_pin_cellside(bat: BQ40Z50R1, gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation, calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:

    print("PSU Cell Output ON")
    psu2.configure_supply(10.8, 0.080, 50, 1)
    #psu2.configure_cc_mode(0.08, None, 10.8, 1.0, 50, 1)
    print("PSU Pack Output ON")
    psu1.configure_supply(10.8, 0.080, 50, 1)
    sleep(1.5)  # wait PSUs
    vsim.enable_all_cell_channels()
    vsim.set_cell_n_voltage(1, 3.6)
    vsim.set_cell_n_voltage(2, 3.6)
    vsim.set_cell_n_voltage(3, 3.6)
    #vsim.set_cell_n_voltage(4, 3.6)

    print("PSU pack", psu1.get_all_measurements())
    print("PSU cell", psu2.get_all_measurements())
    #print("PSU Output off")

    gpio.disable_relay_n(1) # short-GND
    gpio.disable_relay_n(2) # 8.2kOhm-GND
    gpio.disable_relay_n(4) # Vaux

    print("Check battery:")
    if not bat.isReady():
        print("no battery found, stop test")
        psu2.set_output_state(0)
        vsim.power_down_all_cell_channels()
        return

    print("PSU Pack Output OFF")
    psu1.set_output_state(0)

    gpio.enable_relay_n(1) # short-GND
    #sleep(3.5)

    print(bat.device_name())
    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 10.8

    bat.set_fet_control(False) # OFF
    bat.set_chg_fet(True)
    bat.set_dsg_fet(True)
    sleep(0.5)
    _ = bat.operation_status()
    print(bat._operation_status)
    _ = bat.manufacturing_status()
    print(bat._manufacturing_status)
    for i in range(50):
        print(f"BQ FET Gate: {daq.get_VDC_rounded(8,3)}V")
        sleep(0.2)

    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 0 - 1.2V

    psu2.set_output_state(0)
    vsim.power_down_all_cell_channels()
    return

    bat.set_fet_control(False)
    bat.set_fuse(True)


    gpio.disable_relay_n(1) # Vaux
    sleep(1.0)
    print(f"Cell Stack: {daq.get_VDC_rounded(15,3)}V") # 10.8
    #bat.set_fet_control(False) # OFF
    bat.set_chg_fet(True)
    bat.set_dsg_fet(True)

    print(f"Pack: {daq.get_VDC_rounded(4,3)}V") # 10.8
    bat.set_chg_fet(False)
    bat.set_dsg_fet(False)
    sleep(1.5)
    print(f"Pack: {daq.get_VDC_rounded(4,3)}V") # 10.8
    psu2.set_output_state(0)
    vsim.power_down_all_cell_channels()


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    #LINE_NETWORK = "172.21.101"  # HOM Warehouse
    #LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.25.102"  # VN line 2
    LINE_NETWORK = "172.25.103"  # VN line 3

    SOCKET = 0  # 0, 1 or 2

    if SOCKET == 0:
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.31:3000", termination="\n")  # PCBA test, socket 0
        i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101") # socket 0
        #i2cbus = I2CPort("192.168.69.77:2101") # HOMEGROW
    if SOCKET == 1:
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.33:3000")  # PCBA test, socket 1
        i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101") # socket 1
    if SOCKET == 2:
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.35:3000")  # PCBA test, socket 2
        i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101") # socket 2

    #test_feasa_only(feasa)
    #exit()

    #print("Change clock frequency and timeout - RRC: ",
    #      str(i2cbus.i2c_change_clock_frequency(50000, timeout_ms=50)))

    mux = BusMux(i2cbus, address=0x77)
    for c in range(1,9):
        mux.setChannel(c)
        print("CH:", c, i2cbus.i2c_bus_scan())

    calib = CalibrationStorage(I2CMuxedBus(i2cbus, mux, 1))
    print("Inventory:", calib.load_inventory_number())
    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 2), retry_limit=7, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)

    #bat_flash_test_debug(bat)
    #exit()

    gpio = RelayBoard4Relay4GPIO(I2CMuxedBus(i2cbus, mux, 3))
    vsim = CellVoltageSimulation(I2CMuxedBus(i2cbus, mux, 4))
    vsim.initialize()

    #sleep(0.5)
    if SOCKET == 0:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=1)  # socket 0 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=2)  # socket 0 / share
    if SOCKET == 1:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=3)  # socket 1 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=4)  # socket 1 / share
    if SOCKET == 2:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=5)  # socket 2 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=6)  # socket 2 / share
    psu1.set_output_state(0)
    psu2.set_output_state(0)

    if SOCKET == 0:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=1)  # socket 0
    if SOCKET == 1:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=2)  # socket 1
    if SOCKET == 2:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=3)  # socket 2

    #psu_test(bat, gpio, psu2)
    #psu_test(bat, gpio, psu1)
    rack_test(bat, gpio, vsim, calib, feasa, psu1, psu2, daq)
    #test_fuse_pin_cellside(bat, gpio, vsim, calib, feasa, psu1, psu2, daq)
    #test_lvl2_heater(bat, gpio, vsim, calib, feasa, psu1, psu2, daq)
    #psu_mode_test(bat, gpio, vsim, calib, feasa, psu1, psu2, daq)
    #test_relay_only(gpio)
    #test_calibration_storage_only(calib)
    #bat_flash_test(bat, psu1, psu2)

# END OF FILE
