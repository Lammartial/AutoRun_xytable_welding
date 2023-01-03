from drv_DAQ970A import DAQ970A

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    DAQ970A_IP_STR = "TCPIP0::192.168.1.184::inst0::INSTR" #"TCPIP0::169.254.196.86::inst0::INSTR"
    DAQ970A_NAME_STR = "TCPIP0::K-DAQ970A-17481.local::inst0::INSTR"

    # 1. Create an instance of DAQ970A class
    daq970a = DAQ970A()

    # 2. Connect to the device
    #daq970a.connect_by_name(DAQ970A_NAME_STR)
    # or
    daq970a.connect_by_IP(DAQ970A_IP_STR)

    # 3. Do some stuff
    print(daq970a.selftest())

    res = daq970a.get_resistance(1,1)
    print(res)

    #print(daq970a.get_4w_resistance(1,2))

    #print(daq970a.get_VDC(1,3))

    #print(daq970a.get_VAC(1,4))

    #print(daq970a.get_ADC(1,21))

    #print(daq970a.get_temp(1, 1, "DEF", 0, 0, "B"))

    # 4. ERRORS 
    # Value error (channel = 25):
    #print(daq970a.get_resistance(1,25))

    # Value error (tran_type is not a string)
    #print(daq970a.get_temp(1, 1, 0, 0, 0, "B"))

    # Value error (tc_type is not a string)
    #print(daq970a.get_temp(1, 1, "DEF", 0, 0, 0))

    # 4. Close connection
    daq970a.disconnect()
    
    print("DONE.")
    
# END OF FILE