from rrc.eth2serial.base import Eth2Serial_SockSingleConnection_Device
from rrc.eth2serial.base import Eth2SerialDevice
from time import sleep

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


#--------------------------------------------------------------------------------------------------
#  BT3561A Device
#--------------------------------------------------------------------------------------------------

class Hioki_BT3561A(Eth2SerialDevice):

    #def __init__(self, host: str, port: int, termination: str = "\r\n"):
    #     super().__init__(host, port, termination)
    def __init__(self, resource_str: str, termination: str = "\r\n"):
        super().__init__(resource_str, termination)

    def __str__(self) -> str:
        return f"Hioki BT3561A device on {self.super().__str__()}"

    def __repr__(self) -> str:
        return f"Hioki_BT3561A({self.host}, {self.port}, termination={self.termination})"

    #----------------------------------------------------------------------------------------------
    def init(self):
        """
        Some presets for the correct operation of the BT3561A 

        Returns:
            bool: True - no errors, otherwise False
        """
        result = True
        # CLS (BT3561A)
        result &= self.clear_status()
        # HEADER OFF (BT3561A)
        result &= self.set_raw_command(":SYST:HEAD OFF")
        # continuous measurement off (BT3561A)
        result &= self.set_continous_measurement(0)
        # Trigger source: IMMEDIATE (BT3561A)
        result &= self.set_trigger_source('IMM')
        # Comparator: OFF (BT3561A) (':CALC:LIM:STAT OFF')
        result &= self.set_raw_command(":CALC:LIM:STAT OFF")
        # Set resistance range 0.1 Ohm
        #result &= self.set_resistance_range(0.1)
        # Set voltage range 6 V
        #result &= self.set_voltage_range(6)
        # Autorange = ON
        result &= self.set_autorange(1)
        # Set measurement = RV (BT3561A)
        result &= self.set_function("RV")
        return result

    def get_esr(self) -> bool:
        """
        Queries the Standard Event Status Register (SESR).

        Returns:
            bool: True when SESR = 0, otherwise False
        """
        return True if (self.request('*ESR?').strip() == "0") else False

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
        return self.get_esr()

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

        Returns:
            bool : True - success, False - failed
        """
        range = float(range)
        assert((range >= 0) and (range <= 3100)), ValueError('Error, Hioki set_resistance_range: Allowed range is 0 .. 3100')
        self.send(f':RES:RANG {range}')
        return self.get_esr()

    def get_resistance_range(self) -> float:
        """
        Query the Resistance Measurement Range.

        Returns:
            float: resistance 3.0000E-3/ 30.000E-3/ 300.00E-3/
                   3.0000E+0/ 30.000E+0/ 300.00E+0/ 3.0000E+3
        """
        return float(self.request(':RES:RANG?'))

    def set_voltage_range(self, range: float) -> bool:
        """
        Set the Voltage Measurement Range.

        Args:
            range (float): voltage -300...300 V

        Raises:
            ValueError: invalid parameters

        Returns:
            bool : True - success, False - failed
        """
        range = float(range)
        assert((range >= -300) and (range <= 300)), ValueError('Error, Hioki set_voltage_range: Allowed range is -300 .. 300')
        self.send(f':VOLT:RANG {range}')
        return self.get_esr()

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

        Returns:
            bool : True - success, False - failed
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_autorange: Only 0 or 1 are allowed.')
        self.send(f':AUT {state}')
        return self.get_esr()

    def get_autorange(self) -> str:
        """
        Query the Auto-Ranging Setting.

        Returns:
            str: autorange 'ON'|'OFF'
        """
        return self.request(':AUT?')

    def set_adjustment_clear(self) -> bool:
        """
        Cancel Zero-Adjustment.

        Returns:
            bool : True - success, False - failed
        """
        self.send(':ADJ:CLEA')
        return self.get_esr()

    def set_adjustment(self) -> int:
        """
        Execute Zero Adjustment and Query the Result.

        Returns:
            int: 0 - Zero adjustment succeeded
                 1 - Zero adjustment failed
        """
        return self.request(':ADJ?')

    def set_syst_calibration(self) -> bool:
        """
        Execute Self-Calibration.

        Returns:
            bool : True - success, False - failed
        """
        self.send(':SYST:CAL')
        return self.get_esr()

    def set_syst_calibration_auto(self, state: int) -> bool:
        """_summary_

        Args:
            state (int): 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters

        Returns:
            bool : True - success, False - failed
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_autorange: Only 0 or 1 are allowed.')
        self.send(f':SYST:CAL:AUTO {state}')
        return self.get_esr()

    def get_syst_calibration_auto(self) -> str:
        """
        Query the Self-Calibration State.

        Returns:
            str: auto-calibration 'ON'|'OFF'
        """

        return self.request(':SYST:CAL:AUTO?')

    def set_syst_klock(self, state: int) -> bool:
        """
        Set the Key-Lock State.

        Args:
            state (int): klock 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters

        Returns:
            bool : True - success, False - failed
        """
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, Hioki set_syst_klock: Only 0 or 1 are allowed.')
        self.send(f':SYST:KLOC {state}')
        return self.get_esr()

    def get_syst_klock(self) -> str:
        """
        Query the Key-Lock State.

        Returns:
            str: klock 'ON'|'OFF'
        """
        return self.request(':SYST:KLOC?')

    def set_local_control(self) -> bool:
        """
        Set Local Control.

        Returns:
            bool : True - success, False - failed
        """
        self.send(f':SYST:LOC')
        return self.get_esr()

    def set_trigger_source(self, state: str) -> bool:
        """
        Set the Trigger Source.

        Args:
            state (str): state 'IMM'|'EXT'

        Raises:
            ValueError: invalid parameters

        Returns:
            bool : True - success, False - failed
        """

        assert((state == 'IMM') or (state == 'EXT')), ValueError("Error, Hioki set_trigger_source: Only 'IMM' and 'EXT' are allowed.")
        self.send(f':TRIG:SOUR {state}')
        return self.get_esr()

    def get_trigger_source(self) -> str:
        """
        Query the Trigger Source.

        Returns:
            str: trigger source 'IMMEDIATE'|'EXTERNAL'
        """

        return self.request(':TRIG:SOUR?')

    def set_continous_measurement(self, state: int) -> bool:
        """
        Sets continuous measurement ON|OFF.

        Args:
            state (int): state 1 - On, 0 - Off

        Raises:
            ValueError: invalid parameters

        Returns:
            bool : True - success, False - failed
        """
        state = int(state)
        assert((state == 0) or (state == 1)),  ValueError('Error, Hioki set_continous_measurement: Only 0 or 1 are allowed.')
        self.send(f':INIT:CONT {state}')
        return self.get_esr()

    def read(self) -> str:
        """
        Execute a Measurement and Read the Measured Values.

        Returns:
            str: Measured Values
        """
        try:
            resp = self.request(':READ?').strip()
            return resp
        except Exception:
            raise

    def measure(self) -> list:
        """
        Measures the voltage or/and impedance.

        Returns:
            list: array[0]: float, resistance, Ω mode
                  array[1]: float, voltage, V mode
        """
        resp = True
        result = []
        function_type = self.get_function()
        #[BT3561A] :READ? Execute single measurement using BT3561A.
        val = self.read()
        try:
            if (function_type == "RV"):
                lst = val.split(',')
                result.append(float(lst[0]))
                result.append(float(lst[1]))
            else:
                result.append(float(resp))
                result.append(float(0))
        except Exception:
            raise
        return result

    def set_raw_command(self, msg: str) -> bool:
        """
        Sets raw command and returns error.

        Args:
            msg (str): command

        Returns:
            bool : True - success, False - failed
        """
        self.send(msg)
        return self.get_esr()

    def set_raw_query(self, msg: str) -> str:
        """
        Query raw command and returns response.

        Args:
            msg (str): command

        Returns:
            str: response
        """
        return self.request(msg)

    def clear_status(self) -> bool:
        """
        Resets the Status byte and Event status registers.

        Returns:
            bool : True - success, False - failed
        """
        self.send('*CLS')
        return self.get_esr()

