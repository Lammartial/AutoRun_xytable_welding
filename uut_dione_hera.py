"""
UUT adapter module for DIONE / HERA.

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
I2C_CMD_Read_UDI = 0x56  # new to Dione / Hera

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

   
    def read_battery_detection_from_uut(self) -> bool:
        return super().read_battery_detection_from_uut()


    def read_battery_measurements_from_uut(self) -> Tuple[float, float]:
        return super().read_battery_measurements_from_uut()
    
    
    def read_charger_measurements_from_uut(self) -> Tuple[float, float, float, float]:
        """Read charger measurements from UUT.

        Note: Dione/Hera reads two more values as MiniCharger

        Returns:
            Tuple[float, float]: VIN in volts, T in Celsius, V_SYS in volts, I_Adapter in amperes
        """

        #self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_CHG_Values, 9)        
        #self.cpu.I2C_Master_set_PEC(1)
        VIN = unpack_from(">H", buf, 1)[0] / 1e+3  # data come big endian
        V_SYS = unpack_from(">H", buf, 3)[0] / 1e+3  # data come big endian
        T = unpack_from(">H", buf, 5)[0] / 1e+1    # data come big endian
        I_Adapter = unpack_from(">H", buf, 7)[0] / 1e+3  # data come big endian
        return VIN, T, V_SYS, I_Adapter


    def read_r_sense_from_uut(self) -> float:
        """Reads the UUT's measurement of R_SNS pin of battery.

        Note: Dione/Hera has different resistance factor than MiniCharger.

        Returns:
            float: R sense in ohms.
        """

        #self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_R_SNS_BAT, 3)
        #self.cpu.I2C_Master_set_PEC(1)
        #R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 1e+2  # data come big endian
        R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 10 / 5  # this was the precalc of Hera DLL
        return R_SNS_BAT
    

    def read_r_sense_dc_in_from_uut(self) -> float:
        """Reads the UUT's measurement of R-Sense of DC IN pin.

        Note: This is new function to Dione/Hera.

        Returns:
            float: R sense DC IN in ohms.
        """

        #self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, I2C_CMD_Read_R_SNS_DC_IN, 3)
        #self.cpu.I2C_Master_set_PEC(1)
        #R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 1e+2  # data come big endian
        R_SNS_BAT = unpack_from(">H", buf, 1)[0] / 10 / 5  # this was the precalc of Hera DLL
        return R_SNS_BAT
    

    def read_bq_charge_option(self) -> bytearray:
        return super().read_bq_charge_option()
    

    def set_bq_charge_option(self, onoff: bool) -> bool:
        """_summary_

        Note: This is new function to Dione/Hera.

        Returns:
            bytearray: _description_
        """

        buf = self.read_bq_charge_option()
        if onoff:
            buf[2] |= 0x08
        else:
            buf[2] &= ~0x08
        #self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_BQ_Charge_Option, buf)


    def set_u_bat_i_bat(self, voltage: float, current: float) -> bool:
        """Sets the charger of UUT to charge voltage and chareg current.        

        Args:
            voltage (float): battery voltage limit in V
            current (float): battery current limit in A

        Returns:
            bool: _description_
        """
        
        return super().set_u_bat_i_bat(voltage, current)
    

    def calibrate_r_sns_bat(self, reference_current: float, r_sense_ohm: float = 0.010) -> int:
        """
        Calculates the current calibration value for UUT's battery path and also writes this
        value to the UUT. An uncalibrated measurement of current by UUT is performed as preparation. 

        Args:
            reference_current (float): With high accuracy measured current.
            r_sense_ohm (float, optional): Used sense resistor in *Ohm*. Defaults to 0.010.

        Returns:
            int: Calibration value as it is written into UUT.
        """

        return super().calibrate_r_sns_bat(reference_current, r_sense_ohm=r_sense_ohm)

 
    def calibrate_r_sns_dc_in(self, reference_current: float, r_sense_ohm: float = 0.002) -> int:
        """
        Calculates the current calibration value for UUT's DC IN path and also writes this
        value to the UUT. An uncalibrated measurement of current by UUT is performed 
        as preparation.

        Args:
            reference_current (float): measured reference current in A.
            r_sense_ohm (float, optional): Used sense resistor in *Ohm*. Defaults to 0.002.

        Returns:
            int: calibration ratio value as written to the UUT
        """

        v_in, t, v_sys, i_adapter = self.read_charger_measurements_from_uut()
        calibration_ratio = int(round((i_adapter / reference_current) * r_sense_ohm * 1e+6))
        buf = pack("<B", 2) + pack(">h", calibration_ratio)  # UUT need in big endian signed short int
        #self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_DC_IN, buf):
            return calibration_ratio
        else:
            return -1


    def calibrate_input_current_offset(self, reference_current: float) -> int:
        """
        Calibrates input current measurement offset correction. 
        An measurement of current by UUT is performed as preparation. 
        Thus the calibration of this should be done before.

        Args:
            reference_current (float): measured reference current in A.

        Returns:
            int: Offset as it is written into UUT.
        """

        v_in, t, v_sys, i_adapter = self.read_charger_measurements_from_uut()
        calibration_value = int(round((reference_current - i_adapter) * 1e+3))
        buf = pack("<B", 2) + pack(">h", calibration_value)  # UUT need in big endian signed short int
        #self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_AdapterCurrentOffset, buf):
            return calibration_value
        else:
            return -1



    def toggle_gpio(self, bit: int, onoff: bool) -> bool:  # overwrite inherited function as command code is different
        self._set_gpio_pattern(int(bit), bool(onoff))
        buf = pack("<B", 1) + pack("<B", self.gpio_pattern)
        #self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_GPIOs, buf)


    

    # NEW FUNCTIONS to DIONE / HERA

    def switch_application_on_off(self, state: bool | int | str) -> bool:
        buf = pack("<B", 1) + pack("<B", self._state_to_zero_or_one(state))
        #self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_APP_ON_OFF, buf)


    def set_power_path(self, mode: int) -> bool:
        buf = pack("<B", 1) + pack("<B", mode)
        #self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_APP_ON_OFF, buf)  # uses the same command as APP ON/OFF


    def set_input_current_limit(self, current_limit: float) -> bool:
        _w = int(round(current_limit * 1000))
        buf = pack("<B", 2) + pack(">H", _w)
        #self.cpu.I2C_Master_set_PEC(1)
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_Input_Current_Limit, buf)


    def get_input_current_limit(self) -> float:
        """

        Note: this function uses the second_i2c_address which should be the SmartCharger address (0x14)

        Returns:
            float: Returns the input current limit in A
        """

        #self.cpu.I2C_Master_set_PEC(0)
        w = self.cpu.I2C_Master_ReadWord(self.second_i2c_address, 63)
        #self.cpu.I2C_Master_set_PEC(1)
        return float(w) * 1e-3


    def reset_calibration(self) -> bool:
        # write the magic keyword into two word addresses
        buf = pack("<B", 2) + pack(">H", 0x1388)
        #self.cpu.I2C_Master_set_PEC(1)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_BAT, buf)
        ok &= self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_R_SNS_DC_IN, buf)
        return ok


    def set_and_verify_udi(self, udi: str) -> bool:
        """Write a string of len 16 into the UUT's EEPROM and read it back with compare.

        Args:
            udi (str): _description_

        Returns:
            bool: _description_
        """

        if len(udi) != 16:
            raise ValueError(f"Length of UDI string is '{len(udi)}' which is not 16.")
        buf = pack("<B", 16) + udi.encode("utf-8")
        #self.cpu.I2C_Master_set_PEC(0)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_UDI, buf)
        #self.cpu.I2C_Master_set_PEC(1)
        rbbuf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, 0x81, 17)
        if rbbuf[0] != 16:
            raise ValueError(f"Length of readback UDI string is '{rbbuf[0]}' which is not 16.")
        rbstr = bytes(rbbuf[1:]).decode("utf-8")
        if rbstr != udi:
            raise ValueError(f"Readback UDI string is different from exprected one.")
        return True


    def get_udi(self) -> str:
        #
        # read UDI as string.
        #
        #self.cpu.I2C_Master_set_PEC(1)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, 0x81, 17)
        if len(buf) != 17:
            raise ValueError(f"Expected 17 bytes for UDI, got '{len(buf)}'")
        return bytes(buf[1:]).decode("utf-8")


#--------------------------------------------------------------------------------------------------

def test_myself():
    from rrc.track.chroma import DC63600
    from rrc.track.tdklambda import DCZPlus
    from rrc.keysight import AGILENT34972A, DAQ970A, daq_class_selector
    load1 = DC63600("192.168.31.103:2101", channel=1)
    print(load1.ident())
    load1.initialize_device()
    load2 = DC63600("192.168.31.103:2101", channel=2)
    print(load2.ident())
    load2.initialize_device()
    psu1 = DCZPlus("192.168.31.101:8003", channel=1)
    print(psu1.ident())
    psu1.initialize_device()
    psu2 = DCZPlus("192.168.31.101:8003", channel=2)
    print(psu2.ident())
    psu2.initialize_device()
    daq = daq_class_selector("192.168.31.106:5025", 1)
    #daq = AGILENT34972A("192.168.31.106:5025", card_slot=1)    
    print(daq.ident())
    #daq.send("*RST")
    #sleep(0.5)    
    #daq.send("MEAS:TEMP:FRTD? 100,(@106)")
    daq.wait_response_ready()
    # daq.send("SENS:TEMP:TRAN:FRTD:TYPE 85,(@106)")
    print(daq.read_error_status())
    # daq.send("SENS:TEMP:TRAN:FRTD:RES 100,(@106)")
    # print(daq.read_error_status())
    # print(daq.request("MEAS:TEMP? FRTD,85,(@106)"))
    # print(daq.read_error_status())
    # print(daq.get_temp_rounded(6, "FRTD", 100, 0, "", 2))

    #print(daq.selftest())      
    dev = UUT_Dione_Hera(0x33, 0x09, resource_str="COM3,115200,8N1")
    print(dev.cpu.ident())
    dev.initialize_cpu_ports()    
    #psu1.set_output(0)
    #sleep(2)
    psu1.set_voltage(24.0)
    psu1.set_current_limit(1.0)
    psu1.set_output(1)
    sleep(0.5)
    for port in "AC":
        print(f"Port {port} Status: ", dev.cpu.IO_Get_Portstatus(port))
        for bit in range(8):
            print(f"Read Port {port}, bit {bit}:", dev.cpu.IO_Read_Port_bit(port, bit))
    print(dev.is_adapter_correctly_connected())
    print("VCC:", daq.get_VDC_rounded(3,3))
    print("TP_V_SYSM:", daq.get_VDC_rounded(4,3))
    print("TP_VIN_M:", daq.get_VDC_rounded(5,3))
    print("TEMP:",daq.get_temp_rounded(6, "FRTD", 100, 0, "", 2))
    print(dev.reset_calibration())
    print(dev.set_and_verify_udi("1234567890123456"))
    print(psu1.set_voltage(16.0))
    print(psu1.set_current_limit(4.0))
    print(psu1.set_output(1))
    print(load2.set_load_output(0))
    print(load2.set_load_mode("CCH"))
    print(load2.set_measure_sense_to("UUT"))    
    print(load2.activate_device_display())
    print(load2.measure_voltage())
    print(load2.measure_current())
    print(dev.read_battery_measurements_from_uut())
    print(dev.read_charger_measurements_from_uut())    
    print(dev.switch_application_on_off(0))
    dev.set_u_bat_i_bat(0, 0)  # dummy action, next one will set correctly
    print(load2.set_load_mode("CRL"))
    print(load2.get_load_mode())
    print(load2.set_load_output(1))
    load2.set_load_resistance(10.0)    
    load2.set_load_resistance(5.0)
    load2.set_load_resistance(3.0)
    #dev.set_u_bat_i_bat(12.05, 3.6)
    #print("Startup with 0 load")
    #print(load2.set_load_current(0))
    #print(load2.set_load_output(1))
    for c in [0,50,10,4,2,1]:
        # set next current
        cc = 3.6
        dev.set_u_bat_i_bat(12.05, cc)
        _nc: float = (cc / c) if c > 0 else 0
        print(f"Set current {_nc:.3f}A")
        load2.set_load_current(_nc)
        load2.set_load_output(1)                
        sleep(0.75)
        #print(dev.read_battery_measurements_from_uut())
        #print(dev.read_charger_measurements_from_uut())
        print(f"{load2.measure_voltage():.3f}")
        print(f"{load2.measure_current():.4f}")
        #print(load1.measure_voltage())
        #print(load1.measure_current())
        load2.set_load_output(0)
    
    # OFF
    print(load2.set_load_output(0))
    print(load1.set_load_output(0))
    print(psu2.set_output(0))
    print(psu1.set_output(0))
    




#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   # quick test, just call: python uut_dione_hera.py
   test_myself()


# END OF FILE