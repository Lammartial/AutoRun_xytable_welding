"""
UUT adapter module for Dione (PMM240).

simplifies CPU card configurations and more complex tasks
which would be to unhandy implementing them in Teststand

VERSION WHEN        WHO  WHAT
-------------------------------------------------------------------------------
0.1.0   2026-01-26  MSm  created using uut_4bc.py

"""

from typing import Tuple
from time import sleep
from struct import pack, unpack, unpack_from
from rrc.track import CPU_Card
from rrc.uut_mini_charger import UUT_MiniCharger
from rrc.uut_dione_hera import UUT_Dione_Hera


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
I2C_CMD_Read_R_SNS_DC_IN = 0x55

# I2C_Write_commands
I2C_CMD_Write_BAT_V_I_limit = 0x40
I2C_CMD_Write_BQ_Charge_Option = 0x41
I2C_CMD_Write_R_SNS_BAT = 0x42
I2C_CMD_Write_R_SNS_DC_IN = 0x43
I2C_CMD_Write_GPIOs = 0x44
I2C_CMD_Write_APP_ON_OFF = 0x45
I2C_CMD_Write_Input_Current_Limit = 0x46

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

#class UUT_4bayCharger(UUT_Dione_Hera):
class UUT_Dione(UUT_MiniCharger):
    """Dione is using much of the MiniCharger UUT base.

    Args:
        UUT_MiniCharger (_type_): _description_
    """
    GPIO_pattern = 0

    def __init__(self, i2c_address_7bit: int, resource_str: str = None, cpu_reference: CPU_Card = None) -> None:
        """_summary_

        Args:
            i2c_address_7bit (int): Should be SmartCharger Address (0x10)
            resource_str (str, optional): _description_. Defaults to None.
            cpu_reference (CPU_Card, optional): _description_. Defaults to None.
        """
        super().__init__(i2c_address_7bit, resource_str=resource_str, cpu_reference=cpu_reference)


    def initialize_cpu_ports(self) -> None:
        # Dont call the inherited function. This function is HW specific and might be different for each device.
        # super().initialize_cpu_ports()  # this is fix for Teststand missing inheritance

        self.cpu.IO_Set_Cfg_Pin("A", 0, 2);           # Open Collector: Connected to TPTEST
        self.cpu.IO_Set_Cfg_Pin("A", 7, 2);           # Open Collector: Connected to all T-Pins in parallel

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
        """ Checks if a battery is present in the specified bay.

        Returns:
            bool: True if a battery is present, false if not.
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_Bat_Detection, 2)
        self.cpu.I2C_Master_set_PEC(1)
        return (buf[1] == 1)

    def read_battery_measurements_from_uut(self) -> Tuple[float, float]:
        """ Reads the ADC measurements for voltage and current of a given bay and charger

        Returns:
            Tuple[float, float]: voltage in volts, current in amps
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_Bat_Values, 5)
        self.cpu.I2C_Master_set_PEC(1)

        alles = unpack_from(">HH", buf, 1)

        voltage = alles[0]/1000.0
        current = alles[1]/1000.0

        return voltage, current


    def read_charger_measurements_from_uut(self) -> Tuple[float, float, float, float]:
        """Read charger ADC measurements from UUT.


        Returns:
            Tuple[float, float, float, float]: VIN in volts, VSys in volts, temperature of charger in °C, Input current of charger in A
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_CHG_Values, 9)
        self.cpu.I2C_Master_set_PEC(1)

        alles = unpack_from(">HHHH", buf, 1)

        VIN = alles[0] / 1000  # mV to V
        VSys = alles[1] / 1000  # mV to V
        T_Charger = alles[2] / 10  # 0.1°C to 1°C
        I_adapter = alles[3] / 1000  # mA to A

        return VIN, VSys, T_Charger, I_adapter


    def get_r_sense_battery_from_uut(self) -> float:
        """Reads the stored Rsense value of the battery shunt.

        Returns:
            float: R sense in ohms.
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_R_SNS_BAT, 3)
        self.cpu.I2C_Master_set_PEC(1)

        R_SNS_BAT = float(unpack_from(">H", buf, 1)[0]) / 10.0 / 5.0  # No idea why this is /50. I took the numbers from DIONE.dll

        return R_SNS_BAT


    def get_r_sense_adapter_from_uut(self) -> float:
        """Reads the stored Rsense value of the input current shunt.

        Returns:
            float: R sense in ohms.
        """

        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_R_SNS_DC_IN, 3)
        self.cpu.I2C_Master_set_PEC(1)

        R_SNS_DC_IN = float(unpack_from(">H", buf, 1)[0]) / 10.0 / 5.0  # No idea why this is /50. I took the numbers from DIONE.dll

        return R_SNS_DC_IN


    def set_turbo_boost_mode(self, on_off: bool) -> str:
        self.cpu.I2C_Master_set_PEC(0)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_7bit, I2C_CMD_Read_BQ_Charge_Option, 3)
        if on_off:
            buf[2] |= 0x08
        else:
            buf[2] &= 0xF7

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_BQ_Charge_Option, buf):
            return "OK"
        else:
            return "FAIL set turbo boost mode"


    def set_u_bat_i_bat(self, voltage: float, current: float) -> str:
        """Sets the charger of UUT to charge voltage and charge current.

        Args:
            voltage (float): target voltage in V
            current (float): target current in A

        Returns:
            bool: Result of I2C transfer
        """

        ubat = int(round(voltage * 1e+3))
        ibat = int(round(current * 1e+3))
        buf = pack("<B", 4) + pack(">H", ubat) + pack(">H", ibat)  # need big endian
        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_BAT_V_I_limit, buf):
            return "OK"
        else:
            return "FAIL write U_bat I_bat"


    def calibrate_r_sns_DC_IN(self, actual_current_A: float) -> int:
        """ Calibrates the current measurement of the given charger.

        Args:
            actual_current_A (float): The actual, real current in Ampere measured by the test system.

        Returns:
            int: calibration ratio value as written to the UUT
        """

        _, _, _, i_adapter_A = self.read_charger_measurements_from_uut()
        calibration_value = int(round(i_adapter_A / actual_current_A * 1000.0)) * 5

        buf = pack("<B", 3) + pack(">H", calibration_value)

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_R_SNS_DC_IN, buf):
            return calibration_value
        else:
            return -1


    def calibrate_r_sns_bat(self, actual_current_A: float) -> int:
        """ Calibrates the current measurement of the given charger.

        Args:
            actual_current_A (float): The actual, real current in Ampere measured by the test system.

        Returns:
            int: calibration ratio value as written to the UUT
        """

        _, i_bat_A = self.read_battery_measurements_from_uut()
        calibration_value = int(round(i_bat_A / actual_current_A * 1000.0)) * 5

        buf = pack("<B", 3) + pack(">H", calibration_value)

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_R_SNS_BAT, buf):
            return calibration_value
        else:
            return -1

    def set_gpio_1(self, on_off: bool) -> str:
        if on_off:
            self.GPIO_pattern |= 0x01
        else:
            self.GPIO_pattern &= 0xFE

        buf = pack("<B", 1) + pack(">B", self.GPIO_pattern)

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_GPIOs, buf):
            return "OK"
        else:
            return "FAIL writing GPIO1"

    def set_gpio_2(self, on_off: bool) -> str:
        if on_off:
            self.GPIO_pattern |= 0x02
        else:
            self.GPIO_pattern &= 0xFD

        buf = pack("<B", 1) + pack(">B", self.GPIO_pattern)

        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_GPIOs, buf):
            if on_off:
                return "ON"
            else:
                return "OFF"
        else:
            return "FAIL writing GPIO2"

    def application_on_off(self, on_off: bool) -> str:
        if on_off:
            value = 1
        else:
            value = 0

        buf = pack("<B", 1) + pack(">B", value)
        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_APP_ON_OFF, buf):
            if on_off:
                return "APP_ON"
            else:
                return "APP_OFF"
        else:
            return "FAIL writing APP_ON_OFF"

    def set_input_current(self, I_limit_A: float) -> str:
        buf = pack("<B", 2) + pack(">H", int(I_limit_A * 1000))
        self.cpu.I2C_Master_set_PEC(1)
        if self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_Input_Current_Limit, buf):
            return "OK"
        else:
            return "FAIL writing input current limit"

    def reset_calibration(self, r_sense_nominal_ohm: float) -> bool:
        """ Resets both R sense values to the given value

        Args:
            r_sense_nominal_ohm (float): The nominal value of the sense resistance in Ohm. (0.5 Ohm on Dione)

        Returns:
            bool: commands were sent sucessfully
        """
        buf = pack("<B", 2) + pack(">H", r_sense_nominal_ohm)
        self.cpu.I2C_Master_set_PEC(1)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_R_SNS_BAT, buf)
        ok &= self.cpu.I2C_Master_WriteBytes(self.i2c_address_7bit, I2C_CMD_Write_R_SNS_DC_IN, buf)
        return ok


