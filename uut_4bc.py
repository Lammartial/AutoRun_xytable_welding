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
CHARGERS = [CHARGER_1, CHARGER_2]

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

#class UUT_4bayCharger(UUT_Dione_Hera):
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
        self.i2c_address_mux_testsystem = (0x71 << 1)


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
        sleep(0.25)
        #self.cpu.I2C_Master_set_PEC(1)
        rbbuf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, 0x81, 17)
        if rbbuf[0] != 16:
            raise ValueError(f"Length of readback UDI string is '{rbbuf[0]}' which is not 16.")
        rbstr = bytes(rbbuf[1:]).decode("utf-8")
        if rbstr != udi:
            raise ValueError(f"Readback UDI string is different from exprected one.")
        return True



    def get_udi(self) -> str:
        #self.cpu.I2C_Master_set_PEC(1)
        buf = self.cpu.I2C_Master_ReadBytes(self.i2c_address, 0x81, 17)
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

        buf = pack("<B", 2) + pack("<B", bay_ID) + pack("<b", int(state))  # need big endian
        return self.cpu.I2C_Master_WriteBytes(self.i2c_address, I2C_CMD_Write_I2CMUX, buf)


    def set_I2C_mux_TestSystem(self, state_bays: tuple | list | int) -> bool:
        """Enables or disables the channel of test system's I2C mux.

        Args:
            state_bays (tuple or list or int): new state of the channel 1,2,3 and 4 depending on positon, 
                e.g. (1,0,1,0) selects bay 1 and 3. Can by any combination or select one by an integer in the range 1 to 4.

        Returns:
            bool: Result of I2C transfer
        """

        new_control_reg = 0
        if isinstance(state_bays, int):
            new_control_reg = (1 << ((state_bays-1) & 0x3))
        else:
            for i,b in enumerate(state_bays):
                # combine the bits according to the given list
                new_control_reg |= (1 << i) if int(b) else 0
        self.cpu.I2C_Master_set_PEC(0)
        ok = self.cpu.I2C_Master_WriteBytes(self.i2c_address_mux_testsystem, new_control_reg, bytes())
        self.cpu.I2C_Master_set_PEC(1)
        return ok
        # Writes command byte only (select channel) and reads it back.
        # With this trick there is only one byte written and we get the verififaction in one turn
        buf = pack("<B", new_control_reg)
        rbuf = self.cpu.I2C_Master_ReadBytes(self.i2c_address_mux_testsystem, new_control_reg, 1)
        return (buf == rbuf)
        #return new_control_reg == int(unpack("<B", rbuf)[0])
        #return self.cpu.I2C_Master_WriteBytes(self.i2c_address_mux_testsystem, 0x00, buf)

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
    dev = UUT_Dione_Hera(0x09, 0x33, resource_str="COM3,115200,8N1")
    print(dev.cpu.ident())
    dev.initialize_cpu_ports()    
    #print("HELP CONTENT:", dev.cpu.help().replace("\r","\n\r"))
    psu1.set_output(0)
    sleep(1.5)
    #print(dev.set_uut_into_testmode(False))
    psu1.set_voltage(20.0)
    psu1.set_current_limit(1.0)
    psu1.set_output(1)
    sleep(0.5)
    #print(dev.set_uut_into_testmode(True))
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
    #dev.set_I2C_mux_UUT(1, True)
    # sleep(0.5)
    dev.cpu.I2C_Master_set_PEC(0)
    while True:
        for i in range(0, 5):
            # tca9548a - set bit for channel
            _ch = int(1 << i)   
            #_ch = 0x1f
            #print(i, dev.cpu.I2C_Master_WriteBytes((0x71 << 1), _ch, bytes()))
            #print(i, dev.cpu.I2C_Master_WriteBytes((0x71 << 1), _ch, bytes([_ch])))
            #print(i, dev.cpu.I2C_Master_ReadBytes((0x71 << 1), _ch, 0))  # writes command (select channel) and reads it back
            #print(i, dev.cpu.I2C_Master_ReadBytes((0x71 << 1), _ch, 1))  # writes command (select channel) and reads it back
            print(dev.set_I2C_mux_TestSystem([1,0,0,0]))
            #print(dev.set_I2C_mux_TestSystem(i))
            #print(i, dev.cpu.I2C_Master_WriteBytes((0x70 << 1), _ch, bytes([_ch])))
            try:
                #dev.set_and_verify_udi("1234567890123456")
                #print(i, dev.get_udi())
                #dev.cpu.I2C_Master_ReadBytes((0x09 << 1), I2C_CMD_Read_Bat_Detection, 5)
                dev.cpu.I2C_Master_ReadBytes((0x09 << 1), 0x81, 17)
                #dev.cpu.I2C_Master_ReadBytes((0x33 << 1), 0x81, 17)
            except Exception as ex:
                print("False", ex)
                pass

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