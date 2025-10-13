"""
PETA Design PCBA Adapter.
"""

#import unittest
from typing import Tuple
from time import sleep
from pathlib import Path
from rrc.eth2i2c import I2CPort
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1, BQStudioFileFlasher, BQ34Z100, BQ76942
from rrc.gpio_tcal6416 import TCAL6416
from rrc.cartridge_peta import CartridgePETA
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
    cart.select_bus_to_micro("i2c")
    for i in range(3):
        cart.switch_mosfet(i, 1)
        sleep(0.5)
        cart.switch_mosfet(i, 0)
        sleep(0.5)
    cart.select_bus_to_micro("can")

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
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.30:2000")  # socket 0
        i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101")  # socket 0
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.30:3000")  # PCBA test, socket 0
    if SOCKET == 1:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.32:2000")  # socket 1
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.32:3000")  # PCBA test, socket 1
        i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101")  # socket 1
    if SOCKET == 2:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.34:2000")  # socket 2
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.34:3000")  # PCBA test, socket 2
        i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101")  # socket 2


    #print("Change clock frequency and timeout - RRC: ",
    #      str(i2cbus.i2c_change_clock_frequency(50000, timeout_ms=50)))
    print("MASTER:", i2cbus.i2c_bus_scan())

    mux = BusMux(i2cbus, address=0x77)
    #mux = BusMux(i2cbus, address=0x70)  # OLIMEX Breakout
    for c in range(1,9):
        mux.setChannel(c)
        print("CH:", c, i2cbus.i2c_bus_scan())

    print("MUX ON CARTRIDGE:")
    dutcom = I2CMuxedBus(i2cbus, mux, 2)  # i2c to the DUT
    mux_on_cartridge = BusMux(dutcom, address=0x70)  # this is the MUX on the DUT board
    for c in range(1,9):
        mux_on_cartridge.setChannel(c)
        print("CH:", c, dutcom.i2c_bus_scan())

    
    cart = CartridgePETA(dutcom)
    test_cartridge_only(cart)
    # double MUX'd
    dut_micro = BusMaster(I2CMuxedBus(dutcom, mux_on_cartridge, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    dut_gasgauge = BQ34Z100(I2CMuxedBus(dutcom, mux_on_cartridge, 2))
    dut_afe = BQ76942(I2CMuxedBus(dutcom, mux_on_cartridge, 2))    
    dut_gpio = TCAL6416(I2CMuxedBus(dutcom, mux_on_cartridge, 8), i2c_address_7bit=0x20)
    # testdummy for double, transparent MUX
    print(dut_micro.bus.i2c_bus_scan())
    print(dut_gasgauge.bus.i2c_bus_scan())
    print(dut_afe.bus.i2c_bus_scan())
    print(dut_gpio.bus.i2c_bus_scan())

    # which EEPROM type do we need to implement ?

    calib = CalibrationStorage(I2CMuxedBus(i2cbus, mux, 1))
    print("Inventory:", calib.load_inventory_number())

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

    # .... do some tests here ....


# END OF FILE
