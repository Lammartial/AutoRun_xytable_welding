"""
UUT adapter module for MiniCharger:

simplifies CPU card configurations and more complex tasks
which would be to unhandy implementing them in Teststand

VERSION WHEN        WHO  WHAT
-------------------------------------------------------------------------------
0.1.0   2025-01-19  MR   initially created from C# DLLs


"""

from typing import Tuple
from time import sleep
from struct import pack, unpack, unpack_from
from rrc.track import CPU_Card


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

# I2C_Write_commands
I2C_CMD_Write_BAT_V_I_limit = 0x40
I2C_CMD_Write_BQ_Charge_Option = 0x41
I2C_CMD_Write_R_SNS_BAT = 0x42
I2C_CMD_Write_GPIOs = 0x43

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class UUT_MiniCharger:

    def __init__(self, i2c_address_7bit: int, resource_str: str = None, cpu_reference: CPU_Card = None) -> None:
        if cpu_reference:
            self.cpu = cpu_reference
        else:
            # need to create by our own
            self.cpu = CPU_Card(resource_str)
        self.i2c_address = int(i2c_address_7bit) << 1
        self.gpio_pattern = 0


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

        self.cpu.I2C_Master_set_PEC(1)  # use PEC by default. This is the only good place to put it


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


    def _state_to_zero_or_one(self, state: int | bool | str) -> int:
        if isinstance(state, (int, float)) and int(state) > 0:
            _v = 1
        elif isinstance(state, (bool)) and (state == True):
            _v = 1
        elif isinstance(state, str) and state.upper() == "ON":
            _v = 1
        else:
            _v = 0  # OFF, 0 or False
        return _v


    def set_i2c_5v_bus(self, state: bool | int | str) -> bool:
        return self.cpu.IO_Write_Port_bit("A", 2, self._state_to_zero_or_one(state))


    def set_bat_ntc_300_ohm(self, onoff: bool) -> bool:
        return self.cpu.IO_Write_Port_bit("A", 1, 0 if onoff else 1)  # inverted logic


    def set_uut_into_testmode(self, onoff: bool) -> bool:
        return self.cpu.IO_Write_Port_bit("A", 0, 1 if onoff else 0)


    def read_battery_detection_from_uut(self) -> bool:
        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Detection, 2)
        self.cpu.I2C_Master_set_PEC(1)
        return (buf[1] == 1)


    def read_battery_measurements_from_uut(self) -> Tuple[float, float]:
        """_summary_

        Returns:
            Tuple[float, float]: voltage in volts, current in amps
        """
        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Values, 5)
        self.cpu.I2C_Master_set_PEC(1)
        voltage = float(unpack_from(">H", buf, 1)[0]) / 1e+3  # data come big endian
        current = float(unpack_from(">H", buf, 3)[0]) / 1e+3  # data come big endian
        return voltage, current


    def read_charger_measurements_from_uut(self) -> Tuple[float, float]:
        """_summary_

        Returns:
            Tuple[float, float]: VIN in volts, T in Celsius.
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_CHG_Values, 5)
        self.cpu.I2C_Master_set_PEC(1)
        VIN = float(unpack_from(">H", buf, 1)[0]) / 1e+3  # data come big endian
        T   = float(unpack_from(">H", buf, 3)[0]) / 1e+1    # data come big endian
        return VIN, T


    def read_r_sense_from_uut(self) -> float:
        """Reads the UUT's measurement of R_SNS pin of battery.

        Returns:
            float: R sense in ohms.
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_R_SNS_BAT, 3)
        self.cpu.I2C_Master_set_PEC(1)
        R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 1e+2  # data come big endian
        return R_SNS_BAT


    def read_bq_charge_option(self) -> bytearray:
        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_BQ_Charge_Option, 3)
        self.cpu.I2C_Master_set_PEC(1)
        return buf


    def set_u_bat_i_bat(self, voltage: float, current: float) -> bool:
        """Sets the charger of UUT to charge voltage and chareg current.        

        Args:
            voltage (float): battery voltage limit in V
            current (float): battery current limit in A

        Returns:
            bool: _description_
        """

        ubat: int = int(round(voltage * 1e+3))
        ibat: int = int(round(current * 1e+3))
        buf = pack("<B", 4) + pack(">H", ubat) + pack(">H", ibat)  # need big endian
        self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_BAT_V_I_limit, buf)
    

    def _set_gpio_pattern(self, bit: int, logic: bool) -> None:
        self.gpio_pattern = (self.gpio_pattern | (1 << bit)) if logic else (self.gpio_pattern & ~(1 << bit))


    def toggle_gpio(self, bit: int, onoff: bool) -> bool:
        self._set_gpio_pattern(int(bit), bool(onoff))
        buf = pack("<B", 1) + pack("<B", self.gpio_pattern)
        self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_GPIOs, buf)


    def calibrate_r_sns_bat(self, reference_current: float) -> int:
        """_summary_

        Args:
            reference_current (float): measured reference current in A

        Returns:
            int: calibration ratio value as written to the UUT
        """

        u_bat, i_bat = self.read_battery_measurements_from_uut()
        calibration_ratio = int(round(((i_bat / reference_current) * 1e+3))) * 10
        buf = pack("<B", 2) + pack(">h", calibration_ratio)  # UUT need in big endian signed short int
        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_BAT, buf):
            return calibration_ratio
        else:
            return -1


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   pass


# END OF FILE