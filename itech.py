from typing import List, Tuple
from time import sleep
from rrc.visa import AdhocVisaDevice

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
class M3400(AdhocVisaDevice):
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
        super().__init__(resource_str, read_termination="\n", write_termination="\n", pause_on_retry=50)  # configure the itech VISA device
        self.last_mode = "??"  # not yet set
        self.dev_channel = dev_channel
        self.initialize_device()

    def __str__(self) -> str:
        return f"M3400 VISA device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"M3400({self.resource_str}, {self.dev_channel})"

    #----------------------------------------------------------------------------------------------
    # insert the channel to message strings for this device

    def send(self, msg: str, timeout: int = 1500) -> None:
        if (self.dev_channel > 0):
            #_chn = f"CHAN {self.dev_channel};"
            #_query = ";".join([_chn + p for p in msg.split(";")])
            _query = f"CHAN {self.dev_channel};{msg}"
        else:
            _query = msg
        super().send(_query, pause_after_write=15, timeout=timeout, retries=3)

    def request(self, msg: str, timeout: int = 3000) -> str:
        if (self.dev_channel > 0):
            _query = f"CHAN {self.dev_channel};{msg}"
        else:
            _query = msg
        return super().request(_query, pause_after_write=30, timeout=timeout, retries=3).strip()

    #----------------------------------------------------------------------------------------------

    def initialize_device(self) -> None:
        self.send("SYST:REM")     # set remote control ON
        self.reset_device()       # Reset device
        #self.send("OFF:VOLT CONST")  # CONST or ZERO -> for CC priority mode
        #self.send("FUNC:MODE FIX")   # FIX, LIST, BATT, BEM
        self.send("SENS:STAT 1")  # set sense state ON
        self.send("OUTP 0")       # set OUTPUT OFF
        sleep(0.25)

    #----------------------------------------------------------------------------------------------

    def reset_device(self):
        """
        Issues a reset by *RST resulting in these settings:

        SCPI Commands *RST Initial Settings:
        ...

        """
        self.send("*RST")  # Reset device
        #self.send("SYST:CLE")     # Clear error queue

    #----------------------------------------------------------------------------------------------

    def read_system_error(self) -> Tuple[int, str]:
        err_str = self.request_raw_query("SYSTEM:ERROR?")
        err = err_str.split(",")  # try to split on comma => int, str
        if len(err) < 2:
            err = err_str.split(" ")  # try to split on space
            if len(err < 2):
                raise ValueError(f"Error response not valid '{err_str}'.")
        return int(err[0]), str(err[1]).strip("\"")

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
        return tuple([float(m) for m in lst[:-1]])


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


    def configure_current_rise_times(self, pos: float | str = "DEF", neg: float | str = "DEF"):
        """Configures the current rise (negative rise = fall) times in seconds (s). 
        Need be called when device is configured for CC mode, otherwise device throws an execution error.

        Args:
            pos (float | str, optional): Positive time value in s or MIN=0.001, MAX=2000 or DEF=0.1. Defaults to "DEF".
            neg (float | str, optional): Positive time value in s or MIN=0.001, MAX=2000 or DEF=0.1. Defaults to "DEF".
        """
        self.send(f"CURRENT:SLEW:NEG {neg}")
        self.send(f"CURRENT:SLEW:POS {pos}")

    def configure_voltage_rise_times(self, pos: float | str = "DEF", neg: float | str = "DEF"):
        """Configures the voltage rise (negative rise = fall) times in seconds (s).
        Need be called when device is configured for CV mode, otherwise device throws an execution error.

        Args:
            pos (float | str, optional): Positive time value in s or MIN=0.001, MAX=2000 or DEF=0.1. Defaults to "DEF".
            neg (float | str, optional): Positive time value in s or MIN=0.001, MAX=2000 or DEF=0.1. Defaults to "DEF".
        """
        self.send(f"VOLTAGE:SLEW:NEG {neg}")
        self.send(f"VOLTAGE:SLEW:POS {pos}")


    def configure_sink(self, current: float, resistance: float | None,
                       current_limit: float, voltage_limit_high: float,
                       power_limit: float, set_output: bool = False) -> None:
        if self.last_mode != "CURR":
            self.set_output_state(0)  # make sure output is OFF
        self.set_function("CURR")  # CC priority
        self.send(f"POW:LIM:NEG {-abs(power_limit):0.2f}")
        self.send(f"POW:LIM:POS 0.0") # always fixed!
        #self.send(f"CURR:LIM:NEG {-abs(current_limit*1.1):0.3f}")
        #self.send(f"CURR:LIM:POS 0.0") # always fixed!
        self.send(f"VOLT:LIM:LOW 0.0") # always fixed!
        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:0.2f}")
        #self.send(f"VOLT {voltage_limit_high:0.2f}")
        self.send(f"CURR {-abs(current):0.3f}")
        if resistance is not None:
            self.send(f"SINK:RES {resistance:0.3f}")
            self.send("SINK:RES:STATE 1")
        else:
            self.send("SINK:RES:STATE 0")
            #self.send(f"CURR {-abs(current):0.3f}")
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
    # insert the channel to message strings for this device

    def send(self, msg: str, timeout: int = 1500) -> None:
        if (self.dev_channel > 0):
            #_chn = f"CHAN {self.dev_channel};"
            #_query = ";".join([_chn + p for p in msg.split(";")])
            _query = f"CHAN {self.dev_channel};{msg}"
        else:
            _query = msg
        super().send(_query, timeout=timeout)

    def request(self, msg: str, timeout: int = 3000) -> str:
        if (self.dev_channel > 0):
            _query = f"CHAN {self.dev_channel};{msg}"
        else:
            _query = msg
        return super().request(_query, timeout=timeout).strip()

    #----------------------------------------------------------------------------------------------
    # common function repeated as trampoline for TestStand only :-(

    def reset_device(self):
        """
        Issues a reset by *RST resulting in these settings:

        SCPI Commands *RST Initial Settings:

        ARB:COUNt 1
        ARB:CURRent:CDWell:DWELl 0.001
        ARB:FUNCtion:SHAPe CDW
        ARB:FUNCtion:TYPE VOLTage
        ARB:TERMinate:LAST OFF
        ARB:VOLTage:CDWell:DWELl 0.001
        CALibrate:STATe OFF
        CURRent 0
        CURRent:LIMit 1% of rating
        CURRent:LIMit:NEGative -1% of rating
        CURRent:MODE FIXed
        CURRent:PROTection:DELay 20ms
        CURRent:PROTection:STATe OFF
        CURRent:SHARing OFF
        CURRent:SLEW MAX
        CURRent:SLEW:MAXimum ON
        CURRent:TRIGgered 0
        FUNCtion VOLTage
        INITialize:CONTinuous:TRANsient OFF
        OUTPut OFF
        OUTPut:DELay:FALL 0
        OUTPut:DELay:RISE 0
        OUTPut:PROTection:WDOG OFF
        OUTPut:PROTection:WDOG:DELay 60
        RESistance 0
        RESistance:STATe 0
        TRIGger:ACQuire:CURRent 0
        TRIGger:ACQuire:CURRent:SLOPe POSitive
        TRIGger:ACQuire:SOURce BUS
        TRIGger:ACQuire:TOUTput OFF
        TRIGger:ACQuire:VOLTage 0
        TRIGger:ACQuire:VOLTage:SLOPe POSitive
        TRIGger:ARB:SOURce BUS
        TRIGger:TRANsient:SOURce BUS
        VOLTage 1% of rating
        VOLTage:LIMit 1% of rating
        VOLTage:MODE FIXed
        VOLTage:PROTection 120% of rating
        VOLTage:RESistance 0
        VOLTage:RESistance:STATe OFF
        VOLTage:SLEW MAX
        VOLTage:SLEW:MAXimum ON
        """

        self.send("*RST")       # Reset device
        self.send("SYST:CLE")  # Clear error queue


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

    # def configure_sink(self, current: float, resistance: float | None,
    #                    current_limit: float, voltage_limit_high: float, power_limit: float, set_output: bool = False) -> None:
    #     if self.last_mode != "CURR":
    #         self.set_output_state(0)  # make sure output is OFF
    #     self.set_function("CURR")  # CC priority


    def configure_charge_mode(self, current: float, voltage_limit_high: float, voltage_limit_low: float,
                              power_limit: float, set_output: bool = False) -> None:
        """
        Use to switch on battery charging mode. CC priority mode.
        M3900 device only.
        """
        self.configure_cc_mode(current, voltage_limit_high, voltage_limit_low, power_limit, set_output=set_output)


    def configure_discharge_mode(self, current: float,  voltage_limit_high: float, voltage_limit_low: float,
                                 power_limit: float, set_output: bool = False) -> None:
        """
        Use to switch on battery discharging mode. CC priority mode.
        M3900 device only.
        """
        self.configure_cc_mode(-abs(current), voltage_limit_high, voltage_limit_low, -abs(power_limit), set_output=set_output)


    def configure_wake_up_mode(self, current: float, voltage_limit_high: float, voltage_limit_low: float,
                               power_limit: float, set_output: bool = False) -> None:
        """
        Use to wake up bq40z50 or another bq chip. CC priority mode.
        M3900 device only.
        """
        self.configure_cc_mode(current, voltage_limit_high, voltage_limit_low, power_limit, set_output=set_output)


    def configure_cc_mode(self, current: float, voltage_limit_high: float, voltage_limit_low: float,
                            power_limit: float, set_output: bool = False) -> None:
        """Switches the PSU into CC priority mode. 
        
        Can be used to supply or sink depending on current sign.
        Use to wake up on battery without triggering a safety event.
        
        To configure supply, provide positive current and power limits,
        to sink set both negative.
        Positve and negative power limits at same time are not allowed here.

        NOTE: In CV mode which is used in configure_supply(), the bq IC triggers a ASCD failure. 
              M3900 device only.
        
        Args:
            current (float): Current limit in A, can be positive (supply) or negative (sink). Adjust sign of power limit accordingly.
            voltage_limit_high (float): upper voltage limit for regulation.
            voltage_limit_low (float): lower voltage limit for regulation.
            power_limit (float): Power limit ion W. The sign need to match the current's one.
            set_output (bool, optional): Enables (True) or disables (False) power terminals for supply or sink. Defaults to False.
        
        """

        # check that power limit and current have same sign
        if (current * power_limit) < 0:
            raise ValueError("Parameters current and power_limit need to have same sign.")

        if self.last_mode != "CURR":
            # was in different mode before: need to prepare settings
            self.set_output_state(0)            # make sure output is OFF
            #
            # Fix setup of M3900 to work correctly: use VOLT xx, then set device to CV priority mode
            # to allow changing the CURRENT limits before switching to CC prio. Otherwise, the
            # after power up the limits are set to 1%/-1% of rating which is 0.4A/-0.4A which 
            # causes CC mode to fail. We set the current limits to MIN/MAX as a change later is
            # not possible without throwing an error.
            #
            self.send(f"VOLT {voltage_limit_high:0.2f}")
            #print(self.read_system_error())
            self.send(f"CURR:LIM:NEG MIN")
            #print(self.read_system_error())
            self.send(f"CURR:LIM:POS MAX")
            #print(self.read_system_error())
   

        self.send(f"VOLT:LIM:HIGH {voltage_limit_high:0.2f}")
        #print(self.read_system_error())
        self.send(f"VOLT:LIM:LOW {voltage_limit_low:0.2f}")
        #print(self.read_system_error())
    
        self.send(f"POW:LIM:NEG {(power_limit if power_limit < 0 else -1):0.2f}")  # does not accept 0W !
        #print(self.read_system_error())
        self.send(f"POW:LIM:POS {(power_limit if power_limit > 0 else +1):0.2f}")  # does not accept 0W !
        #print(self.read_system_error())

        self.set_function("CURR")               # enable CC priority 
        #print(self.read_system_error())
        self.send("FUNC:MODE FIX")
        #print(self.read_system_error())

        self.send(f"CURR {current:0.2f}")       # set current for CC priority mode
        #print(self.read_system_error())

        # DO NOT use current limits in CC priority mode, it Causes an internal error of the M3900

        self.send("SINK:RES:STATE 0")
        #print(self.read_system_error())
        self.set_output_state(1 if set_output else 0)
        #print(self.read_system_error())


    def configure_sink(self, current: float, resistance: float | None,
                       current_limit: float, voltage_limit_high: float,
                       power_limit: float, set_output: bool = False) -> None:
        # because of TS does not see base class
        super().configure_sink(current, resistance, current_limit, voltage_limit_high, power_limit, set_output=set_output)
    

    def configure_supply(self, voltage: float, current_limit: float, power_limit: float, set_output: bool = False) -> None:
        # because of TS does not see base class
        super().configure_supply(voltage, current_limit, power_limit, set_output=set_output)  


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