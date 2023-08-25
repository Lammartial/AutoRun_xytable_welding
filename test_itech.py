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

def test_m3900_some(m3900: M3900) -> bool:
    # Get current
    print(m3900.get_all_measurements())
    
    # Get current
    print(m3900.get_current())
    print(m3900.get_current_rounded(3))

    # Get voltage
    print(m3900.get_voltage())
    print(m3900.get_voltage_rounded(3))


def test_2x_m3400_short(psu1: M3400, psu2 :M3400) -> bool:
    from time import perf_counter, strftime, localtime

    print("PSU Output on")
    current = 2.0
    voltage = 10.8
    psu2.configure_supply(voltage, 0.1, 50, 1)
    sleep(1.0)  # wait PSU powered up
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    psu1.configure_sink(-current, 5.0, -2.4, voltage*0.1, -80, 0)
    sleep(1)
    psu2.configure_supply(voltage, current*1.2, 100, 1)
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())    
    psu1.set_output_state(1)
    print("PSU1", psu1.get_all_measurements())
    print("PSU2", psu2.get_all_measurements())
    sleep(3)
    psu1.configure_sink(-current, 5.0, -2.4, voltage*0.1, -80, 1)
    sleep(1)
    psu1.set_output_state(0)
    sleep(1)
    psu2.set_output_state(0)
    


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep
    from pyvisa import ResourceManager

    ## Initialize the logging
    #logger_init(filename_base=None)  ## init root logger with different filename
    #_log = getLogger(__name__, DEBUG)

    #LINE_NETWORK = "172.25.101"  # VN line 1
    LINE_NETWORK = "172.21.101"  # HOM Warehouse

    rm = ResourceManager()
    print(rm.list_resources())


    # there is one ETH bridge for 6 PSUs    
    #psu1 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=1)  # socket 0, 1, and 2 share
    #psu2 = M3400(f"TCPIP0::{LINE_NETWORK}.37::inst0::INSTR", dev_channel=2)  # socket 0, 1, and 2 share
    # psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=1)  # socket 0, 1, and 2 share
    # psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=2)  # socket 0, 1, and 2 share
    
    # test_2x_m3400_short(psu1, psu2)

    from rrc.eth2serial import Eth2SerialDevice
    psu = Eth2SerialDevice(f"{LINE_NETWORK}.46:30000", termination="\n")
    print(psu.request("*IDN?"))  # Base device
    # sleep(0.03)
    # for c in range(1,7):
    #     print(psu.request(f":CHAN {c};*IDN?"))
    #     sleep(0.03)
    print(psu.request(":OUTP?"))
    print(psu.request(":FETC:VOLT?"))

    # m = M3400("TCPIP0::172.25.101.51::inst0::INSTR")
    # print('IDN:' +str(m.request('*IDN?')))
    # print('ERROR', m.read_system_error())
    # print(m.get_all_measurements())

    #m = M3900("TCPIP0::172.21.101.37::inst0::INSTR")
    #print('IDN:' +str(m.request('*IDN?')))
    #print('ERROR', m.read_system_error())
    #print(m.get_all_measurements())

    #test_m3900_some(m)

    # for m in m3412[:]:
    #     print('IDN:' +str(m.request('*IDN?')))
    #     print('ERROR', m.read_system_error())
    #     # m.set_remote_control()
    #     # m.set_sense_state(1)
    #     # m.set_output_state(0)
    #     # print(m.get_all_meas())

    #test_start_battery_pcba(m3412[0], m3412[1])

    #for m in m3412:
    #    m.set_output_state(0)  # switch all outputs OFF

    print("DONE.")

#--------------------------------------------------------------------------------------------------

# END OF FILE