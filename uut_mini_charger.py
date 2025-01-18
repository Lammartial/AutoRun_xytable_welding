"""
UUT adapter module: simplifies CPU card configurations and more complex tasks 
which would be to unhandy implementing them in Teststand 
"""

from typing import Tuple
from time import sleep
from struct import pack, unpack, unpack_from
from rrc.track import CPU_Card


# I2C_Read_commands        
I2C_CMD_Read_Bat_Detection = 0x50
I2C_CMD_Read_Bat_Values = 0x51
I2C_CMD_Read_CHG_Values = 0x52
I2C_CMD_Read_BQ_Charge_Option = 0x53
I2C_CMD_Read_R_SNS_BAT = 0x54

# I2C_Write_commands
I2C_CMD_Write_BAT_V_I_limit = 0x40
I2C_CMD_Write_BQ_Charge_Option = 0x41
I2C_CMD_Write_R_SNS_BAT = 0x42
I2C_CMD_Write_GPIOs = 0x43
        
class UUT_MiniCharger:

    def __init__(self, i2c_address: int, resource_str: str = None, cpu_reference: CPU_Card = None):
        if cpu_reference:
            self.cpu = cpu_reference
        else:
            # need to create by our own
            self.cpu = CPU_Card(resource_str)
        self.i2c_address = i2c_address << 1

        
    def initialize_cpu_ports(self) -> None:
        self.cpu.IO_Set_Cfg_Pin("A", 0, 2);           # Open Collector: Connected to TPTEST
        #sleep(0.02)    
        self.cpu.IO_Set_Cfg_Pin("A", 1, 2);           # Open Collector: Connected to TPBATNTC
        self.cpu.IO_Set_Cfg_Pin("A", 2, 1);           # Output: Connected to TPSMBVCC
        self.cpu.IO_Set_Cfg_Pin("C", 0, 0);           # Input: To check whether adapter is closed
        self.cpu.IO_Set_Cfg_Pin("C", 1, 0);           # Channel detection TrackMini Channel 1.1 power
        self.cpu.IO_Set_Cfg_Pin("C", 2, 0);           # Channel detection TrackMini Channel 1.2 power
        self.cpu.IO_Set_Cfg_Pin("C", 3, 0);           # Channel detection TrackMini Channel 2.1 power
        self.cpu.IO_Set_Cfg_Pin("C", 4, 0);           # Channel detection TrackMini Channel 2.2 power
        self.cpu.IO_Set_Cfg_Pin("C", 5, 1);           # Channel detection TrachMini Channel 1 datalogger

        self.cpu.IO_Write_Port_bit("A", 0, 1)         # TPTEST released = HIGH
        self.cpu.IO_Write_Port_bit("A", 1, 1)         # TPBATNTC released
        self.cpu.IO_Write_Port_bit("A", 2, 1)         # I2C-Bus Voltage 5V
        self.cpu.IO_Write_Port_bit("C", 5, 1)         # Signal which is checked with dataloger for channel identification


    def is_adapter_correctly_connected(self) -> Tuple[bool, str]:
        _VERIFY_PATTERN = (
            # port, pin, expected value, error info
            ("C", 1, 0, "Power cables not connected correctly"),
            ("C", 2, 0, "Check 5V regulator of TrackMini"),
            ("C", 3, 1, "Power cable 2 is not connected correctly"),
            ("C", 4, 1, "Check 5V regulator of TrackMini"),
        )
        for (port, pin, v, error_text)  in _VERIFY_PATTERN:
            if self.cpu.IO_Read_Port_bit(port, pin) != v:
                return False, error_text
        return True, "Setup correct"
    

    def is_adapter_closed(self) -> bool:
        return (self.cpu.IO_Read_Port_bit("C", 0) == 0) 


    def set_i2c_5v_hv(self, state: int | str) -> bool:
        if isinstance(state, str) and state.upper() == "ON":
            _v = 1
        elif isinstance(state, (int, float)) and int(state) > 0:
            _v = 1
        else:
            _v = 0
        return self.cpu.IO_Write_Port_bit("A", 2, _v)


    def set_bat_ntc_300R(self, onoff: bool) -> bool:
        return self.cpu.IO_Write_Port_bit("A", 1, 0 if onoff else 1)  # inverted logic


    def set_uut_into_testmode(self, onoff: bool) -> bool:
        return self.cpu.IO_Write_Port_bit("A", 0, 1 if onoff else 0)


    def read_battery_detection_from_uut(self) -> bool:
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Detection, 2)
        return (buf[1] == 1)

    def read_battery_measurements_from_uut(self) -> Tuple[float, float]:
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Values, 5)
        voltage = unpack_from("<H", buf, 1)[0] / 1000 # data come litte endian
        current = unpack_from("<H", buf, 3)[0] / 1000 # data come litte endian
        return voltage, current



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   pass


# END OF FILE