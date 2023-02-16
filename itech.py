from typing import List
from time import sleep
from rrc.eth2serial.base_visa import Eth2SerialVisaDevice
import math

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
class M3400(Eth2SerialVisaDevice):
    #
    # Currently there are two backends available: The one included in pyvisa,
    # which uses the IVI library (include NI-VISA, Keysight VISA, R&S VISA, tekVISA etc.),
    # and the backend provided by pyvisa-py, which is a pure python implementation
    # of the VISA library.
    # If no backend is specified, pyvisa uses the IVI backend if any IVI library
    # has been installed (see next section for details). Failing that, it uses the
    # pyvisa-py backend.
    # explicit Python backend:  rm = ResourceManager('@py')
    # explicit IVI lib backend: rm = ResourceManager('Path to library')
#--------------------------------------------------------------------------------------------------
    # Commands:
    #
    # For measuring purpose:
    #
	# + MEASure[:SCALar]:CURRent[:DC]?
	# + MEASure[:SCALar]:VOLTage[:DC]?
	# + MEASure[:SCALar]:UUT:TEMPerature?
	# + MEASure?
    #
    #For device setup and state determination:
    #
	# + OUTPut[:STATe] <bool>
	# + SENSe[:REMote][:STATe] <bool>
	# + OUTPut:REVerse[:STATe]?
	# + [SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
	# + [SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
	# + [SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
	# + [SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
	# + [SOURce:]CURRent:UNDer:PROTection[:LEVel] <NRf+>
    #
	# + [SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>
	# + [SOURce:]VOLTage[:LEVel]:LIMit[:HIGH] <NRf+>
	# + [SOURce:]VOLTage[:LEVel]:LIMit:LOW <NRf+>
	# + [SOURce:]VOLTage[:OVER]:PROTection[:LEVel] <NRf+>
	# + [SOURce:]VOLTage:UNDer:PROTection[:LEVel] <NRf+>


    def __init__(self, resource_str: str, dev_channel: int = 0):
        """
        Initialize the object with VISA resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        In fact this M3400 device is using an IT-E1206 LAN gateway to access the PSUs behind.

        We have 6 PSUs indexed from channel 1 to 6. The communication module
        Eth2SerialVisaDevice takes care about the routing command.

        Args:
            resource_str (str): visa resource string
            dev_channel (int, optional): indexes the real PSU behind the gateway, 0=off, 1..6. Defaults to 0.

        """
        super().__init__(resource_str, dev_channel)
        self.last_mode = "??"  # not yet set
        self.initialize_device()

    def __str__(self) -> str:
        return f"M3400 VISA device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"M3400({self.resource_str}, {self.dev_channel})"

    #----------------------------------------------------------------------------------------------

    def initialize_device(self) -> None:        
        self.send("SYST:REM")     # set remote control ON        
        self.send("SENS:STAT 1")  # set sense state ON        
        self.send("OUTP 0")       # set OUTPUT OFF
        sleep(0.25)

    #----------------------------------------------------------------------------------------------

    # def set_remote_control(self) -> None:
    #     """
    #     This command clears the system status register.
    #     IT M3400 and M3900 devices
    #     """
    #     self.send("SYST:REM")

    def send_raw_command(self, cmd: str) -> None:
        """
        Sets raw SCPI command and returns error.

        Args:
            cmd (str): SCPI command
        """
        self.send(str(cmd))

    def request_raw_query(self, cmd: str) -> str:
        """
        Sets raw SCPI query and returns the result or error.

        Args:
            cmd (str): SCPI command

        Returns:
            str: response
        """
        return self.request(str(cmd))


    def get_current_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_current(), ndigits=int(ndigits))

    def get_current(self) -> float:
        """
        This command queries the present current measurement.
        IT M3400 and M3900 devices

        Returns:
            float: ADC
        """
        return float(self.request("FETC:CURR?"))


    def get_voltage_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_voltage(), ndigits=int(ndigits))

    def get_voltage(self) -> float:
        """
        This command queries the present measured voltage.
    
        Returns:
            float: VDC
        """
        return float(self.request("FETC:VOLT?"))


    def get_temperature_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_temperature(), ndigits=int(ndigits))

    def get_temperature(self) -> float:
        """
        This command queries the measured UUT temperature.
        IT M3400 devices

        Returns:
            float: temperature
        """
        cmd = "FETC:UUT:TEMP?"
        return float(self.request(cmd, 2000))


    def get_all_measurements(self) -> list:
        """
        This command queries the present voltage measurement, current
        measurement and power measurement.
     
        Returns:
            list[5], float:  voltage, current, power, amp-hour, watt-hour
        """
        result = self.request("FETC?")
        # 5 results - string "###, ###, ###, ###, ###"
        # voltage, current, power, amp-hour, watt-hour
        lst = str(result).split(',')
        return tuple([float(m) for m in lst])


    def set_output_state(self, state: int) -> bool:
        """
        This command sets the output state of the power supply.
        IT M3400 and M3900 devices.

        Args:
            state (int):  1 - On, 0 - Off
        """
        # trick to use function in NI Teststand
        self.send(f"OUTP {int(state)}")
        #r = self.request(f"OUTPUT:STATE {int(state)};OUTPUT:STATE?")
        #return int(r) == int(state)
        sleep(0.25)
        #self._helper_wait_for_result("OUTP?", [str(int(state))])  # wait for correct output state
        return True

    # def get_output_state(self) -> int:
    #     """
    #     This command sets the output state of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         int: state, 1 - On, 0 - Off
    #     """
    #     return int(self.request("OUTP?"))
    

    # def set_sense_state(self, state: int) -> None:
    #     """
    #     This command enables or disables the sense function.
    #     IT M3400 devices.

    #     Args:
    #         state (int): state: int 1|0 

    #     Raises:
    #         ValueError: invalid parameters
    #     """
    #     # trick to use function in NI Teststand
        
    #     self.send(f"SENS:STAT {1 if int(state) > 0 else 0}")
    #     # _s = 1 if int(state) > 0 else 0
    #     #r = self.request(f"SENS:STAT {_s}; STAT?")
    #     #return int(r) == int(state)
    #     #self._helper_wait_for_result("SENS?", [str(_s)])  # wait for correct output state


    # def get_sense_state(self) -> int:
    #     """
    #     This command sets the output state of the power supply
    #     IT M3400 devices.

    #     Returns:
    #         int: sense, 1 - On, 0 - Off
    #     """
    #     return int(self.request("SENS?"))


    # def get_output_reverse_state(self) -> int:
    #     """
    #     This command is used to query the connection of output terminals.
    #     IT M3400 devices

    #     Returns:
    #         int: state, 1 - On, 0 - Off
    #     """
    #     cmd = "OUTP:REV?"
    #     return int(self.request(cmd, 2000))

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_current(self, curr: float) -> None:
        """
        This command sets the current value of the power supply.
        The query form of this command gets the set current value of the power supply.
        IT M3400 and M3900 devices

        Args:
            curr (float): current 'X.XXX' Amp
        """
        self.send(f"CURR {curr:0.3f}")
        

    # def get_current_rounded(self, ndigits: int = 3) -> float:
    #     return round(self.get_current(), ndigits=int(ndigits))

    # #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    # def get_current(self) -> float:
    #     """
    #     This command gets the current value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         float: current
    #     """
    #     cmd = "CURR?"
    #     return float(self.request(cmd, 2000))

    # #[SOURce:]CURRent:SLEW:POSitive <NRf+>
    # def set_current_slew_positive(self, rate: float) -> None:
    #     """
    #     This command sets the current rising slew rate of the power supply.

    #     Args:
    #         rate (float): current slew rate, seconds
    #     """
    #     try:
    #         rate = float(rate)
    #         rate_str =  f"{rate:05.2f}"
    #         cmd = "CURR:SLEW:POS " + rate_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    # #[SOURce:]CURRent:SLEW:NEGative <NRf+>
    # def set_current_slew_negative(self, rate: float) -> None:
    #     """
    #     This command sets the current falling slew rate of the power supply.

    #     Args:
    #         rate (float): current slew rate, seconds
    #     """
    #     try:
    #         rate = float(rate)
    #         rate_str =  f"{rate:05.2f}"
    #         cmd = "CURR:SLEW:NEG " + rate_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    # #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    # def set_current_limit_positive(self, curr: float) -> None:
    #     """
    #     This command sets the positive current limit value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         curr (float): current limit 'XX.XXX' Amps
    #     """
    #     try:
    #         param_str =  f"{curr:06.3f}"
    #         cmd = 'CURR:LIM:POS ' + param_str
    #         self.send(cmd, 2000)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    # def get_current_limit_positive(self) -> float:
    #     """
    #     This command gets the positive current limit value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         float: current limit
    #     """
    #     try:
    #         cmd = "CURR:LIM:POS?"
    #         return float(self.request(cmd, 2000))
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    # def set_current_limit_negative(self, curr: float) -> None:
    #     """
    #     This command sets the negative current limit value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         curr (float): current limit '-XX.XXX' Amps
    #     """
    #     try:
    #         param_str =  f"{curr:07.3f}"
    #         cmd = 'CURR:LIM:NEG ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    # def get_current_limit_negative(self) -> float:
    #     """
    #     This command gets the negative current limit value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         float: current limit
    #     """
    #     try:
    #         cmd = "CURR:LIM:NEG?"
    #         return float(self.request(cmd, 2000))
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
    # def set_current_protection(self, curr: float) -> None:
    #     """
    #     This command sets the over current limit of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         curr (float): current protection 'XX.XXX' Amps
    #     """
    #     try:
    #         param_str =  f"{curr:06.3f}"
    #         cmd = 'CURR:PROT ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
    # def get_current_protection(self) -> float:
    #     """
    #     This command gets the over current limit of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         float: current protection
    #     """
    #     try:
    #         cmd = "CURR:PROT?"
    #         return float(self.request(cmd, 2000))
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]CURRent:UNDer:PROTection[:LEVel] <NRf+>
    # def set_current_under_protection(self, curr: float) -> None:
    #     """
    #     This command sets the under current limit of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         curr (_type_): current under protection 'XX.XXX' Amps
    #     """
    #     try:
    #         param_str =  f"{curr:06.3f}"
    #         cmd = 'CURR:UND:PROT ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    #[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_voltage(self, volt: float) -> None:
        """
        This command sets the voltage value of the power supply.
        IT M3400 and M3900 devices.
        Args:
            volt (float): voltage 'X.XX' Volts
        """
        self.send(f"VOLT {volt:0.2f}")

        
    # #[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    # def get_voltage(self) -> float:
    #     """
    #     The query form of this command gets the set voltage value of the power supply.
    #     IT M3400 and M3900 devices.

    #     Returns:
    #         float: voltage
    #     """
    #     try:
    #         cmd = 'VOLT?'
    #         return float(self.request(cmd, 2000))
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]VOLTage:SLEW:POSitive <NRf+>
    # def set_voltage_slew_positive(self, rate: float) -> None:
    #     """
    #     This command sets the voltage rising slew rate of the power supply.

    #     Args:
    #         rate (float): voltage slew rate, seconds
    #     """
    #     try:
    #         rate = float(rate)
    #         rate_str =  f"{rate:05.2f}"
    #         cmd = "VOLT:SLEW:POS " + rate_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    # #[SOURce:]VOLTage:SLEW:NEGative <NRf+>
    # def set_curren_slew_negative(self, rate: float) -> None:
    #     """
    #     This command sets the voltage falling slew rate of the power supply.

    #     Args:
    #         rate (float): voltage slew rate, seconds
    #     """
    #     try:
    #         rate = float(rate)
    #         rate_str =  f"{rate:05.2f}"
    #         cmd = "VOLT:SLEW:NEG " + rate_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    # #[SOURce:]VOLTage[:LEVel]:LIMit[:HIGH] <NRf+>
    # def set_voltage_limit_high(self, volt: float) -> None:
    #     """
    #     This command sets voltage upper limit under CC priority mode.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         volt (float): voltage limit 'XX.XX' Volts
    #     """
    #     try:
    #         param_str =  f"{volt:05.2f}"
    #         cmd = 'VOLT:LIM:HIGH ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]VOLTage[:LEVel]:LIMit:LOW <NRf+>
    # def set_voltage_limit_low(self, volt: float) -> None:
    #     """
    #     This command sets voltage lower limit under CC priority mode.
    #     IT M3400 devices.

    #     Args:
    #         volt (float): voltage limit 'XX.XX' Volts
    #     """
    #     try:
    #         param_str =  f"{volt:05.2f}"
    #         cmd = 'VOLT:LIM:LOW ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]VOLTage[:OVER]:PROTection[:LEVel] <NRf+>
    # def set_voltage_protection(self, volt: float) -> None:
    #     """
    #     This command sets the over voltage limit of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         volt (float): voltage protection 'XX.XX' Volts
    #     """
    #     try:
    #         param_str =  f"{volt:05.2f}"
    #         cmd = 'VOLT:PROT ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # #[SOURce:]VOLTage:UNDer:PROTection[:LEVel] <NRf+>
    # def set_voltage_under_protection(self, volt: float) -> None:
    #     """
    #     This command sets the under voltage limit of the power supply.
    #     IT M3400 and M3900 devices.

    #     Args:
    #         volt (float): voltage under protection
    #     """
    #     try:
    #         param_str =  f"{volt:05.2f}"
    #         cmd = 'VOLT:UND:PROT ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         #_log.exception(ex)
    #         raise

    # def set_power_limit_positive(self, power: float):
    #     """
    #     This command is used to set the power upper limit value.

    #     Args:
    #         power (float): power limit value, Watt.
    #     """
    #     power = float(power)
    #     try:
    #         param_str =  f"{power:05.2f}"
    #         cmd = 'POW:LIM ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    # def set_power_limit_negative(self, power: float):
    #     """
    #     This command is used to set the power lower limit value.

    #     Args:
    #         power (float): power limit value, Watt.
    #     """
    #     power = float(power)
    #     try:
    #         param_str =  f"{power:05.2f}"
    #         cmd = 'POW:LIM:NEG ' + param_str
    #         self.send(cmd)
    #     except Exception as ex:
    #         raise

    def _helper_wait_for_result(self, query:str, expected_result: List[str], loops: int = 20) -> None:
        for n in range(loops):
            r = self.request(query, timeout=5000)
            if any(e in r for e in expected_result):
                return True
            sleep(0.1)
        raise TimeoutError(f"Could not get desired result '{expected_result}'")


    def set_function(self, func: str = "VOLT") -> bool:
        """
        This command is used to set the working mode of the power supply.

        Args:
            func (str, optional): VOLT or CURR mode. Defaults to "VOLT".
        """
        assert(func in ["VOLT", "CURR"]), ValueError('Error, set_function: only "VOLT", "CURR" allowed')
        self.last_mode = func
        self.send(f"FUNC {func}")
        sleep(0.1)
        #self.send(f"FUNC {func}")
        #r = self.request("FUNC?")
        #return func in r
        #self._helper_wait_for_result("FUNC?", [str(func)])
        return True

        
    def configure_current_rise_times(self, pos: float| str = "MIN", neg: float | str = "MIN"):
        self.send(f"CURRENT:SLEW:NEG {neg:0.3f}; SLEW:POS {pos:0.3f}")
        #self.send(f"CURRENT:SLEW:POS {pos:0.3f}")

    def configure_voltage_rise_times(self, pos: float | str = "MIN", neg: float | str = "MIN"):
        self.send(f"VOLTAGE:SLEW:NEG {neg:0.3f}; SLEW:POS {pos:0.3f}")
        #self.send(f"VOLTAGE:SLEW:POS {pos:0.3f}")


    def configure_sink(self, current: float, resistance: float | None,
                       current_limit: float, voltage_limit_high: float, 
                       power_limit: float, set_output: bool = False) -> None:
        if self.last_mode != "CURR":
            self.set_output_state(0)  # make sure output is OFF
        self.set_function("CURR")  # CC priority
        self.send(f"POW:LIM:NEG {-abs(power_limit):0.2f}")
        self.send(f"POW:LIM:POS 0.0") # always fixed!
        self.send(f"CURR:LIM:NEG {-abs(current_limit):0.3f}")
        self.send(f"CURR:LIM:POS 0.0") # always fixed!        
        self.send(f"VOLT:LIM:LOW 0.0") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:0.2f}")
        #self.send(f"VOLT {voltage_limit_high:0.2f}")
        self.send(f"CURR {-abs(current):0.3f}")        
        if resistance is not None:
            self.send(f"SINK:RES {resistance:0.3f}")
            self.send("SINK:RES:STATE 1")            
        else:
            self.send("SINK:RES:STATE 0")
        self.set_output_state(1 if set_output else 0)

    def configure_supply(self, voltage: float, current_limit: float, power_limit: float, set_output: bool = False) -> None:
        if self.last_mode != "VOLT":
            self.set_output_state(0)  # make sure output is OFF
        self.set_function("VOLT")
        self.send(f"POW:LIM:NEG 0.0") # always fixed!
        self.send(f"POW:LIM:POS {abs(power_limit):0.2f}")
        self.send(f"CURR:LIM:NEG 0.0") # always fixed!
        self.send(f"CURR:LIM:POS {abs(current_limit):0.3f}")
        self.send(f"VOLT:LIM:LOW 0.0") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage:0.2f}")
        #self.send(f"CURR {abs(current_limit):0.3f}")
        self.send(f"VOLT {voltage:0.2f}")
        self.send("SINK:RES:STATE 0")       
        self.set_output_state(1 if set_output else 0)


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class M3900(M3400):

    def __init__(self, resource_str: str, dev_channel: int = 0):
        """
        Initialize the object with VISA resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
            dev_channel (int, optional): 0=off, 1 .. n selects a proprietary device behind the gateway. Defaults to 0.

        """
        super().__init__(resource_str, dev_channel)
        pass

    def __str__(self) -> str:
        return f"M3900 VISA device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"M3900({self.resource_str}, {self.dev_channel})"

    #----------------------------------------------------------------------------------------------
    # common function repeated as trampoline for TestStand only :-(

    #def set_remote_control(self) -> None:
    #    super().set_remote_control()

    def initialize_device(self) -> None:
        super().initialize_device()

    def send_raw_command(self, cmd: str) -> None:
        super().send_raw_command(cmd)

    def request_raw_query(self, cmd: str) -> str:
        return super().request_raw_query(cmd)

    #def get_ADC_rounded(self, ndigits: int = 3) -> float:
    #    return super.get_ADC_rounded(ndigits=int(ndigits))

    #def get_ADC(self) -> float:
    #    return super().get_ADC()

    #def get_VDC_rounded(self, ndigits: int = 3) -> float:
    #    return super().get_VDC_rounded(ndigits=int(ndigits))

    #def get_VDC(self) -> float:
    #    return super().get_VDC()

    #def get_temp_rounded(self, ndigits: int = 3) -> float:
    #    return super().get_temp_rounded(ndigits=int(ndigits))

    #def get_temp(self) -> float:
    #    return super().get_temp()

    def get_all_meas(self) -> list:
        return super().get_all_meas()

    def set_output_state(self, state: int) -> None:
        super().set_output_state(int(state))

    #def get_output_state(self) -> int:
    #    return super().get_output_state()

    #def set_current(self, curr: float) -> None:
    #    super().set_current(curr)

    #def get_current_rounded(self, ndigits: int = 3) -> float:
    #    return super().get_current_rounded(ndigits=int(ndigits))

    def get_current(self) -> float:
        return super().get_current()

    #def set_current_limit_positive(self, curr: float) -> None:
    #    super().set_current_limit_positive(curr)

    #def get_current_limit_positive(self) -> float:
    #    return super().get_current_limit_positive()

    #def set_current_limit_negative(self, curr: float) -> None:
    #    super().set_current_limit_negative(curr)

    #def get_current_limit_negative(self) -> float:
    #    return super().get_current_limit_negative()

    #def set_current_protection(self, curr: float) -> None:
    #    super().set_current_protection(curr)

    #def get_current_protection(self) -> float:
    #    return super().get_current_protection()

    #def set_current_under_protection(self, curr: float) -> None:
    #    super().set_current_under_protection(curr)

    #def set_voltage(self, volt: float) -> None:
    #    super().set_voltage(volt)

    def get_voltage(self) -> float:
        return super().get_voltage()

    #def set_voltage_limit_high(self, volt: float) -> None:
    #    super().set_voltage_limit_high(volt)

    #def set_voltage_limit_low(self, volt: float) -> None:
    #    super().set_voltage_limit_low(volt)

    #def set_voltage_protection(self, volt: float) -> None:
    #    super().set_voltage_protection(volt)

    #def set_voltage_under_protection(self, volt: float) -> None:
    #    super().set_voltage_under_protection(volt)

    #def set_power_limit_positive(self, power: float) -> None:
    #    super().set_power_limit_positive(power)

    #def set_power_limit_negative(self, power: float) -> None:
    #    super().set_power_limit_negative(power)

    def set_function(self, func: str) -> None:
        super().set_function(func)

    #----------------------------------------------------------------------------------------------
    #def set_resistance_mode(self, mode: int):
    #    """M3900 device only."""
    #    try:
    #       mode = int(mode)
    #       assert((mode == 1) or (mode == 0)), ValueError('Error, set_resistance_mode: only 1 or 0 allowed')
    #       cmd = "SINK:RES:STAT " + str(mode)
    #       self.send(cmd)
    #    except Exception as ex:
    #        raise

    #def set_resistance(self, resist: int):
    #    """M3900 device only."""
    #    try:
    #        resist = int(resist)
    #        assert((resist > 0) and (resist < 2500)), ValueError('Error, set_resistance: only 0 ... 2500 Ohm allowed')
    #        cmd = "SINK:RES " + str(resist)
    #        self.send(cmd)
    #    except Exception as ex:
    #        raise

    def configure_sink(self, current: float, resistance: float | None,
                       current_limit: float, voltage_limit_high: float, power_limit: float, set_output: bool = False) -> None:
        if self.last_mode != "CURR":
            self.set_output_state(0)  # make sure output is OFF
        self.set_function("CURR")  # CC priority
               

    def configure_charge_mode(self, current: float, current_limit: float, 
                       voltage_limit_high: float, power_limit: float, set_output: bool = False) -> None:
        """
        Use to switch on battery charging mode. CC mode.
        M3900 device only.
        """
        if self.last_mode != "CURR":
            self.set_output_state(0)            # make sure output is OFF
        self.set_function("CURR")               # CC priority     
        self.send(f"POW:LIM:NEG {0.0:05.2f}")
        self.send(f"POW:LIM:POS {power_limit:05.2f}") # always fixed!
        self.send(f"CURR:LIM:NEG {0.0:06.3f}")
        self.send(f"CURR:LIM:POS {current_limit:06.3f}") # always fixed!        
        self.send(f"VOLT:LIM:LOW {0.0:05.2f}") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:05.2f}")
        self.send(f"CURR {current:06.3f}") 
        self.send("SINK:RES:STATE 0")
        self.set_output_state(1 if set_output else 0)


    def configure_discharge_mode(self, current: float, current_limit: float, 
                       voltage_limit_high: float, power_limit: float, set_output: bool = False) -> None:
        """
        Use to switch on battery discharging mode. CC mode.
        M3900 device only.
        """
        if self.last_mode != "CURR":
            self.set_output_state(0)            # make sure output is OFF
        self.set_function("CURR")               # CC priority     
        self.send(f"POW:LIM:NEG {power_limit:05.2f}")
        self.send(f"POW:LIM:POS {0.0:05.2f}") # always fixed!
        self.send(f"CURR:LIM:NEG {current_limit:06.3f}")
        self.send(f"CURR:LIM:POS {0.0:06.3f}") # always fixed!        
        self.send(f"VOLT:LIM:LOW {0.0:05.2f}") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:05.2f}")
        self.send(f"CURR {current:06.3f}") 
        self.send("SINK:RES:STATE 0")
        self.set_output_state(1 if set_output else 0)

    def configure_wake_up_mode(self, current: float, current_limit: float, 
                       voltage_limit_high: float, power_limit: float, set_output: bool = False) -> None:
        """
        Use to wake up bq40z50 or another bq chip. CV mode.
        M3900 device only.
        """
        if self.last_mode != "CURR":
            self.set_output_state(0)            # make sure output is OFF
        self.set_function("CURR")               # CC priority   
        param = f"POW:LIM:NEG {0.0:05.2f}"  
        self.send(param)
        param = f"POW:LIM:POS {power_limit:05.2f}"
        self.send(param) # always fixed!
        param = f"CURR:LIM:NEG {0.0:06.3f}"
        self.send(param)
        param = f"CURR:LIM:POS {current_limit:06.3f}"
        self.send(param) # always fixed!        
        self.send(f"VOLT:LIM:LOW {0.0:05.2f}") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:05.2f}")
        self.send(f"CURR {current:06.3f}") 
        self.send("SINK:RES:STATE 0")
        self.set_output_state(1 if set_output else 0)


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # TESTS have been moved out to module: test_itech.py
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    print("DONE.")

# END OF FILE