#--------------------------------------------------------------------------------------------------
# SW1001
#--------------------------------------------------------------------------------------------------

class Hioki_SW1001(Eth2Serial_SockSingleConnection_Device):

    #def __init__(self, host: str, port: int, termination: str = "\r\n"):
    #    super().__init__(host, port, termination)
    def __init__(self, resource_str: str, termination: str = "\r\n"):
        super().__init__(resource_str, termination)

    def __repr__(self) -> str:
        return super().__repr__()

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
            bool: True - present operation is complete.
        """
        return True if (self.request('*OPC?').strip() == "1") else False

    def get_esr(self) -> bool:
        """
        Queries the Standard Event Status Register (SESR).

        Returns:
            bool: True when SESR = 0, otherwise False
        """
        return True if (self.request('*ESR?').strip() == "0") else False

    def set_reset(self) -> bool:
        """
        Initializes the device.

        Returns:
            bool : True - success, False - failed
        """
        self.send('*RST')
        return self.get_esr()

    def clear_status(self) -> bool:
        """
        Resets the Status byte and Event status registers.

        Returns:
            bool : True - success, False - failed
        """
        self.send('*CLS')
        return self.get_esr()

    def self_test(self) -> bool:
        """
        Initiates a self-test and queries the result.

        Returns:
            bool:   True - Pass, False - Fail
        """
        return True if (self.request('*TST?').strip() == "PASS") else False

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

        Returns:
            bool : True - success, False - failed
        """
        result = True
        slot = int(slot)
        mode = int(mode)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki set_wire_mode: Allowed slot range is 1 .. 3')
        assert((mode == 2) or (mode == 4)), ValueError('Error, Hioki set_wire_mode: Only 2 or 4 modes are allowed')
        self.send(f":SYST:MOD:WIRE:MODE {slot},WIRE{mode}")
        result = self.get_esr()
        result &= self.get_opc()
        return result


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

        Returns:
            bool : True - success, False - failed
        """
        result = True
        slot = int(slot)
        arr_mode = ['OFF','GND','TERM1','TERM2','TERM3','T1T3','SNS2L']
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki set_shield_mode: Allowed slot range is 1 .. 3')
        assert(mode in arr_mode), ValueError('Error, Hioki set_shield_mode: incorrect mode')
        self.send(f':SYST:MOD:SHI {slot},{mode}')
        result = self.get_esr()
        result &= self.get_opc()
        return result

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

        Returns:
            bool : True - success, False - failed
        """
        slot = int(slot)
        channel = int(channel)
        assert((slot >= 1) and (slot <= 3)), ValueError('Error, Hioki close: Allowed slot range is 1 .. 3')
        assert((channel >= 1) and (channel <= 22)), ValueError('Error, Hioki close: Allowed channel range is 1 .. 22')
        self.send(f':ROUT:CLOS {slot}{channel:02d}')
        result = self.get_esr()
        result &= self.get_opc()
        return result

    def open(self) -> bool:
        """
        Opens all channels.

        Returns:
            bool : True - success, False - failed
        """
        self.send(f':OPEN')
        return self.get_esr()

    def set_raw_command(self, msg: str) -> bool:
        """
        Sets raw command and returns error.

        Args:
            msg (str): command

        Returns:
            bool : True - success, False - failed
        """
        self.send(msg)
        return self.get_esr()

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
                           pause_reboot: float = 10.0):
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

