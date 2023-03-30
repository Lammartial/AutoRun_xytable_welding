#import unittest
from typing import Tuple
from rrc.itech import M3400
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import I2CBus, BusMux, I2CMuxedBus
from rrc.cell_voltage_simulation import CellVoltageSimulation
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 0
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

def test_start_battery_pcba(i2cbus: I2CPort, psu1: M3400, psu2: M3400) -> Tuple[BQ40Z50R1, CellVoltageSimulation]:    
    mux = BusMux(i2cbus, 0x77)
    cellsim = CellVoltageSimulation(I2CMuxedBus(i2cbus, mux, 4), 0x48)
    cellsim.initialize()
    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 2), retry_limit=7, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)

    # Wakeup battery
    sleep(2)

    resistance = 50.0
    power_limit = 150
    current_limit = 0.08
    pack_voltage = 10.8
    cell_count = 3

    cellsim.enable_all_cell_channels()
    
    # psu1.set_voltage(pack_voltage)
    # psu1.set_current_limit_negative(-current_limit)
    # psu1.set_current_limit_positive(current_limit)
    # psu1.set_power_limit_positive(power_limit)
    # psu1.set_power_limit_negative(-power_limit)
    psu1.configure_supply(pack_voltage, current_limit, power_limit, 0)

    # psu2.set_voltage(pack_voltage)
    # psu2.set_current_limit_negative(0)
    # psu2.set_current_limit_positive(2.0)
    # psu2.set_power_limit_positive(power_limit)
    # psu2.set_power_limit_negative(-power_limit)
    psu2.configure_supply(pack_voltage, 2.0, 50, 0)

    cellsim.set_cell_n_voltage(1, pack_voltage/cell_count)
    cellsim.set_cell_n_voltage(2, pack_voltage/cell_count)

    psu2.set_output_state(1)
    print("Wait after PSU2 on...")
    sleep(1.0)
    psu1.set_output_state(1)
    print("Wait after PSU1 on...")
    sleep(0.5)
    if not bat.waitForReady(timeout_ms=5000):
        _msg = "battery not ready."
        #cellsim.power_down_all_cell_channels()
        #raise Exception(_msg)
        # output off
        psu1.set_output_state(0)            
        print(_msg)
        return bat, cellsim
    # output off
    psu1.set_output_state(0)
    print("Battery ready...")

    #bat.enable_full_access()
    #bat.manufacturing_status()
    #print(bat._manufacturing_status)

    return bat, cellsim

#--------------------------------------------------------------------------------------------------

def test_something(bat: BQ40Z50R1, cellsim: CellVoltageSimulation):
    resistance = 50.0
    power_limit = 150
    current_limit = 0.05
    pack_voltage = 10.8
    cell_count = 3

    bat.manufacturing_status()
    print(bat._manufacturing_status)
    print("BEFORE FET TOGGLE:", bat.manufacturing_dastatus1())
    # connect the input PSU to the output
    #bat.toggle_fet_control()
    bat.set_fet_control(0)
    sleep(1)
    bat.manufacturing_status()
    print(bat._manufacturing_status)
    
    psu1.configure_sink(-0.05, 300.0, -0.08, 9.0, power_limit, 1)
    #psu1.set_output_state(1)

    bat.set_chg_fet(1)
    bat.manufacturing_status()
    print(bat._manufacturing_status)
    bat.set_dsg_fet(1)
    bat.manufacturing_status()
    print(bat._manufacturing_status)

    print("AFTER FET TOGGLE:", bat.manufacturing_dastatus1())
    
    #psu2.set_current_limit_negative(0)
    #psu2.set_current_limit_positive(2.0)

    # now we should see a voltage as Input for PSU1 in the next steps.
    print(psu1.get_all_measurements())
    print(psu2.get_all_measurements())
 
    sleep(2)
    # measure battery
    print(bat.manufacturing_dastatus1())

    # psu1.set_power_limit_positive(150.0)
    # #psu1.set_voltage_limit_high(pack_voltage)
    # #psu1.set_voltage_limit_low(1.0)
    # psu1.set_current_limit_negative(-2.0)
    # psu1.set_current_limit_positive(2.0)
    # psu1.set_current(-0.2)
    # psu1.set_function("CC") 
    # psu1.set_output_state(1)
    #psu1.configure_sink(-0.02, 50.0, -0.05, 12.0, power_limit, 1)

    sleep(3)
    # measure
    print(bat.voltage())

    # now disable FET in PCBA
    bat.set_dsg_fet(True)

    sleep(1)
    # measure
    print(bat.manufacturing_dastatus1())

   
    sleep(2)
    psu1.set_output_state(0)
    psu2.set_output_state(0)
    cellsim.power_down_all_cell_channels()

#--------------------------------------------------------------------------------------------------

def test_program_firmware(bat: BQ40Z50R1, filename: str):
    from rrc.chipsets.bq_flasher import BQStudioFileFlasher

    flasher = BQStudioFileFlasher(bat, filename)
    flasher.program_fw_file()


#--------------------------------------------------------------------------------------------------

def test_flash_write(bat: BQ40Z50R1):
    bat.write_flash_block(0x4000, b'\x00\x01\x02\x04')

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    from time import sleep
    from pyvisa import ResourceManager

    ## Initialize the logging
    #logger_init(filename_base=None)  ## init root logger with different filename
    #logger = logging.getLogger()  # we need to cut down the root logger to suppress pyvisa
    #logger.setLevel(logging.INFO)
    #_log = getLogger(__name__, DEBUG)

    rm = ResourceManager()
    print(rm.list_resources())
    
    # there is one ETH bridge for 6 PSUs
    E1206_IP_STR = "TCPIP0::172.25.101.37::inst0::INSTR"
    m3412 = [M3400(E1206_IP_STR, i) for i in range(1,7)]
    #test_m3400_some(m3412[0])

    for m in m3412[:]:
        m.set_output_state(0)
        print(m.get_all_measurements())

    i2cbus = I2CPort("172.25.101.34:2101")  # battery on socket_2
    psu1 = m3412[4]
    psu2 = m3412[5]
    try:
        bat, cellsim = test_start_battery_pcba(i2cbus, psu1, psu2)
        test_program_firmware(bat, "C:/Production/Battery-PCBA-Test/filestore/SCD_3412031-04_A_Rubin-B_RRC2020B_Recovery.bq.fs")
        #test_program_firmware(bat, "C:/Production/Battery-PCBA-Test/filestore/SCD_3412031-04_A_Rubin-B_RRC2020B.bq.fs")
        #test_flash_write(bat)
        #test_something(bat, cellsim)
    except Exception as ex:
        print(ex)
    

    for m in m3412:
        m.set_output_state(0)  # switch all outputs OFF


    print("DONE.")

# END OF FILE