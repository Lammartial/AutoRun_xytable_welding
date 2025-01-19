"""
UUT adapter module for DIONE:

simplifies CPU card configurations and more complex tasks
which would be to unhandy implementing them in Teststand

VERSION WHEN        WHO  WHAT
-------------------------------------------------------------------------------
0.1.0   2025-01-19  MR   initially created from C# DLLs of Dione GUI 2015-08-26

"""

from typing import Tuple
from time import sleep
from struct import pack, unpack, unpack_from
from rrc.track import CPU_Card
from rrc.uut_mini_charger import UUT_MiniCharger

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.1.0"

__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


# I2C_Read_commands
I2C_CMD_Read_Bat_Detection = 0x50
I2C_CMD_Read_Bat_Values = 0x51
I2C_CMD_Read_CHG_Values = 0x52
I2C_CMD_Read_BQ_Charge_Option = 0x53
I2C_CMD_Read_R_SNS_BAT = 0x54
I2C_CMD_Read_R_SNS_DC_IN = 0x55  # new to Dione

# I2C_Write_commands
I2C_CMD_Write_BAT_V_I_limit = 0x40
I2C_CMD_Write_BQ_Charge_Option = 0x41
I2C_CMD_Write_R_SNS_BAT = 0x42
I2C_CMD_Write_R_SNS_DC_IN = 0x43  # new to Dione
I2C_CMD_Write_GPIOs = 0x44        # different to Dione
I2C_CMD_Write_APP_ON_OFF = 0x45   # new to Dione
I2C_CMD_Write_Input_Current_Limit = 0x46  # new to Dione



#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class UUT_Dione(UUT_MiniCharger):
    """Dione is using much of the MiniCharger UUT base.

    Args:
        UUT_MiniCharger (_type_): _description_
    """

    def __init__(self, i2c_address: int, resource_str: str = None, cpu_reference: CPU_Card = None) -> None:
        super().__init__(i2c_address, resource_str=resource_str, cpu_reference=cpu_reference)


    def initialize_cpu_ports(self) -> None:
        super().initialize_cpu_ports()  # this is fix for Teststand missing inheritance


    def is_adapter_correctly_connected(self) -> Tuple[bool, str]:
        return super().is_adapter_correctly_connected()


    def is_adapter_closed(self):
        return super().is_adapter_closed()


    def set_i2c_5v_bus(self, state):
        return super().set_i2c_5v_bus(state)


    def set_bat_ntc_300R(self, onoff):
        return super().set_bat_ntc_300R(onoff)
    

    def set_uut_into_testmode(self, onoff):
        return super().set_uut_into_testmode(onoff)


    def read_battery_detection_from_uut(self):
        return super().read_battery_detection_from_uut()


    def read_battery_measurements_from_uut(self):
        return super().read_battery_measurements_from_uut()


    def read_r_sense_from_uut(self):
        return super().read_r_sense_from_uut()
    

    def read_bq_charge_option(self):
        return super().read_bq_charge_option()
    

    def set_u_bat_i_bat(self, voltage, current):
        return super().set_u_bat_i_bat(voltage, current)


    def toggle_gpio(self, bit: int, onoff: bool) -> bool:  # overwrite inherited function as command code is different
        self._set_gpio_pattern(bit, onoff)
        buf = pack("<b", 1) + pack("<b", self.gpio_pattern)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_GPIOs, buf)


    def calibrate_R_SNS_BAT(self, reference_current):
        return super().calibrate_R_SNS_BAT(reference_current)


    # NEW FUNCTIONS to DIONE

    def switch_application_on_off(self, state: bool | int | str) -> bool:
        buf = pack("<b", 1) + pack("<b", self._state_to_zero_or_one(state))
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_APP_ON_OFF, buf)


    def set_input_current_limit(self, current_limit: float) -> bool:
        _w = int(round(current_limit * 1000))
        buf = pack("<b", 2) + pack("<H", _w)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_Input_Current_Limit, buf)


    def reset_calibration(self) -> bool:
        # write the magic keyword into two word addresses
        buf = pack("<b", 2) + pack("<H", 0x1388)
        self.cpu.I2C_Master_set_PEC(1)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_BAT, buf)
        ok &= self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_DC_IN, buf)
        return ok


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   pass


# END OF FILE