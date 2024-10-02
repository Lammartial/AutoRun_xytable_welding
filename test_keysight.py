from rrc.keysight import DAQ970A
from rrc.eth2serial import Eth2SerialDevice
from time import sleep


#--------------------------------------------------------------------------------------------------

def do_tests(daq970a: DAQ970A) -> None:
    res : float = 0

    #print(daq970a.selftest())    

    daq970a.setup_channel_delay_preset(1, "AUTO")
    daq970a.setup_channel_delay_preset("2,3,4,6,7,8,11", 0.005)

    daq970a.setup_voltage_range_and_resolution_preset(1, scale="AUTO", resolution="DEF")
    daq970a.setup_voltage_range_and_resolution_preset("2,3,4,6,7,8,11", scale="10 V", resolution="DEF")

    #res = daq970a.get_resistance(5)
    #print(res)

    #print(daq970a.get_4w_resistance(1,2))

    print(daq970a.get_VDC(11))

    #print(daq970a.get_VAC(1,4))

    # for i in range(50):
    #     print(daq970a.get_temp(channel=3,tran_type="FRTD", rtd_resist= 1000, fth_type= 0, tc_type=""))
    #     print(daq970a.get_ADC(channel= 22, scale= "1 mA"))
    #     print(daq970a.get_VDC(channel=20))

    # #print(daq970a.get_temp(1, 1, "DEF", 0, 0, "B"))

    #daq970a.send("*RST")


def test_set_all_channel_delays():
    
     for c in range(1,23):  # 22 channels per module
        for ch in range(1, 4):
            channel = f"{ch:1}{c:02}"
            try:
                dev.send(f"ROUTe:CHANnel:DELay 0.005,(@{channel})", timeout=1000)
            except TimeoutError as ex:
                print(f"CH {channel}: Cannot configure")


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    #LINE_NETWORK = "172.25.101"  # VN line 1
    LINE_NETWORK = "172.21.101"  # HOM Warehouse

    RESOURCE_STR = f"{LINE_NETWORK}.36:5025"  # port 5025 is default of DAQ970
    RESOURCE_VISA_STR = f"TCPIP0::{LINE_NETWORK}.36::inst0::INSTR"  # VISA not used anymore
   
    # 1. Create an instance of DAQ970A class
    chn = 1  # = socket index + 1
    dev = DAQ970A(RESOURCE_STR, chn)
    # 2. Reset device and get configuration info
    dev.send("*RST")
    for r in [        
        "*IDN?",
        "*ESR?",
        "CALibration:DATE?",
        "CALibration:COUNt?",
        "TRIGger:DELay?",
        ]:
        print(f"{r}:", dev.request(r))
    
    # test_set_all_channel_delays()
    # print(dev.selftest())
    # for r in [
    #     "CONFigure?", 
    #     "ROUTe:CHANnel:DELay?",
    #     ]:  
    #     #_req_list = f"{r} (@{','.join([str(c) for c in range(1,21)])})"
    #     #print(dev.request(_req_list))
    #     for c in range(1,23):  # 22 channels per module
    #         for ch in range(1, 4):
    #             channel = f"{ch:1}{c:02}"
    #             try:
    #                 _response = dev.request(f"{r} (@{channel})", timeout=100)
    #                 print(f"{r} - CH {channel:2}:", _response)
    #             except TimeoutError as ex:
    #                 print(f"{r} - CH {channel:2}: Not configured")
    
    # 3.do some tests        
    do_tests(dev)

#--------------------------------------------------------------------------------------------------

# END OF FILE