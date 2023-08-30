from rrc.keysight import DAQ970A
from rrc.eth2serial import Eth2SerialDevice
from time import sleep


#--------------------------------------------------------------------------------------------------

def do_tests(daq970a):
    res : float = 0

    print(daq970a.selftest())

    res = daq970a.get_resistance(5)
    print(res)

    #print(daq970a.get_4w_resistance(1,2))

    #print(daq970a.get_VDC(1,3))

    #print(daq970a.get_VAC(1,4))

    # for i in range(50):
    #     print(daq970a.get_temp(channel=3,tran_type="FRTD", rtd_resist= 1000, fth_type= 0, tc_type=""))
    #     print(daq970a.get_ADC(channel= 22, scale= "1 mA"))
    #     print(daq970a.get_VDC(channel=20))

    # #print(daq970a.get_temp(1, 1, "DEF", 0, 0, "B"))


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    #LINE_NETWORK = "172.25.101"  # VN line 1
    LINE_NETWORK = "172.21.101"  # HOM Warehouse

    RESOURCE_STR = f"{LINE_NETWORK}.36:5025"  # port 5025 is default of DAQ970
    RESOURCE_VISA_STR = f"TCPIP0::{LINE_NETWORK}.36::inst0::INSTR"
   
    # 1. Create an instance of DAQ970A class
    chn = 1  # = socket index + 1
    dev = DAQ970A(RESOURCE_STR, chn)
    print(dev.request("*IDN?"))
    
    do_tests(dev)

#--------------------------------------------------------------------------------------------------

# END OF FILE