#import unittest
from rrc.itech import M3400, M3900

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 0
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

#--------------------------------------------------------------------------------------------------
def test_m3900_modes(m3900: M3900) -> bool:

    #========= CHARGE & DISCHARGE MODE =====================================================================

    m3900.wake_up_mode_on(voltage_limit= 12.0, curr_limit= 0.1)
    m3900.wake_up_mode_off()


    m3900.charge_mode_on(voltage_limit= 12.55, curr= 2.0)     # Volt limit 12.55 for RRC2020
    m3900.charge_mode_off()

    m3900.discharge_mode_on(voltage_limit= 11.0, curr= -2.0)
    m3900.discharge_mode_off()

    m3900.charge_mode_on(voltage_limit= 12.55, curr= 2.0)     # Volt limit 12.55 for RRC2020
    m3900.charge_mode_off()

    m3900.discharge_mode_on(voltage_limit= 11.0, curr= -2.0)
    m3900.discharge_mode_off()

    #=======================================================================================================

    #print(it_m3902.get_ADC())

    #print(it_m3902.get_VDC())

    return True

#--------------------------------------------------------------------------------------------------
def test_m3400_some(m3400: M3400) -> bool:
    # Get current
    print(m3400.get_ADC())

    # Get voltage
    #print(m3400.get_VDC())

    # Doesn't work. Get temperature
    #print(m3400.get_temp())

    # Get Current, Voltage, Temperature, ...
    #print(m3400.get_all_meas())

    # Set SENSE state
    #m3400.set_sense_state(0)                        # No return value

    # Get SENSE state
    #print(m3400.get_sense_state())

    #Doesn't work. Get output reverse state
    #print(m3400.get_output_reverse_state())

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    #m3400.set_current(1.0005)                      # No return value

    # Get current.
    #print(m3400.get_current())

    # Set current limit positive. curr - string 'MIN', 'MAX' or'X.XX' Amp
    #m3400.set_current_limit_positive(curr = 5.000)       # No return value

    # Get current limit positive
    #print(m3400.get_current_limit_positive())

    # Set current limit negative. curr - string 'MIN', 'MAX' or'X.XX' Amp
    #m3400.set_current_limit_negative(curr = -5.000)   #(-02.000)       # No return value

    # Get current limit negative
    #print(m3400.get_current_limit_negative())

    # Set current protection
    #m3400.set_current_protection(10.000)           # No return value

    # Get current protection
    #print(m3400.get_current_protection())

    # Set under-current limit
    #m3400.set_current_under_protection(1.000)      # No return value

    # Set voltage value
    #m3400.set_voltage(10.00)                       # No return value

    # Set voltage upper limit
    #m3400.set_voltage_limit(20.00)                 # No return value

    # Set voltage lower limit under CC priority mode
    #it_m3902.set_voltage_limit_low(1.00)              # No return value

    # Set over voltage limit (MAX = 61.00)
    #m3400.set_voltage_protection(60.00)            # No return value

    # Set voltage under-protection
    #m3400.set_voltage_under_protection(10.00)      # No return value

    #============== 6 channel test ===============================================================

    # 1. Create an instance of ITECH_DEV class
    # using multi-channel communication
    # m3400_1 = M3400(M3412_IP_STR, 1)
    # m3400_2 = M3400(M3412_IP_STR, 2)
    # m3400_3 = M3400(M3412_IP_STR, 3)
    # m3400_4 = M3400(M3412_IP_STR, 4)
    # m3400_5 = M3400(M3412_IP_STR, 5)
    # m3400_6 = M3400(M3412_IP_STR, 6)

    # # 2. IMPORTANT! Set remote control mode.
    # m3400_1.set_remote_control()
    # m3400_2.set_remote_control()

    # # 3. Do some stuff

    # print(m3400_1.get_ADC())
    # print(m3400_2.get_ADC())
    # print(m3400_3.get_ADC())
    # print(m3400_4.get_ADC())
    # print(m3400_5.get_ADC())
    # print(m3400_6.get_ADC())

    #print(m3400_1.get_VDC())
    #print(m3400_2.get_VDC())

    # Set voltage value
    #m3400_1.set_voltage(1.00)                       # No return value
    #m3400_2.set_voltage(1.00)                       # No return value
    #m3400_3.set_voltage(1.00)                       # No return value
    #m3400_4.set_voltage(1.00)                       # No return value
    #m3400_5.set_voltage(1.00)                       # No return value
    #m3400_6.set_voltage(1.00)                       # No return value

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    #m3400_1.set_current_limit_positive(0.05)                      # No return value
    #m3400_2.set_current_limit_positive(0.05)                      # No return value
    #m3400_3.set_current_limit_positive(0.05)                      # No return value
    #m3400_4.set_current_limit_positive(0.05)                      # No return value
    #m3400_5.set_current_limit_positive(0.05)                      # No return value
    #m3400_6.set_current_limit_positive(0.05)                      # No return value

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    #m3400_1.set_current(0.100)                      # No return value
    #m3400_2.set_current(0.100)                      # No return value
    #m3400_3.set_current(0.100)                      # No return value
    #m3400_4.set_current(0.100)                      # No return value
    #m3400_5.set_current(0.100)                      # No return value
    #m3400_6.set_current(0.100)                      # No return value

    # Set OUTPUT ON/OFF
    #m3400_1.set_output_state(1)                    # No return value
    #m3400_2.set_output_state(1)                    # No return value
    #m3400_3.set_output_state(1)                    # No return value
    #m3400_4.set_output_state(1)                    # No return value
    #m3400_5.set_output_state(1)                    # No return value
    #m3400_6.set_output_state(1)                    # No return value

    #sleep(1)

    # Get OUTPUT state
    #print(m3400_1.get_output_state())
    #print(m3400_2.get_output_state())
    #print(m3400_3.get_output_state())
    #print(m3400_4.get_output_state())
    #print(m3400_5.get_output_state())
    #print(m3400_6.get_output_state())

    #print(m3400_1.get_all_meas())
    #print(m3400_2.get_all_meas())
    #print(m3400_3.get_all_meas())
    #print(m3400_4.get_all_meas())
    #print(m3400_5.get_all_meas())
    #print(m3400_6.get_all_meas())

    # Set OUTPUT ON/OFF
    #m3400_1.set_output_state(0)                    # No return value
    #m3400_2.set_output_state(0)                    # No return value
    #m3400_3.set_output_state(0)                    # No return value
    #m3400_4.set_output_state(0)                    # No return value
    #m3400_5.set_output_state(0)                    # No return value
    #m3400_6.set_output_state(0)                    # No return value

    return True