#--------------------------------------------------------------------------------------------------
#  Combined Device
#--------------------------------------------------------------------------------------------------

class Hioki_Cell_Tester(object):
    """This is a class that holds a BT3561A and a SW1001 device providing convenience functions."""

    #def __init__(self, BT_HOST, BT_PORT, SW_HOST, SW_PORT):
    #    self.bt = Hioki_BT3561A(BT_HOST, BT_PORT)
    #    self.sw = Hioki_SW1001(SW_HOST, SW_PORT, termination="\r\n")
    #    self.bt_function_type = "RV"
    def __init__(self, BT_resource_str, SW_resource_str):
        self.bt = Hioki_BT3561A(BT_resource_str)
        self.sw = Hioki_SW1001(SW_resource_str)
        self.bt_function_type = "RV"

    def BT3561A_self_test(self) -> bool:
        """
        BT3561A self test.

        Returns:
            bool: True - Pass, False - Fail
        """
        return self.bt.self_test()

    def SW1001_self_test(self) -> bool:
        """
        SW1001 self test.

        Returns:
            bool: True - Pass, False - Fail
        """
        with self.sw as sw_dev:
            return sw_dev.self_test()

    def init(self) -> bool:
        """
        Some presets for the correct operation of the devices (BT3561A and SW1001)

        Returns:
            bool: True - no errors, otherwise False
        """
        result = True
        with self.sw as sw_dev:
            # CLS (SW1001)
            result &= sw_dev.clear_status()
            # OPEN (SW1001)
            result &= sw_dev.open()
            # Wire mode, slot 1 (SW1001)
            result &= sw_dev.set_wire_mode(1, 4)
            # Wire mode, slot 2 (SW1001)
            result &= sw_dev.set_wire_mode(2, 4)
            # Delay = 0, slot 1 (SW1001) (:SYST:MOD:DEL 1,0)
            result &= sw_dev.set_raw_command(":SYST:MOD:DEL 1,0")
            # Delay = 0, slot 2 (SW1001)
            result &= sw_dev.set_raw_command(":SYST:MOD:DEL 2,0")

        # CLS (BT3561A)
        result &= self.bt.clear_status()
        # HEADER OFF (BT3561A)
        result &= self.bt.set_raw_command(":SYST:HEAD OFF")
        # continuous measurement off (BT3561A)
        result &= self.bt.set_continous_measurement(0)
        # Trigger source: IMMEDIATE (BT3561A)
        result &= self.bt.set_trigger_source('IMM')
        # Comparator: OFF (BT3561A) (':CALC:LIM:STAT OFF')
        result &= self.bt.set_raw_command(":CALC:LIM:STAT OFF")
        # Set resistance range 0.1 Ohm
        result &= self.bt.set_resistance_range(0.1)
        # Set voltage range 6 V
        result &= self.bt.set_voltage_range(6)
        # Autorange = ON
        #result &= self.bt.set_autorange(1)
        # Set measurement = RV (BT3561A)
        result &= self.bt.set_function(self.bt_function_type)
        return result

    def measurement_finished(self) -> bool:
        """
        Returns the devices to init state.

        Returns:
            bool : True - success, False - failed
        """
        result = True
        result &= self.bt.set_continous_measurement(1)
        with self.sw as sw_dev:
            result &= sw_dev.open()
        return result

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
        resp = True
        result = []
        channel = int(channel)
        assert((channel >= 1) and (channel <= 22)), ValueError('Error, measure_channnel: Only channels 1 .. 22 are allowed')
        with self.sw as sw_dev:
            # SW1001 operations ==================
            if (channel <= 11):
                #SLOT 1
                resp &= sw_dev.close(1, channel)
            else:
                #SLOT 2
                channel = channel - 11
                resp &= sw_dev.close(2, channel)
        # BT3561A operations =================
        #[BT3561A] :READ? Execute single measurement using BT3561A.
        val = self.bt.read()
        try:
            if (self.bt_function_type == "RV"):
                lst = val.split(',')
                result.append(float(lst[0]))
                result.append(float(lst[1]))
            else:
                result.append(float(resp))
                result.append(float(0))
        except Exception:
            raise
        return result

    def measure_all_channels(self) -> list:
        """
        Measures voltage and impedance of all 22 channels.

        Returns:
            list: array[0..43]: float, Ch1.Impedance, Ch1.Voltage, Ch2.Impedance, Ch2.Voltage, ...
        """
        resp = True
        result = []
        with self.sw as sw_dev:
            for i in range(22):
                if (i < 11):
                    #SLOT 1
                    resp &= sw_dev.close(1, i+1)
                else:
                    #SLOT 2
                    resp &= sw_dev.close(2, (i-11)+1)
                #[BT3561A] :READ? Execute single measurement using BT3561A.
                sleep(0.1)
                val = self.bt.read()
                try:
                    if (self.bt_function_type == "RV"):
                        lst = val.split(',')
                        result.append(float(lst[0]))
                        result.append(float(lst[1]))
                    else:
                        result.append(float(resp))
                        result.append(float(0))
                except Exception:
                    raise
        return result
