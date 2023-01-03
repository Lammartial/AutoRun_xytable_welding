from drv_M3400 import M3400_DEV

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    #M3412_IP_STR = "TCPIP0::169.254.208.73::inst0::INSTR" 
    M3412_IP_STR = "TCPIP0::192.168.1.63::inst0::INSTR" 
    #M3412_NAME_STR = "TCPIP0::K-DAQ970A-17481.local::inst0::INSTR"

    # 1. Create an instance of ITECH_DEV class
    it_m3412 = M3400_DEV()

    # 2. Connect to the device
    #it_m3412.connect_by_name(DAQ970A_NAME_STR)
    # or
    print(it_m3412.connect_by_IP(M3412_IP_STR))

    # 3. IMPORTANT! Set remote control mode.
    it_m3412.set_remote_control()                   # No return value

    # 4. Do some stuff

    # Set OUTPUT ON/OFF
    it_m3412.set_output_state(1)                    # No return value

    sleep(1)

    # Get OUTPUT state 
    print(it_m3412.get_output_state())

    # Get current
    print(it_m3412.get_ADC())

    # Get voltage
    print(it_m3412.get_VDC())

    # Doesn't work. Get temperature
    #print(it_m3412.get_temp())

    # Get Current, Voltage, Temperature, ...
    print(it_m3412.get_all_meas())

    # Set SENSE state
    it_m3412.set_sense_state(0)                        # No return value

    # Get SENSE state
    print(it_m3412.get_sense_state())

    #Doesn't work. Get output reverse state
    #print(it_m3412.get_output_reverse_state())

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    it_m3412.set_current(1.0005)                      # No return value

    # Get current.
    print(it_m3412.get_current())

    # Set current limit positive. curr - string 'MIN', 'MAX' or'X.XX' Amp
    it_m3412.set_current_limit_positive(curr = 5.000)       # No return value

    # Get current limit positive
    print(it_m3412.get_current_limit_positive())

    # Set current limit negative. curr - string 'MIN', 'MAX' or'X.XX' Amp
    it_m3412.set_current_limit_negative(curr = -5.000)   #(-02.000)       # No return value

    # Get current limit negative
    print(it_m3412.get_current_limit_negative())

    # Set current protection
    it_m3412.set_current_protection(10.000)           # No return value

    # Get current protection
    #print(it_m3412.get_current_protection())

    # Set under-current limit
    it_m3412.set_current_under_protection(1.000)      # No return value

    # Set voltage value
    it_m3412.set_voltage(10.00)                       # No return value

    # Set voltage upper limit
    it_m3412.set_voltage_limit(20.00)                 # No return value

    # Set voltage lower limit under CC priority mode
    it_m3412.set_voltage_limit_low(1.00)              # No return value

    # Set over voltage limit (MAX = 61.00)
    it_m3412.set_voltage_protection(60.00)            # No return value

    # Set voltage under-protection
    it_m3412.set_voltage_under_protection(10.00)      # No return value

    # 4. ERRORS 

    # Check errors
    #print(it_m3412.set_raw_query('SYST:ERR?'))

    # Check Standard Event Status Register (SESR)
    #print(it_m3412.set_raw_query('*ESR?'))

    # 5. Close connection
    it_m3412.disconnect()
    
    print("DONE.")
    
# END OF FILE