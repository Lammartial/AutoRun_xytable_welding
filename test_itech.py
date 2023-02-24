#import unittest
from rrc.itech import M3400, M3900

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 0
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

def test_m3900_modes(m3900: M3900) -> bool:

    #========= CHARGE & DISCHARGE MODE =====================================================================

    #m3900.configure_wake_up_mode(current= 0.05, current_limit= 0.1, voltage_limit_high= 12.0, power_limit= 80, set_output= True)
    #m3900.configure_wake_up_mode(current= 0.05, current_limit= 0.1, voltage_limit_high= 12.0, power_limit= 80, set_output= False)

    m3900.configure_discharge_mode(current= -2.0, current_limit= -2.5, voltage_limit_high= 12.55, power_limit= -150, set_output= True)    
    m3900.configure_discharge_mode(current= -2.0, current_limit= -2.5, voltage_limit_high= 12.55, power_limit= -150, set_output= False) 

    m3900.configure_charge_mode(current= 2.0, current_limit= 2.5, voltage_limit_high= 12.55, power_limit= 150, set_output= True)    
    m3900.configure_charge_mode(current= 2.0, current_limit= 2.5, voltage_limit_high= 12.55, power_limit= 150, set_output= False)

    #m3900.configure_discharge_mode(voltage_limit= 11.0, curr= -2.0)

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
if __name__ == "__main__":
    from time import sleep
    from pyvisa import ResourceManager

    ## Initialize the logging
    #logger_init(filename_base=None)  ## init root logger with different filename
    #_log = getLogger(__name__, DEBUG)


    rm = ResourceManager()
    print(rm.list_resources())


    # # predefined resource ID
    # M3902_IP_STR = "TCPIP0::172.21.101.51::inst0::INSTR"
    # # 1. Create an instance of ITECH_DEV class
    # # using multi-channel communication
    # m3902 = M3900(M3902_IP_STR, 0)
    # # 2. IMPORTANT! Set remote control mode.
    # m3902.initialize_device()
    # # 3. Do some stuff
    # test_m3900_modes(m3902)



    # there is one ETH bridge for 6 PSUs
    E1206_IP_STR = "TCPIP0::172.21.101.24::inst0::INSTR"
    m3412 = [M3400(E1206_IP_STR, i) for i in range(1,7)]
    #test_m3400_some(m3412[0])

    for m in m3412[:]:
        print('IDN:' +str(m.request('*IDN?')))
        print('ERROR', m.read_system_error())
        # m.set_remote_control()
        # m.set_sense_state(1)
        # m.set_output_state(0)
        # print(m.get_all_meas())

    #test_start_battery_pcba(m3412[0], m3412[1])

    for m in m3412:
        m.set_output_state(0)  # switch all outputs OFF

    print("DONE.")

#--------------------------------------------------------------------------------------------------

# END OF FILE