#--------------------------------------------------------------------------------------------------
def test_start_battery_pcba(psu1: M3400, psu2: M3400):
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CBus, BusMux, I2CMuxedBus
    from rrc.testadapter_cell_voltage_source import CellVoltageSource
    from rrc.smbus import BusMaster
    from rrc.chipsets import BQ40Z50R1

    i2cbus = I2CPort("172.21.101.21:2101")
    mux = BusMux(i2cbus, 0x77)
    cellsim = CellVoltageSource(I2CMuxedBus(i2cbus, mux, 4), 0x48)
    cellsim.initialize()
    smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 2), retry_limit=5, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)

    # Wakeup battery
    sleep(2)

    power_limit = 150
    current_limit = 0.05
    pack_voltage = 10.8
    cell_count = 3
    cellsim.enable_all_cell_channels()
    psu1.set_voltage(pack_voltage)
    psu1.set_current_limit_negative(-current_limit)
    psu1.set_current_limit_positive(current_limit)
    psu1.set_power_limit_positive(power_limit)
    psu1.set_power_limit_negative(-power_limit)

    psu2.set_voltage(pack_voltage)
    psu2.set_current_limit_negative(0)
    psu2.set_current_limit_positive(2.0)
    psu2.set_power_limit_positive(power_limit)
    psu2.set_power_limit_negative(-power_limit)

    cellsim.set_cell_n_voltage(1, pack_voltage/cell_count)
    cellsim.set_cell_n_voltage(2, pack_voltage/cell_count)

    psu2.set_output_state(1)
    sleep(1.0)
    psu1.set_output_state(1)
    sleep(0.5)
    if not bat.waitForReady(timeout_ms=2000):
        print("battery not ready.")
        return
    # output off
    psu1.set_output_state(0)

    # connect the input PSU to the output
    bat.toggle_chg_fet()
    bat.toggle_dsg_fet()

    psu2.set_current_limit_negative(0)
    psu2.set_current_limit_positive(2.0)

    # now we should see a voltage as Input for PSU1 in the next steps.
    print(psu1.get_all_meas())
    print(psu2.get_all_meas())
 
    sleep(2)
    # measure
    print(bat.voltage())

    psu1.set_power_limit_positive(150.0)
    #psu1.set_voltage_limit_high(pack_voltage)
    #psu1.set_voltage_limit_low(1.0)
    psu1.set_current_limit_negative(-2.0)
    psu1.set_current_limit_positive(2.0)
    psu1.set_current(-0.2)
    psu1.set_function("CC") 
    psu1.set_output_state(1)

    sleep(2)
    # measure
    print(bat.voltage())

    # now disable FET in PCBA
    bat.set_dsg_fet(False)

    sleep(1)
    # measure
    print(bat.voltage())

   
    sleep(2)
    psu1.set_output_state(0)
    psu2.set_output_state(0)
    cellsim.power_down_all_cell_channels()
    



#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    logger = logging.getLogger()  # we need to cut down the root logger
    logger.setLevel(logging.INFO)
    _log = getLogger(__name__, DEBUG)

    res : float = 0

    # # predefined resource ID
    # M3902_IP_STR = "TCPIP0::172.21.101.33::inst0::INSTR"

    # # 1. Create an instance of ITECH_DEV class
    # # using multi-channel communication
    # m3902 = M3900(M3902_IP_STR, 0)
    # # 2. IMPORTANT! Set remote control mode.
    # print(m3902.set_remote_control())
    # # 3. Do some stuff
    # test_m3900_modes(m3902)

    # there is one ETH bridge for 6 PSUs
    E1206_IP_STR = "TCPIP0::172.21.101.24::inst0::INSTR"
    m3412 = [M3400(E1206_IP_STR, i) for i in range(1,7)]
    #test_m3400_some(m3412[0])

    for m in m3412[:2]:
        m.set_remote_control()
        m.set_sense_state(1)
        m.set_output_state(0)

    psu1 = m3412[0]
    psu2 = m3412[1]

    print(psu1.get_all_meas())
    print(psu2.get_all_meas())

    test_start_battery_pcba(psu1, psu2)

    for m in m3412:
        m.set_output_state(0)  # switch all outputs OFF

 #=============================================================================================

    print("DONE.")