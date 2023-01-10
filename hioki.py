from eth2serial.base import Eth2Serial_SockSingleConnection_Device
from eth2serial.base import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

DEBUG = 0

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
#  BT3561A Device
#--------------------------------------------------------------------------------------------------

class Hioki_BT3561A(Eth2SerialDevice):

    def __init__(self, host: str, port: int, termination: str = "\r\n"):
         super().__init__(host, port, termination)

    def set_function(self, mode: str) -> bool:
        """
        Select the Measurement Mode Setting.

        Args:
            mode (str): 'RV', 'RES', 'VOLT'

        Raises:
            ValueError: _description_

        Returns:
            bool : True - success, False - failed
        """
        assert((mode == 'RV') or (mode == 'RES') or (mode == 'VOLT')), ValueError("Error, Hioki set_function: Only 'RV', 'RES' and 'VOLT' modes are allowed.")
        self.send(f':FUNC {mode}')
        return True if self.request("*ESR?").strip() == "0" else False

    def get_function(self) -> str:
        """
        Query the Measurement Mode Setting.

        Returns:
            str: 'RV', 'RES', 'VOLT'
        """
        return self.request(':FUNC?')

    def set_resistance_range(self, range: float) -> bool:
        """
        Set the Resistance Measurement Range.

        Args:
            range (float): resistance 0...3100 Ohm

        Raises:
            ValueError: invalid parameters
        """
        range = float(range)
        assert((range >= 0) and (range <= 3100)), ValueError('Error, Hioki set_resistance_range: Allowed range is 0 .. 3100')
        self.send(f':RES:RANG {range}')
        return True if self.request("*ESR?").strip() == "0" else False

    def get_resistance_range(self) -> float:
        """
        Query the Resistance Measurement Range.

        Returns:
            float: resistance 3.0000E-3/ 30.000E-3/ 300.00E-3/
                   3.0000E+0/ 30.000E+0/ 300.00E+0/ 3.0000E+3
        """
        return float(self.request(':RES:RANG?'))

        """ Set the Voltage Measurement Range.

            Parameters
            ----------
            range: float,  """

    def set_voltage_range(self, range: float) -> bool:
        """
        Set the Voltage Measurement Range.

        Args:
            range (float): voltage -300...300 V

        Raises:
            ValueError: invalid parameters
        """
        range = float(range)
        assert((range >= -300) and (range <= 300)), ValueError('Error, Hioki set_voltage_range: Allowed range is -300 .. 300')
        self.send(f':VOLT:RANG {range}')
        return True if self.request("*ESR?").strip() == "0" else False

    def get_voltage_range(self) -> float:
        """
        Query the Voltage Measurement Range.

        Returns:
            float: voltage range, 6.00000E+0/
                   60.0000E+0/100.000E+0/300.000E+0
        """
        return float(self.request(':VOLT:RANG?'))

    def set_autorange(self, state: int) -> bool:
        """
        Set the Auto-Ranging Setting.

        Args:
            state (int): autoranfe 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_autorange: Only 0 or 1 are allowed.')
        self.send(f':AUT {state}')
        return True if self.request("*ESR?").strip() == "0" else False

    def get_autorange(self) -> str:
        """
        Query the Auto-Ranging Setting.

        Returns:
            str: autorange 'ON'|'OFF'
        """
        return self.request(':AUT?')

    def set_adjustment_clear(self) -> bool:
        """ Cancel Zero-Adjustment. """
        self.send(':ADJ:CLEA')
        return True if self.request("*ESR?").strip() == "0" else False

    def set_adjustment(self) -> int:
        """
        Execute Zero Adjustment and Query the Result.

        Returns:
            int: 0 - Zero adjustment succeeded
                 1 - Zero adjustment failed
        """
        return self.request(':ADJ?')

    def set_syst_calibration(self) -> bool:
        """ Execute Self-Calibration. """
        self.send(':SYST:CAL')
        return True if self.request("*ESR?").strip() == "0" else False

    def set_syst_calibration_auto(self, state: int) -> bool:
        """_summary_

        Args:
            state (int): 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_autorange: Only 0 or 1 are allowed.')
        self.send(f':SYST:CAL:AUTO {state}')
        return True if self.request("*ESR?").strip() == "0" else False

    def get_syst_calibration_auto(self) -> str:
        """
        Query the Self-Calibration State.

        Returns:
            str: auto-calibration 'ON'|'OFF'
        """

        return self.request(':SYST:CAL:AUTO?')

    def set_syst_klock(self, state: int) -> None:
        """
        Set the Key-Lock State.

        Args:
            state (int): klock 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_syst_klock: Only 0 or 1 are allowed.')
        self.send(f':SYST:KLOC {state}')

    def get_syst_klock(self) -> str:
        """
        Query the Key-Lock State.

        Returns:
            str: klock 'ON'|'OFF'
        """
        return self.request(':SYST:KLOC?')

    def set_local_control(self) -> None:
        """ Set Local Control. """
        self.send(f':SYST:LOC')

    def set_trigger_source(self, state: str) -> None:
        """
        Set the Trigger Source.

        Args:
            state (str): state 'IMM'|'EXT'

        Raises:
            ValueError: invalid parameters
        """

        assert((state == 'IMM') or (state == 'EXT')), ValueError("Error, Hioki set_trigger_source: Only 'IMM' and 'EXT' are allowed.")
        self.send(f':TRIG:SOUR {state}')

    def get_trigger_source(self) -> str:
        """
        Query the Trigger Source.

        Returns:
            str: trigger source 'IMMEDIATE'|'EXTERNAL'
        """

        return self.request(':TRIG:SOUR?')

    def set_continous_measurement(self, state: int) -> None:
        """
        Sets continuous measurement ON|OFF.

        Args:
            state (int): state 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters
        """
        state = int(state)
        assert((state == 0) or (state == 1)),  ValueError('Error, Hioki set_continous_measurement: Only 0 or 1 are allowed.')
        self.send(f':INIT:CONT {state}')

    def read(self) -> float:
        """
        Execute a Measurement and Read the Measured Values.

        Returns:
            float: Measured Values
        """
        try:
            resp = self.request(':READ?').strip()
            func = self.get_function().strip()
            if (func == 'RV'):
                lst = resp.split(',')
                result = []
                result.append(float(lst[0]))
                result.append(float(lst[1]))
            else:
                result = float(resp)
            return result
        except Exception:
            raise

    def set_raw_command(self, msg: str) -> None:
        """
        Sets raw command and returns error.

        Args:
            msg (str): command
        """
        return self.send(msg)

    def set_raw_query(self, msg: str) -> str:
        """
        Query raw command and returns response.

        Args:
            msg (str): command

        Returns:
            str: response
        """
        return self.request(msg)

    def clear_status(self) -> None:
        """ Resets the Status byte and Event status registers. """
        return self.send('*CLS')

#--------------------------------------------------------------------------------------------------
# SW1001
#--------------------------------------------------------------------------------------------------

class Hioki_SW1001(Eth2Serial_SockSingleConnection_Device):

    def __init__(self, host: str, port: int, termination: str = "\r\n"):
        super().__init__(host, port, termination)

    #---STANDARD FUNCTIONS---

    def get_idn(self) -> str:
        """
        Queries the device ID

        Returns:
            str:    <Manufacturer's name>,
                    <Model name>,0,
                    <Software version>
        """
        return self.request('*IDN?')

    def get_opc(self) -> bool:
        """
        Queries the device OPC

        Returns:
            str:    <Manufacturer's name>,
                    <Model name>,0,
                    <Software version>
        """
        return True if (self.request('*OPC?').strip() == "1") else False

    def set_reset(self) -> None:
        """ Initializes the device. """
        return self.send('*RST')

    def clear_status(self) -> None:
        """ Resets the Status byte and Event status registers. """
        return self.send('*CLS')

    def self_test(self) -> bool:
        """
        Initiates a self-test and queries the result.

        Returns:
            int:    0 - No Errors
                    1 - RAM Error
                    2 - EEPROM Error
                    3 - RAM and EEPROM Errors
        """
        return True if (self.request('*TST?').strip() == "0") else False

    #---DEVICE FUNCTIONS---

    def read_error_info(self) -> str:
        return self.request(":SYST:ERR?")

    def set_wire_mode(self, slot: int, mode: int) -> bool:
        """
        Sets the connection method for a given slot.

        Args:
            slot (int): slot number
            mode (int): wire mode (2 or 4)

        Raises:
            ValueError: invalid parameters
        """

        slot = int(slot)
        mode = int(mode)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki set_wire_mode: Allowed slot range is 1 .. 3')
        assert((mode == 2) or (mode == 4)), ValueError('Error, Hioki set_wire_mode: Only 2 or 4 modes are allowed')
        self.send(f":SYST:MOD:WIRE:MODE {slot},WIRE{mode}")
        #return hioki.sw.set_raw_query("*ESR?")
        return self.get_opc()


    def get_wire_mode(self, slot: int) -> str:
        """
        Queries the connection method for a given slot.

        Args:
            slot (int): slot number

        Raises:
            ValueError: invalid parameters

        Returns:
            str: mode 'WIRE2' or 'WIRE4'
        """

        slot = int(slot)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki get_wire_mode: Allowed slot range is 1 .. 3')
        return self.request(f':SYST:MOD:WIRE:MODE? {slot}')

    def set_shield_mode(self, slot: int, mode: str) -> bool:
        """
        Sets the shield wire connection destination for a given slot.

        Args:
            slot (int): slot number
            mode (str): _description_

        Raises:
            ValueError: mode OFF/GND/TERM1/TERM2/TERM3/T1T3/SNS2L
        """
        slot = int(slot)
        arr_mode = ['OFF','GND','TERM1','TERM2','TERM3','T1T3','SNS2L']
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki set_shield_mode: Allowed slot range is 1 .. 3')
        assert(mode in arr_mode), ValueError('Error, Hioki set_shield_mode: incorrect mode')
        self.send(f':SYST:MOD:SHI {slot},{mode}')
        return self.get_opc()

    def get_shield_mode(self, slot: int) -> str:
        """
        Queries the shield wire connection destination for a given slot.

        Args:
            slot (int): slot number

        Raises:
            ValueError: invalid parameters

        Returns:
            str: mode OFF/GND/TERM1/TERM2/TERM3/T1T3/SNS2L
        """

        slot = int(slot)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki get_shield_mode: Allowed slot range is 1 .. 3')
        return self.request(f':SYST:MOD:SHI? {slot}')

    def get_module_count(self, slot: int) -> int:
        """
        Returns to the specified relay opening/closing frequency.

        Args:
            slot (int): slot number

        Raises:
            ValueError: invalid parameters

        Returns:
            int: <Opening/closing frequency> = 0 to 1000000000
        """
        slot = int(slot)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki get_module_count: Allowed slot range is 1 .. 3')
        return self.request(f':SYST:MOD:COUN? {slot}')

    def close(self, slot: int, channel: int) -> bool:
        """
        Closes the specified slot and channel.
        The channel that was closed previously is automatically opened.

        Args:
            slot (int): slot number
            channel (int): channel number

        Raises:
            ValueError: invalid parameters
        """

        slot = int(slot)
        channel = int(channel)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki close: Allowed slot range is 1 .. 3')
        assert((channel >= 1) and (channel <= 22)), ValueError('Error, Hioki close: Allowed channel range is 1 .. 22')
        self.send(f':ROUT:CLOS {slot}{channel:02d}')
        return self.get_opc()
        #return hioki.sw.set_raw_query("*ESR?")

    def open(self) -> bool:
        """ Opens all channels. """
        self.send(f':OPEN')
        return self.get_opc()

    def set_raw_command(self, msg: str) -> None:
        """
        Sets raw command and returns error.

        Args:
            msg (str): command
        """
        return self.send(msg)

    def set_raw_query(self, msg: str) -> str:
        """
        Query raw command and returns response.

        Args:
            msg (str): command

        Returns:
            str: response
        """
        return self.request(msg)

    def set_new_ip_address(self, new_ip: str, new_port: int = 23,
                           new_subnet_mask: str = "255.255.255.0", new_default_gateway: str = "0.0.0.0",
                           pause_reboot: float = 5.0):
        """_summary_

        Args:
            new_ip (str): _description_
            new_port (int, optional): _description_. Defaults to 23.
            new_subnet_mask (str, optional): _description_. Defaults to "255.255.255.0".
            new_default_gateway (str, optional): _description_. Defaults to "0.0.0.0".
            pause_reboot (float, optional): _description_. Defaults to 5.0.
        """
        # remove the dots from the strings
        _ip_str = new_ip.replace('.' , ',')
        _subnet_mask = new_subnet_mask.replace('.' , ',')
        _default_gateway = new_default_gateway.replace('.' , ',')
        _port = int(new_port)
        # Set the IP address for the device.
        # :SYSTem:COMMunicate:LAN:IPADdress <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:IPAD {_ip_str}')
        # Set the LAN subnet mask.
        # :SYSTem:COMMunicate:LAN:SMASK <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:SMASK {_subnet_mask}')
        # Set the address for the default gateway.
        # :SYSTem:COMMunicate:LAN:GATeway <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:GAT {_default_gateway}')
        # Specify the communication command port No.
        # :SYSTem:COMMunicate:LAN:CONTrol <1 - 9999>
        self.send(f':SYST:COMM:LAN:CONT {_port}')
        #:SYSTem:COMMunicate:LAN:UPDate
        self.send(f':SYST:COMM:LAN:UPD')
        # now we need to update our communication host and port internally...
        #self.host = new_ip
        #self.port = new_port
        sleep(pause_reboot)
        try:
            # check if the new address is available
            result = self.request(f"SYST:COMM:LAN:IPAD?").replace(',','.')
            _log.info('IP address has been set: %s' , result)
        except NameError as ex:
            _log.error(ex)
        except ConnectionRefusedError as ex:
            _log.error(ex)

# add more ...


#--------------------------------------------------------------------------------------------------
#  Combined Device
#--------------------------------------------------------------------------------------------------

class Hioki_Cell_Tester(object):
    """This is a class that holds a BT3561A and a SW1001 device providing convenience functions."""

    def __init__(self, BT_HOST, BT_PORT, SW_HOST, SW_PORT):
        self.bt = Hioki_BT3561A(BT_HOST, BT_PORT)
        self.sw = Hioki_SW1001(SW_HOST, SW_PORT, termination="\r\n")

    def measure_channnel(self, channel: int) -> list:
        """
        Measures the voltage and impedance of the a given channel.

        Args:
            channel (int): channel number 1 ... 22

        Raises:
            ValueError: invalid channel number

        Returns:
            list: array[0]: float, resistance, Ω mode
                  array[1]: float, voltage, V mode
        """
        channel = int(channel)
        assert((channel >= 1) and (channel <= 22)), ValueError('Error, measure_channnel: Only channels 1 .. 22 are allowed')
        # IMPORTANT! Set continuous measurement OFF.
        self.bt.set_continous_measurement(0)
        with self.sw as sw_dev:
            # SW1001 operations ==================
            if (channel <= 11):
                #SLOT 1
                #self.sw.set_shield_mode(1, 'GND')
                sw_dev.set_wire_mode(1, 4)
                sw_dev.close(1, channel)
            else:
                #SLOT 2
                channel = channel - 11
                #self.sw.set_shield_mode(2, 'GND')
                sw_dev.set_wire_mode(2, 4)
                sw_dev.close(2, channel)
        # BT3561A operations =================
        #[BT3561A] :READ? Execute single measurement using BT3561A.
        result = self.bt.read()
        self.bt.set_continous_measurement(1)
        return result

    def measure_all_channels(self) -> list:
        """
        Measures voltage and impedance of all 22 channels.

        Returns:
            list: array[0..43]: float, Ch1.Impedance, Ch1.Voltage, Ch2.Impedance, Ch2.Voltage, ...
        """
        # IMPORTANT! Set continuous measurement OFF.
        self.bt.set_continous_measurement(0)
        result = []
        # bt_sock should be closed before invoking BT_get_function!
        bt_function_type = self.bt.get_function().strip()
        for i in range(22):
            # Channel 1/Slot1 or Channel 1/Slot 2. Needs to switch shield mode and wire mode
            if (i == 0):
                self.sw.set_wire_mode(1, 4)
            if (i == 11):
                self.sw.set_wire_mode(2, 4)
            if (i < 11):
                #SLOT 1
                self.sw.close(1, i+1)
            else:
                #SLOT 2
                self.sw.close(2, (i-11)+1)
            #[BT3561A] :READ? Execute single measurement using BT3561A.
            sleep(0.1)
            resp = self.bt.request(':READ?').strip()
            if (bt_function_type == 'RV'):
                lst = resp.split(',')
                result.append(float(lst[0]))
                result.append(float(lst[1]))
            else:
                result.append(float(resp))
                result.append(float(0))
        self.bt.set_continous_measurement(1)
        return result
#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    #======================================================================================================
    # Set SW 1001 IP address
    #SW_DEFAULT_IP_STR = "192.168.0.254"     # SW1001 IP addr
    #SW_DEFAULT_PORT = 23                    # SW1001 port
    #sw = Hioki_SW1001(SW_DEFAULT_IP_STR, SW_DEFAULT_PORT)
    #print(sw.set_new_ip_address("192.168.1.203"))

    # Switch off the SW1001. 
    # Set communication setting mode switch (DFLT/USER) to USER. 
    # Switch on the device.

    #======================================================================================================

    # predefined resource ID
    BT_IP_STR = "192.168.1.202"     # BT3561A IP addr
    BT_PORT = 23                    # BT3561A port
    SW_IP_STR = "192.168.1.201"     # SW1001 IP addr
    SW_PORT = 23                    # SW1001 port

    # 1. Create an instance of 20 channel MUXER with HIOKI ACIR measurement device class
    hioki = Hioki_Cell_Tester(BT_IP_STR, BT_PORT, SW_IP_STR, SW_PORT)

    # # 2. ==== BT3561A functions ==========================================================================

    # Device initialization
    # *IDN?
    #print('BT3561A ID: ', hioki.bt.get_idn())
    # *CLR 
    #hioki.clear_status()

    # Set trigger source - IMM
    #hioki.bt.set_trigger_source('IMM')

    # Set function 'RV'
    #hioki.bt.set_function('RV')

    # # *TST?
    # print('BT3561A TEST: ', hioki.bt.self_test())

    # # Get function
    # print('BT3561A Func: ', hioki.bt.get_function())

    # # Set resistance range 0.1 Ohm
    # hioki.bt.set_resistance_range(0.1)

    # # Get resistance range
    # print('BT3561A Resistance Range: ', hioki.bt.get_resistance_range())

    # # Set voltage range 6 V
    # hioki.bt.set_voltage_range(6)

    # # Get voltage range
    # print('BT3561A Voltage Range: ', hioki.bt.get_voltage_range())

    # # Set auto range ON
    # hioki.bt.set_autorange(0)

    # # Get auto range
    # print('BT3561A Auto Range : ', hioki.bt.get_autorange())

    # # Adjust zero, 0 - success
    # #print('BT3561A Zero Adjustment: ', hioki.bt.set_adjustment())

    # # Adjust clear
    # hioki.bt.set_adjustment_clear()

    # # System calibration
    # hioki.bt.set_syst_calibration()

    # # System calibration auto 1 - ON, 0 - OFF
    # hioki.bt.set_syst_calibration_auto(0)

    # # Get system key lock
    # print('BT3561A Key Lock: ', hioki.bt.get_syst_klock())

    # # Set system key lock OFF
    # #hioki.bt.set_syst_klock(0)

    # # System Local
    # hioki.bt.set_local_control()

    # # Set trigger source
    # hioki.bt.set_trigger_source('IMM')

    # # Get trigger source
    # print('BT3561A trig source: ', hioki.bt.get_trigger_source())

    # =============== READ? ============================

    # IMPORTANT! Set continuous measurement OFF.
    #hioki.bt.set_continous_measurement(0)

    #sleep(0.1)

    #print('BT3561A measurement ', hioki.bt.read())

    #hioki.bt.set_continous_measurement(1)

    # 3. ==== SW1001 functions ===========================================================================


    #======== TEST =======================================================================================
    #hioki.sw.clear_status()
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print(hioki.sw.get_idn())
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("TYPE ", hioki.sw.set_raw_query(":SYST:CTYP? 1"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("TYPE ", hioki.sw.set_raw_query(":SYST:CTYP? 2"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #hioki.sw.set_raw_command(":ROUT:OPEN")
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))

    #===== BT ===================================================

    #hioki.bt.set_raw_command("*CLS")
    #print("BT ESR ", hioki.bt.set_raw_query("*ESR?"))
    #hioki.bt.set_raw_command(":SYST:HEAD OFF")
    #print("BT ESR ", hioki.bt.set_raw_query("*ESR?"))
    #hioki.bt.set_continous_measurement(0)
    #print("BT ESR ", hioki.bt.set_raw_query("*ESR?"))
    #hioki.bt.set_trigger_source("IMM")
    #print("BT ESR ", hioki.bt.set_raw_query("*ESR?"))
    #hioki.bt.set_raw_command(":CALC:LIM:STAT OFF")
    #print("BT ESR ", hioki.bt.set_raw_query("*ESR?"))

    #============================================================

    #hioki.sw.set_wire_mode(1, 4)
    #hioki.sw.set_raw_command(":SYST:MOD:WIRE:MODE 1,WIRE4")
    #sleep(0.1)
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("OPC ", hioki.sw.set_raw_query("*OPC?"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #hioki.sw.set_wire_mode(2, 4)
    #hioki.sw.set_raw_command(":SYST:MOD:WIRE:MODE 2,WIRE4")
    #sleep(0.1)
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("OPC ", hioki.sw.set_raw_query("*OPC?"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #hioki.sw.set_raw_command(":SYST:MOD:DEL 1,0")
    #sleep(0.1)
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("OPC ", hioki.sw.set_raw_query("*OPC?"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #hioki.sw.set_raw_command(":SYST:MOD:DEL 2,0")
    #sleep(0.1)
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("OPC ", hioki.sw.set_raw_query("*OPC?"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #hioki.sw.close(1, 1)
    #hioki.sw.set_raw_command(":ROUT:CLOS 0101")
    #sleep(0.1)
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))
    #print("OPC ", hioki.sw.set_raw_query("*OPC?"))
    #print("ESR ", hioki.sw.set_raw_query("*ESR?"))

    #print(hioki.bt.read())

    #hioki.bt.set_continous_measurement(1)

    #print('SW1001 Slot1 Wire Mode: ', hioki.sw.get_wire_mode(1))
    #print('SW1001 Slot2 Wire Mode: ', hioki.sw.get_wire_mode(2))
    #======================================================================================================

    # *IDN?
    #print('SW1001 ID: ', hioki.sw.get_idn())

    # *RST
    #hioki.sw.set_reset()
    #print(hioki.sw.get_idn())
    #print(hioki.sw.read_error_info())
    #hioki.sw.clear_status()

    # *TST?
    #print('SW1001 Self Test: ', hioki.sw.self_test())

    # Raw query command
    #print('SW1001 Get Scan List: ', hioki.sw.set_raw_query(':SCAN?'))

    # Raw command
    #hioki.sw.set_raw_command(':SYST:MOD:SHI 1,GND')
    #hioki.sw.open()

    # IMPORTANAT! Switching the channel:
    # 1. Set wire mode
    #hioki.sw.set_wire_mode(1, 4)
    #sleep(5)
    # 2. Set shield mode (if needed)
    #hioki.sw.set_shield_mode(1, 'GND')
    #hioki.sw.set_shield_mode(2, 'GND')
    #sleep(5)
    # 3. CLOSE channel
    #hioki.sw.close(1, 1)

    #print(hioki.sw.set_raw_query("SCAN?"))

    #print('SW1001 Slot1 Wire Mode: ', hioki.sw.get_wire_mode(1))
    #print('SW1001 Slot1 Shield Mode: ', hioki.sw.get_shield_mode(1))
    #print('SW1001 Slot2 Wire Mode: ', hioki.sw.get_wire_mode(2))
    #print('SW1001 Slot2 Shield Mode: ', hioki.sw.get_shield_mode(2))

    #hioki.bt.set_continous_measurement(0)

    #print(hioki.bt.read())

    #hioki.bt.set_continous_measurement(1)

    #hioki.sw.open()

    # Get module count
    #print('SW1001 Slot1 Count: ', hioki.sw.get_module_count(1))
    #print('SW1001 Slot2 Count: ', hioki.sw.get_module_count(2))

    # CLOSE channel
    #hioki.sw.close(1, 1)

    # OPEN
    #hioki.sw.open()

    # 4. ==== Cells tester (BT3561A + SW1001) functions ================================================

    #sleep(0.1)

    # measure single channel (1 ... 22)
    print(hioki.measure_channnel(1))

    # measure all 22 4-wire channels (Could be useful for Zero-adjustment procedure)
    #print(hioki.measure_all_channels())

    #hioki.sw.open()

    # Sockets need to be closed
    #hioki.bt.close_socket()
    #hioki.sw.close_socket()

    print("DONE.")


# END OF FILE
