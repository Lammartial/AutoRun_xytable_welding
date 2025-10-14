"""
PETA Design PCBA Adapter.
"""

#import unittest
from typing import Tuple
from time import sleep
from pathlib import Path
from rrc.eth2can import CANBus
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1, BQStudioFileFlasher, BQ34Z100, BQ76942
from rrc.gpio_tcal6416 import TCAL6416
from rrc.cartridge_peta import CartridgePETA
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


def test_calibration_storage_only(calib: CalibrationStorage) -> None:
    print("Read calibration EEPROM values")
    print("Inventory Number: ", calib.load_inventory_number())
    print("Shunt Resistance: ", calib.load_shunt_resistance_ohm())
    [print(f"Leakage Current: {i}# {calib.load_leakcurrent_amps(i)}") for i in range(3)]


def test_cartridge_only(cart: CartridgePETA) -> None:

    #cart.gpio.set_pin(7) # enable the AFE and Gasgauge
    cart.select_bus_to_micro("i2c")
    #print("I2C to MICRO: ", cart.get_muxed_i2c_bus_for(1).i2c_bus_scan())
    #print("I2C to BACKYARD: ", cart.get_muxed_i2c_bus_for(2).i2c_bus_scan())
    #print("I2C to GPIO: ", cart.get_muxed_i2c_bus_for(8).i2c_bus_scan())
    for i in range(3):
        cart.switch_mosfet(i, 1)
        sleep(0.15)
        cart.switch_mosfet(i, 0)
        sleep(0.15)
    cart.select_bus_to_micro("can")
    #print("I2C to MICRO: ", cart.get_muxed_i2c_bus_for(1).i2c_bus_scan())
    #print("I2C to BACKYARD: ", cart.get_muxed_i2c_bus_for(2).i2c_bus_scan())
    #print("I2C to GPIO: ", cart.get_muxed_i2c_bus_for(8).i2c_bus_scan())
    cart.select_bus_to_micro("i2c")


