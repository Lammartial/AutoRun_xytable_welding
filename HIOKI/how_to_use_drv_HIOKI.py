from drv_HIOKI import HIOKI_DEV

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    BT_IP_STR = "192.168.1.202"     # BT3561A IP addr
    BT_PORT = 23                    # BT3561A port
    SW_IP_STR = "192.168.1.201"     # SW1001 IP addr
    SW_PORT = 23                    # SW1001 port

    # 1. Create an instance of DAQ970A class
    hioki = HIOKI_DEV(BT_IP_STR, BT_PORT, SW_IP_STR, SW_PORT)

    # 2. ==== BT3561A functions ==========================================================================
    # *IDN?
    print('BT3561A ID: ', hioki.BT_get_idn())

    # *RST
    #hioki.BT_set_reset()

    # *TST?
    print('BT3561A TEST: ', hioki.BT_self_test())

    # Set function 'RV'
    hioki.BT_set_function('RV')

    # Get function 
    print('BT3561A Func: ', hioki.BT_get_function())

    # Set resistance range 0.1 Ohm
    hioki.BT_set_resistance_range(0.1)

    # Get resistance range
    print('BT3561A Resistance Range: ', hioki.BT_get_resistance_range())

    # Set voltage range 6 V
    hioki.BT_set_voltage_range(6)

    # Get voltage range 
    print('BT3561A Voltage Range: ', hioki.BT_get_voltage_range())

    # Set auto range ON
    hioki.BT_set_autorange(1)

    # Get auto range 
    print('BT3561A Auto Range : ', hioki.BT_get_autorange())

    # Adjust zero, 0 - success
    #print('BT3561A Zero Adjustment: ', hioki.BT_set_adjustment())

    # Adjust clear 
    hioki.BT_set_adjustment_clear()

    # System calibration 
    hioki.BT_set_syst_calibration()

    # System calibration auto 1 - ON, 0 - OFF 
    hioki.BT_set_syst_calibration_auto(0)

    # Get system key lock
    print('BT3561A Key Lock: ', hioki.BT_get_syst_klock())

    # Set system key lock OFF
    hioki.BT_set_syst_klock(0)

    # System Local
    hioki.BT_set_local_control()

    # Set trigger source
    hioki.BT_set_trigger_source('IMM')

    # Get trigger source 
    print('BT3561A trig source: ', hioki.BT_get_trigger_source())

    # =============== READ? ============================

    # IMPORTANT! Set continuous measurement OFF.
    hioki.BT_set_continous_measurement('OFF')

    sleep(0.1)

    print('BT3561A measurement ', hioki.BT_read())

    hioki.BT_set_continous_measurement('ON')

    # 3. ==== SW1001 functions ===========================================================================
    
    # *IDN?
    print('SW1001 ID: ', hioki.SW_get_idn())

    # *RST
    #hioki.SW_set_reset()

    # *TST?
    #print('SW1001 Self Test: ', hioki.SW_self_test())

    # Raw query command
    #print('SW1001 Get Scan List: ', hioki.SW_set_raw_query(':SCAN?'))
    
    # Raw command
    #hioki.SW_set_raw_command(':SYST:MOD:SHI 1,GND')
 
    # IMPORTANAT! Switching the channel:
    # 1. Set wire mode
    #hioki.SW_set_wire_mode(1, 4)
    # 2. Set shield mode (if needed)
    #hioki.SW_set_shield_mode(1, 'TERM2')
    # 3. CLOSE channel
    #hioki.SW_close(1, 1)

    #print('SW1001 Slot1 Wire Mode: ', hioki.SW_get_wire_mode(1))
    #print('SW1001 Slot1 Shield Mode: ', hioki.SW_get_shield_mode(1))

    # Get module count
    #print('SW1001 Slot1 Count: ', hioki.SW_get_module_count(1))
    #print('SW1001 Slot2 Count: ', hioki.SW_get_module_count(2))

    # CLOSE channel
    #hioki.SW_close(1, 1)

    # OPEN
    #hioki.SW_open()

    # 4. ==== Cells tester (BT3561A + SW1001) functions ================================================

    # IMPORTANT! Set continuous measurement OFF.
    hioki.BT_set_continous_measurement('OFF')

    sleep(0.1)

    # measure single channel (1 ... 22)
    #print(hioki.measure_channnel(15))
    
    # measure all 22 4-wire channels (Could be useful for Zero-adjustment procedure)
    print(hioki.measure_all_channels())

    hioki.SW_open()

    hioki.BT_set_continous_measurement('ON')
    
    print("DONE.")
    
# END OF FILE