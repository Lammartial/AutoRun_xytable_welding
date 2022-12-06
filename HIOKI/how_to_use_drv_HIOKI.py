from drv_HIOKI import HIOKI_DEV

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    BT_IP_STR = "192.168.1.102"     # BT3561A IP addr
    BT_PORT = 23                    # BT3561A port
    SW_IP_STR = "192.168.1.101"     # SW1001 IP addr
    SW_PORT = 23                    # SW1001 port

    # 1. Create an instance of DAQ970A class
    hioki = HIOKI_DEV(BT_IP_STR, BT_PORT, SW_IP_STR, SW_PORT)

    # 2. IMPORTANT! Set continuous measurement OFF.
    hioki.bt_initiate_continous('OFF')

    sleep(0.1)

    # 3. Do some stuff
    print(hioki.measure_channnel(1))
    
    print(hioki.all_channels_zero_adjustment())


    hioki.bt_initiate_continous('ON')

    # 3. ERRORS 


    # 4. Close connection
    
    print("DONE.")
    
# END OF FILE