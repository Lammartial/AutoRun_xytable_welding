from drv_FEASA import FEASA_DEV

if __name__ == "__main__":
    from time import sleep

    # Use LAN connection and "Net Module Configure" software to check CH9121 parameters:
    # 1. LAN parameters of CH9121: TCP SERVER mode, PORT1 (IP address, port number1), PORT2 (IP address, port number2)
    # 2. UART parameters of CH9121 (baudrate 57600, Data bits 8, Stop bit 1)

    # Check FEASA LED ANALYSER RS232 settings. Default: baudrate 57600, Data bits 8, Stop bit 1

    CH9121_IP_STR = "192.168.1.90" 
    # Channel 1
    CH9121_PORT_STR = 2000
    # Channel 2
    #CH9121_PORT_STR = 3000

    # 1. Create an instance of ITECH_DEV class
    feasa = FEASA_DEV(CH9121_IP_STR, CH9121_PORT_STR)

    # 2. Get some data

    # "CAPTURE" command
    print(feasa.capture())

    # "CAPTURE#" command
    print(feasa.capture_range(1))

    # "CAPTUREPWM" command
    #print(feasa.capture_pwm())

    # "CAPTURE#PWM@@" command
    #print(feasa.capture_pwm_range(1, 7))

    # "getRGBI##" command
    print(feasa.get_rgbi_num(1))

    # "getINTENSITY##" command
    print(feasa.get_intensity_num(1))

    # "SetIntGain##xxx" command
    print(feasa.set_intgain_num(1, 100))

    # SetFactor## command
    print(feasa.set_factor(1))

    print("DONE.")
    
# END OF FILE