#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)


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
    #BT_IP_STR = "192.168.1.202"     # BT3561A IP addr
    #BT_PORT = 23                    # BT3561A port
    #SW_IP_STR = "192.168.1.201"     # SW1001 IP addr
    #SW_PORT = 23                    # SW1001 port
    BT_resource_string = "192.168.1.170:23"
    SW_resource_string = "192.168.1.201:23"

    # 1. Create an instance of 20 channel MUXER with HIOKI ACIR measurement device class
    #hioki = Hioki_Cell_Tester(BT_resource_string, SW_resource_string)
    hioki = Hioki_BT3561A(BT_resource_string)

    # # 2. ==== BT3561A functions ==========================================================================

    # Device initialization

    print(hioki.init())

    print(hioki.measure())

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

    # BT3561A_self_test
    #print("BT3561A self test:", hioki.BT3561A_self_test())

    # SW1001_self_test
    #print("SW1001 self test:", hioki.BT3561A_self_test())

    # Devices presets
    #print("Cell tester presets:", hioki.init())

    def check_meas(arr: list, ch: int) -> bool:
        print("Ch ", ch, " ", arr)
        if ((arr[0] >= 1 or arr[0] <= 0) or (arr[1] >= 4)):
            return False
        else:
            return True

    # measure single channel (1 ... 22)
    #err = 0   
    #for i in range(100):
        if (check_meas(hioki.measure_channnel(1), 1) == False):
            err += 1
        if (check_meas(hioki.measure_channnel(4), 4) == False):
            err += 1
        if (check_meas(hioki.measure_channnel(7), 7)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(10), 10)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(13), 13)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(15), 15)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(16), 16)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(18), 18)== False):
            err += 1
        if (check_meas(hioki.measure_channnel(19), 19)== False):
            err += 1
    #print("Errors count:", err)
    #print("Mesurement finished:", hioki.measurement_finished())

    # measure all 22 4-wire channels (Could be useful for Zero-adjustment procedure)
    #print(hioki.measure_all_channels())

    # ==================================================================================================

    print("DONE.")


# END OF FILE