def rack_test(cartridge: CartridgePETA, gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation, calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:
    #psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    #psu.configure_current_rise_times(pos="DEF", neg="DEF")

    # verify that PSU does not trigger battery protection
    print("PSU Output on")
    psu1.configure_supply(25.090, 0.080, 50, 0)
    psu2.configure_supply(25.090, 0.080, 50, 0)
    #psu2.configure_cc_mode(0.05, 10.8*1.15, (10.8*1.15) * 0.8, 50, 1)

    sleep(0.5)  # wait PSU powered up

    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())

    #vsim.power_down_all_cell_channels()
    #sleep(0.2)
    vsim.enable_all_cell_channels()
    for cell_no in range(1, 7):
        vsim.set_cell_n_voltage(cell_no, 3.6)

    # switch cell side on first
    psu2.set_output_state(1)
    sleep(0.25)
    psu1.set_output_state(1)
    sleep(0.5)

    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())

    #cartridge.select_bus_to_micro("i2c")
    print("BACKYARD:", cartridge.backyard_bus.i2c.i2c_bus_scan())
    print("MICRO:", cartridge.smbus_to_mirco.i2c.i2c_bus_scan())
    #for n in range(1,9):
    #    print(cartridge.get_muxed_i2c_bus_for(n).i2c_bus_scan())

    print("DAQ - channel 11", daq.get_VDC(11))
    print("DAQ - channel 12", daq.get_VDC(12))
    print("DAQ - channel 14", daq.get_VDC(14))
    print("DAQ - channel 10", daq.get_VDC(10))
    print("DAQ - channel 18", daq.get_VDC(18))
    print("DAQ - channel 19", daq.get_VDC(19))
    print("DAQ - channel 5", daq.get_VDC(5))

    print("DAQ - channel 15", daq.get_VDC(15))  # full pack voltage

    print("DAQ - channel 8", daq.get_VDC(8))  # should be +3.3v
    print("DAQ - channel 9", daq.get_VDC(9))  # should be +1.8v


    afe = BQ76942(cartridge.backyard_bus, slvAddress=0x08, pec=True)
    print(afe.read_cell_voltages())
    print(afe.read_temperatures())
    print(afe.read_control_status())
    print(afe.read_battery_status())

    print(afe.read_subcommand(0x00a0))
    gg = BQ34Z100(cartridge.backyard_bus, slvAddress=0x55, pec=False)
    print(gg.get_voltage_scale())
    print(gg.get_current_scale())
    print(gg.get_energy_scale())
    print(gg.voltage())
    print(gg.temperature())


    cartridge.reset_mux()
    vsim.power_down_all_cell_channels()

    psu1.set_output_state(0)
    psu2.set_output_state(0)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    LINE_NETWORK = "172.21.101"  # HOM Warehouse
    #LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.25.102"  # VN line 2
    #LINE_NETWORK = "172.25.103"  # VN line 3

    SOCKET = 0  # 0, 1 or 2
    # following assumes own IF-OLIMEX breakout adapter
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
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.31:2000")  # socket 0
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.30:3000")  # PCBA test, socket 0
        i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101")  # socket 0
        #can = CANBus(f"{LINE_NETWORK}.30:3303")  # socket 0
    if SOCKET == 1:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.33:2000")  # socket 1
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.32:3000")  # PCBA test, socket 1
        i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101")  # socket 1
        can = CANBus(f"{LINE_NETWORK}.32:3303")  # socket 1
    if SOCKET == 2:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.35:2000")  # socket 2
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.34:3000")  # PCBA test, socket 2
        i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101")  # socket 2
        can = CANBus(f"{LINE_NETWORK}.34:3303")  # socket 2



    print("Change clock frequency and timeout - RRC: ",
          str(i2cbus.i2c_change_clock_frequency(400000, timeout_ms=20)))
    print("MASTER:", i2cbus.i2c_bus_scan())

    mux = BusMux(i2cbus, address=0x77)
    vsim = CellVoltageSimulation(I2CMuxedBus(i2cbus, mux, 4))
    vsim.initialize()
    vsim.power_down_all_cell_channels()

    for c in range(8,0,-1):
        mux.setChannel(c)
        print("CH:", c, i2cbus.i2c_bus_scan())

    dutcom = I2CMuxedBus(i2cbus, mux, 2)  # i2c to the DUT
    #mux_on_cartridge = BusMux(dutcom, address=0x70)  # this is the MUX on the DUT board
    # print("MUX ON CARTRIDGE:")
    # for c in range(1,9):
    #     mux_on_cartridge.setChannel(c)
    #     print("CH:", c, dutcom.i2c_bus_scan())

    cart = CartridgePETA(dutcom)
    test_cartridge_only(cart)

    #cart.select_bus_to_micro("can")
    #can.send(0x11, (1,2,3,4,5,6,7,8))
    #print(can.receive(0x11))

    # double MUX'd
    # dut_micro = BusMaster(I2CMuxedBus(dutcom, mux_on_cartridge, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    # dut_gasgauge = BQ34Z100(I2CMuxedBus(dutcom, mux_on_cartridge, 2))
    # dut_afe = BQ76942(I2CMuxedBus(dutcom, mux_on_cartridge, 2))
    # dut_gpio = TCAL6416(I2CMuxedBus(dutcom, mux_on_cartridge, 8), i2c_address_7bit=0x20)
    # # testdummy for double, transparent MUX
    # print(dut_micro.i2c.i2c_bus_scan())
    # print(dut_gasgauge.bus.i2c_bus_scan())
    # print(dut_afe.bus.i2c_bus_scan())
    # print(dut_gpio.bus.i2c_bus_scan())

    # which EEPROM type do we need to implement ?

    calib = CalibrationStorage(I2CMuxedBus(i2cbus, mux, 1))
    print("Inventory:", calib.load_inventory_number())

    gpio = RelayBoard4Relay4GPIO(I2CMuxedBus(i2cbus, mux, 3))

    #sleep(0.5)

    if SOCKET == 0:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=1)  # socket 0
    if SOCKET == 1:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=2)  # socket 1
    if SOCKET == 2:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=3)  # socket 2

    print(daq.ident())

    # .... do some tests here ....

    rack_test(cart, gpio, vsim, calib, feasa, psu1, psu2, daq)

    i2cbus.close()

# END OF FILE
