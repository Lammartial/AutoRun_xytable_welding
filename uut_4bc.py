"""
UUT adapter module for 4BC.

simplifies CPU card configurations and more complex tasks
which would be to unhandy implementing them in Teststand

VERSION WHEN        WHO  WHAT
-------------------------------------------------------------------------------
0.1.0   2025-04-15  MSm  created using dione_hera and mini_charger python libs

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
I2C_CMD_Read_UDI = 0x56  # new to Dione / Hera
I2C_CMD_Read_Button_State = 0x57

# I2C_Write_commands
I2C_CMD_Write_BAT_V_I_limit = 0x40
I2C_CMD_Write_BQ_Charge_Option = 0x41
I2C_CMD_Write_R_SNS_BAT = 0x42
I2C_CMD_Write_R_SNS_DC_IN = 0x43  # new to Dione
I2C_CMD_Write_GPIOs = 0x44        # different to Dione
I2C_CMD_Write_APP_ON_OFF = 0x45   # new to Dione
I2C_CMD_Write_Input_Current_Limit = 0x46  # new to Dione
I2C_CMD_Write_UDI = 0x47  # new to Dione / Hera
I2C_CMD_Write_AdapterCurrentOffset = 0x48  # new to Dione / Hera
I2C_CMD_Write_ChargePump = 0x49  # new to Dione / Hera
I2C_CMD_Write_Bay_FETs = 0x4A
I2C_CMD_Write_I2CMUX = 0x4B

BAY_1 = 1
BAY_2 = 2
BAY_3 = 3
BAY_4 = 4
BAYS = [BAY_1, BAY_2, BAY_3, BAY_4]

CHARGER_1 = 1
CHARGER_2 = 2
[CHARGER_1, CHARGER_2]

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class UUT_Dione_Hera(UUT_MiniCharger):
    """Dione is using much of the MiniCharger UUT base.
    Hera extends the Dione functionality a bit more.

    Args:
        UUT_MiniCharger (_type_): _description_
    """

    def __init__(self, i2c_address_7bit: int, second_i2c_address_7bit: int, resource_str: str = None, cpu_reference: CPU_Card = None) -> None:
        """_summary_

        Args:
            i2c_address_7bit (int): Should be SmartCharger Address (0x10)
            second_i2c_address_7bit (int): Secondary address, should be the SmartCharger address (0x14)
            resource_str (str, optional): _description_. Defaults to None.
            cpu_reference (CPU_Card, optional): _description_. Defaults to None.
        """
        super().__init__(i2c_address_7bit, resource_str=resource_str, cpu_reference=cpu_reference)
        self.second_i2c_address = int(second_i2c_address_7bit) << 1  # used to read input current limit from SmartCharger Address (0x14)
        self.i2c_address_mux_testsystem = 0x71


    def initialize_cpu_ports(self) -> None:
        super().initialize_cpu_ports()  # this is fix for Teststand missing inheritance


    def is_adapter_correctly_connected(self) -> Tuple[bool, str]:
        return super().is_adapter_correctly_connected()


    def is_adapter_closed(self) -> bool:
        return super().is_adapter_closed()


    def set_i2c_5v_bus(self, state: bool | int | str) -> bool:
        return super().set_i2c_5v_bus(state)


    def set_bat_ntc_300_ohm(self, onoff) -> bool:
        return super().set_bat_ntc_300_ohm(onoff)


    def set_uut_into_testmode(self, onoff) -> bool:
        return super().set_uut_into_testmode(onoff)


    def read_battery_detection_from_uut(self, bay_ID: int) -> bool:
        """ Checks if a battery is present in the specified bay.

        Args: bay_ID (int): The bay that should be checked. Either 1, 2, 3 or 4

        Returns:
            bool: True if a battery is present, false if not.
        """
        if bay_ID not in BAYS:
            return False

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Detection, 5)
        self.cpu.I2C_Master_set_PEC(1)
        return (buf[bay_ID] == 1)


    def read_battery_measurements_from_uut(self, bay_ID: int, charger_ID: int) -> Tuple[float, float]:
        """ Reads the ADC measurements for voltage and current of a given bay and charger

        Args:
            bay_ID (int): The bay for the battery voltage. Either 1, 2, 3 or 4
            charger_ID (int): The charger for the battery current. Either 1 or 2

        Returns:
            Tuple[float, float]: voltage in volts, current in amps
        """

        if charger_ID not in CHARGERS:
            return False

        if bay_ID not in BAYS:
            return False

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_Bat_Values, 13)
        self.cpu.I2C_Master_set_PEC(1)

        offset_voltage = (bay_ID - 1) * 2
        offset_current = ((charger_ID - 1) * 2) + 8

        voltage = unpack_from(">H", buf, offset_voltage)[0] / 1e+3  # data come big endian
        current = unpack_from(">H", buf, offset_current)[0] / 1e+3  # data come big endian
        return voltage, current


    def read_charger_measurements_from_uut(self) -> Tuple[float, float, float, float, float]:
        """Read charger ADC measurements from UUT.


        Returns:
            Tuple[float, float, float, float, float]: VIN in volts, temperature of charger 1 in °C, temperature of charger 2 in °C, Input current of charger 1 in A, input current of charger 2 in A
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_CHG_Values, 11)
        self.cpu.I2C_Master_set_PEC(1)
        VIN = unpack_from(">H", buf, 1)[0] / 1e+3  # data come big endian
        T_Fet_charger1 = unpack_from(">H", buf, 3)[0] / 1e+1  # data come big endian
        T_Fet_charger2 = unpack_from(">H", buf, 5)[0] / 1e+1    # data come big endian
        I_input_charger1 = unpack_from(">H", buf, 7)[0] / 1e+3  # data come big endian
        I_input_charger2 = unpack_from(">H", buf, 9)[0] / 1e+3  # data come big endian
        return VIN, T_Fet_charger1, T_Fet_charger2, I_input_charger1, I_input_charger2


    def get_r_sense_battery_from_uut(self, charger_ID: int) -> float:
        """Reads the stored Rsense value of the given charger.

        Args:
            charger_ID (int): The charger to read the Rsense value from. Either 1 or 2.

        Returns:
            float: R sense in ohms.
        """

        if charger_ID not in CHARGERS:
            return False

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_R_SNS_BAT, 5)
        self.cpu.I2C_Master_set_PEC(1)

        if charger_ID == 1:
            R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 1000
        elif charger_ID == 2:
            R_SNS_BAT = unpack_from(">H", buf, 3)[0] / 1000

        return R_SNS_BAT


    def set_u_bat_i_bat(self, voltage: float, current: float, charger_ID: int) -> bool:
        """Sets the charger of UUT to charge voltage and charge current.

        Args:
            voltage (float): target voltage in V
            current (float): target current in A
            charger_ID (int): 1 for charger 1 (left) or 2 for charger 2 (right)

        Returns:
            bool: Result of I2C transfer
        """

        if charger_ID not in CHARGERS:
            return False

        ubat: int = int(round(voltage * 1e+3))
        ibat: int = int(round(current * 1e+3))
        buf = pack("<B", 5) + pack(">H", ubat) + pack(">H", ibat) + pack(">B", charger_ID)  # need big endian
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_BAT_V_I_limit, buf)


    def calibrate_r_sns_bat_generic(self, actual_current_A: float, r_sense_nominal_Ohm: float, charger_ID) -> int:
        """ Calibrates the current measurement of the given charger.

        Args:
            actual_current_A (float): The actual, real current in Ampere measured by the test system.
            r_sense_nominal_Ohm (float): The nominal value of the sense resistance in Ohm.
            charger_ID (int): ID of the charger that should be calibrated. Either 1 or 2.

        Returns:
            int: calibration ratio value as written to the UUT
        """

        if charger_ID not in CHARGERS:
            return False

        _, i_bat_A = self.read_battery_measurements_from_uut(BAY_1, charger_ID)
        r_sense_calibrated_mOhm = int(round((i_bat_A / actual_current_A) * r_sense_nominal_Ohm * 1e+6))

        buf = pack("<B", 3) + pack(">H", r_sense_calibrated_mOhm) + pack(">B", charger_ID)

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_BAT, buf):
            return r_sense_calibrated_mOhm
        else:
            return -1


    def reset_calibration(self, r_sense_nominal_ohm: float) -> bool:
        buf = pack("<B", 2) + pack(">H", r_sense_nominal_ohm)
        self.cpu.I2C_Master_set_PEC(1)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_BAT, buf)
        ok &= self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_DC_IN, buf)
        return ok


    def set_udi(self, udi: str) -> bool:
        """Write the UUT's UDI. Must be 16 characters long. Only ASCII characters

        Args:
            udi (str): UDI as a string. 16 characters long. ASCII only

        Returns:
            bool: True
        """

        if len(udi != 16):
            raise ValueError(f"Length of UDI string is '{len(udi)}' which is not 16.")
        if not isascii(udi):
            raise ValueError(f"The UDI string may only consist of ASCII characters. \"{udi}\"")

        buf = pack("<B", 16) + udi.encode("ascii")

        self.cpu.I2C_Master_set_PEC(1)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_UDI, buf)
        self.cpu.I2C_Master_set_PEC(2)
        rbbuf = self.cpu.I2C_Master_ReadBytes(self.second_i2c_address, 0x81, 17)  # what command is it ?
        if rbbuf[0] != 16:
            raise ValueError(f"Length of readback UDI string is '{rbbuf[0]}' which is not 16.")
        rbstr = bytes(rbbuf[1:]).decode("ascii")
        if rbstr != udi:
            raise ValueError(f"Readback UDI string is different from exprected one.")
        return True


    def get_udi(self) -> str:

        self.cpu.I2C_Master_set_PEC(1)
        buf = self.cpu.I2C_Master_ReadBytes(self.second_i2c_address, 0x81, 17)
        if buf[0] != 16:
            raise ValueError(f"Expected 16 bytes for UDI, got '{buf[0]}'")
        udi = buf[1:].decode("ascii")
        return udi

    def set_bay_fets(self, charger_ID: int, bay_ID: int, state: bool) -> bool:
        """Enables or disables the FET between the given charger and bay.
            Does nothing if this FET doesn't exist (e.g. connecting charger 1 to bay 4)

        Args:
            charger_ID (int): 1 for charger 1 (left) or 2 for charger 2 (right)
            bay_ID (int): Either 1, 2, 3 or 4
            state (bool): new state of the FET

        Returns:
            bool: Result of I2C transfer
        """

        if charger_ID not in CHARGERS:
            return False

        if bay_ID not in BAYS:
            return False

        buf = pack("<B", 3) + pack(">B", charger_ID) + pack(">B", bay_ID) + pack(">B", int(state))  # need big endian
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_Bay_FETs, buf)

    def set_I2C_mux_UUT(self, bay_ID: int, state: bool) -> bool:
        """Enables or disables the channel of the given bay in the UUT's I2C mux.

        Args:
            bay_ID (int): Either 1, 2, 3 or 4
            state (bool): new state of the channel

        Returns:
            bool: Result of I2C transfer
        """

        if bay_ID not in BAYS:
            return False

        buf = pack("<B", 2) + pack(">B", bay_ID) + pack(">B", int(state))  # need big endian
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_I2CMUX, buf)


    def set_I2C_mux_TestSystem(self, state_bay1: bool, state_bay2: bool, state_bay3: bool, state_bay4: bool) -> bool:
        """Enables or disables the channel of test system's I2C mux.

        Args:
            state_bay1 (bool): new state of the channel 1
            state_bay2 (bool): new state of the channel 2
            state_bay3 (bool): new state of the channel 3
            state_bay4 (bool): new state of the channel 4

        Returns:
            bool: Result of I2C transfer
        """

        new_control_reg = 0

        if state_bay1:
            new_control_reg |= 1

        if state_bay2:
            new_control_reg |= 2

        if state_bay3:
            new_control_reg |= 4

        if state_bay4:
            new_control_reg |= 8

        buf = pack("<B", new_control_reg)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address_mux_testsystem, 0x00, buf)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   pass


# END OF FILE