#--------------------------------------------------------------------------------------------------

def test_myself():
    from rrc.track.chroma import DC63600
    from rrc.track.tdklambda import DCZPlus
    from rrc.keysight import AGILENT34972A, DAQ970A, daq_class_selector
    load1 = DC63600("172.23.130.32:2101", channel=1)
    print(load1.ident())
    load1.initialize_device()
    load2 = DC63600("172.23.130.32:2101", channel=2)
    print(load2.ident())
    # load2.initialize_device()
    psu1 = DCZPlus("172.23.130.33:8003", channel=1)
    print(psu1.ident())
    psu1.initialize_device()
    psu2 = DCZPlus("172.23.130.33:8003", channel=2)
    print(psu2.ident())
    psu2.initialize_device()
    daq = daq_class_selector("172.23.130.31:5025", 1)
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
    dev = UUT_Dione_Hera(0x09, 0x33, resource_str="COM9,115200,8N1")
    print(dev.cpu.ident())
    dev.initialize_cpu_ports()
    #print("HELP CONTENT:", dev.cpu.help().replace("\r","\n\r"))
    # psu1.set_output(0)
    sleep(1.5)
    #print(dev.set_uut_into_testmode(False))
    psu1.set_voltage(20.0)
    psu1.set_current_limit(5.0)
    psu1.set_output(1)
    sleep(0.5)
    print(dev.set_uut_into_testmode(True))
    sleep(0.5)
    U_CHANNELS = (5, 6, 7, 8)
    print("BAY1")
    dev.set_I2C_mux_TestSystem(1, 0, 0, 0)
    dev.set_bay_fets(1, 1, True)
    dev.set_u_bat_i_bat(12.6, 4.5, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))
    dev.set_bay_fets(1, 1, False)
    dev.set_u_bat_i_bat(0, 0, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))

    print("BAY2")
    dev.set_I2C_mux_TestSystem(0, 1, 0, 0)
    dev.set_bay_fets(1, 2, True)
    dev.set_u_bat_i_bat(12.6, 4.5, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))
    dev.set_bay_fets(1, 2, False)
    dev.set_u_bat_i_bat(0, 0, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))

    print("BAY3")
    dev.set_I2C_mux_TestSystem(0, 0, 1, 0)
    dev.set_bay_fets(1, 3, True)
    dev.set_u_bat_i_bat(12.6, 4.5, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))
    dev.set_bay_fets(1, 3, False)
    dev.set_u_bat_i_bat(0, 0, 1)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))

    print("BAY4")
    dev.set_I2C_mux_TestSystem(0, 0, 0, 1)
    dev.set_bay_fets(2, 4, True)
    dev.set_u_bat_i_bat(12.6, 4.5, 2)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))
    dev.set_bay_fets(2, 4, False)
    dev.set_u_bat_i_bat(0, 0, 2)
    for n in U_CHANNELS:
        print(daq.get_VDC(n))

    sleep(0.5)
    # dev.cpu.I2C_Master_set_PEC(1)
    #dev.set_u_bat_i_bat(12.6, 4.5, 1)
    #sleep(0.5)
    #dev.set_bay_fets(1, 1, True)
    # sleep(0.5)
    # print(dev.read_battery_measurements_from_uut(1, 1))
    # sleep(0.5)
    # print(load1.set_load_output(0))
    # print(load1.set_load_mode("CCH"))
    # print(load1.set_load_current(0.5))
    # print(load1.set_load_output(1))
    # sleep(0.5)
    # print(load1.set_load_current(2))
    # sleep(0.5)
    # print(load1.set_load_current(4))
    print(load1.get_voltage())
    # print(dev.read_battery_measurements_from_uut(1,1))
    # for i in range(100):
    #     print(dev.get_pushbutton_state())
    #     sleep(0.5)
    # dev.cpu.I2C_Master_ReadBytes(0x66, 0x81, 17)
    # print(dev.set_and_verify_udi("AAAABBBBCCCCDDDD"))
    # for port in "AC":
    #     print(f"Port {port} Status: ", dev.cpu.IO_Get_Portstatus(port))
    #     for bit in range(8):
    #         print(f"Read Port {port}, bit {bit}:", dev.cpu.IO_Read_Port_bit(port, bit))
    # print(dev.is_adapter_correctly_connected())
    # print("VCC:", daq.get_VDC_rounded(3,3))
    # print("TP_V_SYSM:", daq.get_VDC_rounded(4,3))
    # print("TP_VIN_M:", daq.get_VDC_rounded(5,3))
    # print("TEMP:",daq.get_temp_rounded(6, "FRTD", 100, 0, "", 2))
    # print(dev.reset_calibration())
    # dev.cpu.reset()
    # sleep(0.5)
    # dev.set_I2C_mux_UUT(1, True)
    # sleep(0.5)
    # print(dev.set_I2C_mux_TestSystem([1,0,0,0]))
    # dev.cpu.I2C_Master_set_PEC(0)
    # print(dev.cpu.con.request(":I2C:MAS:TIM 64,0"))  # speed up I2C com (AVR TWBR,TWPS register)
    # print(dev.cpu.I2C_Master_set_Clockfrequency(50000, fcpu=7372800))
    # z=0
    # while z < 100:
    #     z += 1
    #     for i in range(0, 5):
    #         # tca9548a - set bit for channel
    #         _ch = int(1 << i)
    #         #_ch = 0x1f
    #         #print(i, dev.cpu.I2C_Master_WriteBytes((0x71 << 1), _ch, bytes()))
    #         #print(i, dev.cpu.I2C_Master_WriteBytes((0x71 << 1), _ch, bytes([_ch])))
    #         #print(i, dev.cpu.I2C_Master_ReadBytes((0x71 << 1), _ch, 0))  # writes command (select channel) and reads it back
    #         #print(i, dev.cpu.I2C_Master_ReadBytes((0x71 << 1), _ch, 1))  # writes command (select channel) and reads it back
    #         print(dev.set_I2C_mux_TestSystem([1,0,0,0]))
    #         #print(dev.set_I2C_mux_TestSystem(1))
    #         #dev.cpu.I2C_Master_set_PEC(0)
    #         #print(dev.set_I2C_mux_TestSystem(i))
    #         #print(i, dev.cpu.I2C_Master_WriteBytes((0x70 << 1), _ch, bytes([_ch])))
    #         try:
    #             #dev.set_and_verify_udi("1234567890123456")
    #             #print(i, dev.get_udi())
    #             #dev.cpu.I2C_Master_ReadBytes((0x09 << 1), I2C_CMD_Read_Bat_Detection, 5)
    #             dev.cpu.I2C_Master_ReadBytes((0x09 << 1), 0x81, 17)
    #             #dev.cpu.I2C_Master_ReadBytes((0x33 << 1), 0x81, 17)
    #         except Exception as ex:
    #             print("False", ex)
    #             pass

    # print(dev.get_r_sense_battery_from_uut(1))
    # print(psu1.set_voltage(16.0))
    # print(psu1.set_current_limit(4.0))
    # print(psu1.set_output(1))
    # print(load2.set_load_output(0))
    # print(load2.set_load_mode("CCH"))
    # print(load2.set_measure_sense_to("UUT"))
    # print(load2.activate_device_display())
    # print(load2.measure_voltage())
    # print(load2.measure_current())
    # print(dev.read_battery_measurements_from_uut())
    # print(dev.read_charger_measurements_from_uut())
    # print(dev.switch_application_on_off(0))
    # dev.set_u_bat_i_bat(0, 0)  # dummy action, next one will set correctly
    # print(load2.set_load_mode("CRL"))
    # print(load2.get_load_mode())
    # print(load2.set_load_output(1))
    # load2.set_load_resistance(10.0)
    # load2.set_load_resistance(5.0)
    # load2.set_load_resistance(3.0)
    #dev.set_u_bat_i_bat(12.05, 3.6)
    #print("Startup with 0 load")
    #print(load2.set_load_current(0))
    #print(load2.set_load_output(1))
    # for c in [0,50,10,4,2,1]:
    #     # set next current
    #     cc = 3.6
    #     dev.set_u_bat_i_bat(12.05, cc)
    #     _nc: float = (cc / c) if c > 0 else 0
    #     print(f"Set current {_nc:.3f}A")
    #     load2.set_load_current(_nc)
    #     load2.set_load_output(1)
    #     sleep(0.75)
    #     #print(dev.read_battery_measurements_from_uut())
    #     #print(dev.read_charger_measurements_from_uut())
    #     print(f"{load2.measure_voltage():.3f}")
    #     print(f"{load2.measure_current():.4f}")
    #     #print(load1.measure_voltage())
    #     #print(load1.measure_current())
    #     load2.set_load_output(0)

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