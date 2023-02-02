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

    # BATTery:MODE <CPD>
    # BATTery:MODE?
    # BATTery:CHARge:VOLTage <NRf+>
    # BATTery:CHARge:VOLTage? [MINimum|MAXimum|DEFault]
    # BATTery:CHARge:CURRent <NRf+>
    # BATTery:CHARge:CURRent? [MINimum|MAXimum|DEFault]
    # BATTery:DISCharge:VOLTage <NRf+>
    # BATTery:DISCharge:VOLTage? [MINimum|MAXimum|DEFault]
    # BATTery:DISCharge:CURRent <NRf+>
    # BATTery:DISCharge:CURRent? [MINimum|MAXimum|DEFault]
    # BATTery:SHUT:VOLTage <NRf+>
    # BATTery:SHUT:VOLTage? [MINimum|MAXimum|DEFault]
    # BATTery:SHUT:CURRent <NRf+>
    # BATTery:SHUT:CURRent? [MINimum|MAXimum|DEFault]
    # BATTery:SHUT:CAPacity <NRf+>
    # BATTery:SHUT:CAPacity? [MINimum|MAXimum|DEFault]
    # BATTery:SHUT:TIME <NRf+>
    # BATTery:SHUT:TIME? [MINimum|MAXimum|DEFault]

    def __init__(self, resource_str: str, channel: int):
        """
        Initialize the object with VISA resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
        """
        super().__init__(resource_str, channel)
        pass

    def __str__(self) -> str:
        return f"M3400 VISA device on {self.super().__str__()}"

    def __repr__(self) -> str:
        return f"M3400({self.resource_str}, {self.channel})"

    #----------------------------------------------------------------------------------------------

    def set_remote_control(self) -> None:
        """
        This command clears the system status register.
        IT M3400 and M3900 devices
        """
        cmd = "SYST:REM"
        self.send(cmd)

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


    def get_ADC_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_ADC(), ndigits=int(ndigits))

    def get_ADC(self) -> float:
        """
        This command queries the present current measurement.
        IT M3400 and M3900 devices

        Returns:
            float: ADC
        """
        cmd = "FETC:CURR?"
        return float(self.request(cmd, 2000))


    def get_VDC_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_VDC(), ndigits=int(ndigits))

    def get_VDC(self) -> float:
        """
        This command queries the present measured voltage.
        IT M3400 and M3900 devices

        Returns:
            float: VDC
        """
        cmd = "FETC:VOLT?"
        return float(self.request(cmd, 2000))


    def get_temp_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_temp(), ndigits=int(ndigits))

    def get_temp(self) -> float:
        """
        This command queries the measured UUT temperature.
        IT M3400 devices

        Returns:
            float: temperature
        """
        cmd = "FETC:UUT:TEMP?"
        return float(self.request(cmd, 2000))


    def get_all_meas(self) -> list:
        """
        This command queries the present voltage measurement, current
        measurement and power measurement.
        IT M3400 and M3900 devices

        Returns:
            list[5], float:  voltage, current, power, amp-hour, watt-hour
        """
        try:
            cmd = "FETC?"
            result = self.request(cmd, 2000)
            # 5 results - string "###, ###, ###, ###, ###"
            lst = str(result).split(',')
            result = []
            result.append(float(lst[0]))    # voltage
            result.append(float(lst[1]))    # current
            result.append(float(lst[2]))    # power
            result.append(float(lst[3]))    # amp-hour
            result.append(float(lst[4]))    # watt-hour
            return result
        except Exception as ex:
            #_log.exception(ex)
            raise


    def set_output_state(self, state: int) -> None:
        """
        This command sets the output state of the power supply.
        IT M3400 and M3900 devices.

        Args:
            state (int):  1 - On, 0 - Off
        """
        # trick to use function in NI Teststand
        state = int(state)
        cmd = f'OUTP {state}'
        self.send(cmd)

    def get_output_state(self) -> int:
        """
        This command sets the output state of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            int: state, 1 - On, 0 - Off
        """
        cmd = "OUTP?"
        return int(self.request(cmd, 2000))

    def set_sense_state(self, state: int):
        """
        This command enables or disables the sense function.
        IT M3400 devices.

        Args:
            state (int or str): state: int 1|0 or string 'ON'|'OFF'

        Raises:
            ValueError: invalid parameters
        """
        # trick to use function in NI Teststand
        state = int(state)
        assert((state == 0) or (state == 1)), ValueError('Error, set_output_state: only 1 or 0 allowed')
        cmd = f'SENS {state}'
        self.send(cmd)

    def get_sense_state(self) -> int:
        """
        This command sets the output state of the power supply
        IT M3400 devices.

        Returns:
            int: sense, 1 - On, 0 - Off
        """
        cmd = "SENS?"
        return int(self.request(cmd, 2000))

    def get_output_reverse_state(self) -> int:
        """
        This command is used to query the connection of output terminals.
        IT M3400 devices

        Returns:
            int: state, 1 - On, 0 - Off
        """
        cmd = "OUTP:REV?"
        return int(self.request(cmd, 2000))

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_current(self, curr: float) -> None:
        """
        This command sets the current value of the power supply.
        The query form of this command gets the set current value of the power supply.
        IT M3400 and M3900 devices

        Args:
            curr (float): current 'XX.XXX' Amp
        """
        try:
            param_str =  f"{curr:06.3f}"
            cmd = 'CURR ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise


    def get_current_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_current(), ndigits=int(ndigits))

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def get_current(self) -> float:
        """
        This command gets the current value of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            float: current
        """
        cmd = "CURR?"
        return float(self.request(cmd, 2000))

    #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    def set_current_limit_positive(self, curr: float) -> None:
        """
        This command sets the positive current limit value of the power supply.
        IT M3400 and M3900 devices.

        Args:
            curr (float): current limit 'XX.XXX' Amps
        """
        try:
            param_str =  f"{curr:06.3f}"
            cmd = 'CURR:LIM:POS ' + param_str
            self.send(cmd, 2000)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    def get_current_limit_positive(self) -> float:
        """
        This command gets the positive current limit value of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            float: current limit
        """
        try:
            cmd = "CURR:LIM:POS?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    def set_current_limit_negative(self, curr: float) -> None:
        """
        This command sets the negative current limit value of the power supply.
        IT M3400 and M3900 devices.

        Args:
            curr (float): current limit '-XX.XXX' Amps
        """
        try:
            param_str =  f"{curr:07.3f}"
            cmd = 'CURR:LIM:NEG ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    def get_current_limit_negative(self) -> float:
        """
        This command gets the negative current limit value of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            float: current limit
        """
        try:
            cmd = "CURR:LIM:NEG?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
    def set_current_protection(self, curr: float) -> None:
        """
        This command sets the over current limit of the power supply.
        IT M3400 and M3900 devices.

        Args:
            curr (float): current protection 'XX.XXX' Amps
        """
        try:
            param_str =  f"{curr:06.3f}"
            cmd = 'CURR:PROT ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
    def get_current_protection(self) -> float:
        """
        This command gets the over current limit of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            float: current protection
        """
        try:
            cmd = "CURR:PROT?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]CURRent:UNDer:PROTection[:LEVel] <NRf+>
    def set_current_under_protection(self, curr: float) -> None:
        """
        This command sets the under current limit of the power supply.
        IT M3400 and M3900 devices.

        Args:
            curr (_type_): current under protection 'XX.XXX' Amps
        """
        try:
            param_str =  f"{curr:06.3f}"
            cmd = 'CURR:UND:PROT ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_voltage(self, volt: float) -> None:
        """
        This command sets the voltage value of the power supply.
        IT M3400 and M3900 devices.
        Args:
            volt (float): voltage 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def get_voltage(self) -> float:
        """
        The query form of this command gets the set voltage value of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            float: voltage
        """
        try:
            cmd = 'VOLT?'
            return float(self.request(cmd, 2000))
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage[:LEVel]:LIMit[:HIGH] <NRf+>
    def set_voltage_limit_high(self, volt: float) -> None:
        """
        This command sets voltage upper limit under CC priority mode.
        IT M3400 and M3900 devices.

        Args:
            volt (float): voltage limit 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT:LIM ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage[:LEVel]:LIMit:LOW <NRf+>
    def set_voltage_limit_low(self, volt: float) -> None:
        """
        This command sets voltage lower limit under CC priority mode.
        IT M3400 devices.

        Args:
            volt (float): voltage limit 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT:LIM:LOW ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage[:OVER]:PROTection[:LEVel] <NRf+>
    def set_voltage_protection(self, volt: float) -> None:
        """
        This command sets the over voltage limit of the power supply.
        IT M3400 and M3900 devices.

        Args:
            volt (float): voltage protection 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT:PROT ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    #[SOURce:]VOLTage:UNDer:PROTection[:LEVel] <NRf+>
    def set_voltage_under_protection(self, volt: float) -> None:
        """
        This command sets the under voltage limit of the power supply.
        IT M3400 and M3900 devices.

        Args:
            volt (float): voltage under protection
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT:UND:PROT ' + param_str
            self.send(cmd)
        except Exception as ex:
            #_log.exception(ex)
            raise

    def set_power_limit_positive(self, power: float):
        """
        This command is used to set the power upper limit value.

        Args:
            power (float): power limit value, Watt.
        """
        power = float(power)
        try:
            param_str =  f"{power:05.2f}"
            cmd = 'POW:LIM ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    def set_power_limit_negative(self, power: float):
        """
        This command is used to set the power lower limit value.

        Args:
            power (float): power limit value, Watt.
        """
        power = float(power)
        try:
            param_str =  f"{power:05.2f}"
            cmd = 'POW:LIM:NEG ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    def set_function(self, func: str = "VOLT") -> None:
        """
        This command is used to set the working mode of the power supply.

        Args:
            func (str, optional): CV or CC mode. Defaults to "VOLT".
        """
        try:
            assert(func in ["VOLT", "CV", "CURR", "CC"]), ValueError('Error, set_function: only "VOLT", "CURR", "CV" or "CC" allowed')
            cmd = "FUNC " + func
            self.send(cmd)
        except Exception as ex:
            raise

    def configure_cc_sink(self, current: float, current_limit: float, power_limit, set_output: bool = False) -> None:
        self.set_power_limit_negative(power_limit if power_limit < 0 else -power_limit)
        self.set_power_limit_positive(0)  # always fixed!
        self.set_current_limit_negative(current_limit if current_limit < 0 else -current_limit)
        self.set_current_limit_positive(0)  # always fixed!
        #self.set_voltage_limit_high(voltage_limit if voltage_limit < 0 else -voltage_limit)
        self.set_voltage_limit_low(1.0)  # always fixed!
        self.set_current(current if current < 0 else -current)
        #self.set_function("CURR")  # CC priority
        self.set_output_state(1 if set_output else 0)

    def configure_cc_supply(self, voltage: float, current_limit: float, power_limit, set_output: bool = False) -> None:
        self.set_power_limit_positive(abs(power_limit))
        self.set_power_limit_negative(0)  # always fixed!
        self.set_current_limit_positive(abs(current_limit))
        self.set_current_limit_negative(0)  # always fixed!
        self.set_voltage_limit_high(abs(voltage) * 1.05)
        self.set_voltage_limit_low(abs(voltage) * 0.90)
        self.set_voltage(abs(voltage))
        #self.set_function("VOLT") 
        self.set_output_state(1 if set_output else 0)


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class M3900(M3400):

    def __init__(self, resource_str: str, channel: int):
        """
        Initialize the object with VISA resource string (IP name).
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            resource_str (str): visa resource string
        """
        super().__init__(resource_str, channel)
        pass

    def __str__(self) -> str:
        return f"M3900 VISA device on {self.super().__str__()}"

    def __repr__(self) -> str:
        return f"M3900({self.resource_str}, {self.channel})"

    #----------------------------------------------------------------------------------------------
    # common function repeated as trampoline for TestStand only :-(

    def set_remote_control(self) -> None:
        super().set_remote_control()

    def send_raw_command(self, cmd: str) -> None:
        super().send_raw_command(cmd)

    def request_raw_query(self, cmd: str) -> str:
        return super().request_raw_query(cmd)

    def get_ADC_rounded(self, ndigits: int = 3) -> float:
        return super.get_ADC_rounded(ndigits=int(ndigits))

    def get_ADC(self) -> float:
        return super().get_ADC()

    def get_VDC_rounded(self, ndigits: int = 3) -> float:
        return super().get_VDC_rounded(ndigits=int(ndigits))

    def get_VDC(self) -> float:
        return super().get_VDC()

    def get_temp_rounded(self, ndigits: int = 3) -> float:
        return super().get_temp_rounded(ndigits=int(ndigits))

    def get_temp(self) -> float:
        return super().get_temp()

    def get_all_meas(self) -> list:
        return super().get_all_meas()

    def set_output_state(self, state: int) -> None:
        super().set_output_state(int(state))

    def get_output_state(self) -> int:
        return super().get_output_state()

    def set_current(self, curr: float) -> None:
        super().set_current(curr)

    def get_current_rounded(self, ndigits: int = 3) -> float:
        return super().get_current_rounded(ndigits=int(ndigits))

    def get_current(self) -> float:
        return super().get_current()

    def set_current_limit_positive(self, curr: float) -> None:
        super().set_current_limit_positive(curr)

    def get_current_limit_positive(self) -> float:
        return super().get_current_limit_positive()

    def set_current_limit_negative(self, curr: float) -> None:
        super().set_current_limit_negative(curr)

    def get_current_limit_negative(self) -> float:
        return super().get_current_limit_negative()

    def set_current_protection(self, curr: float) -> None:
        super().set_current_protection(curr)

    def get_current_protection(self) -> float:
        return super().get_current_protection()

    def set_current_under_protection(self, curr: float) -> None:
        super().set_current_under_protection(curr)

    def set_voltage(self, volt: float) -> None:
        super().set_voltage(volt)

    def get_voltage(self) -> float:
        return super().get_voltage()

    def set_voltage_limit_high(self, volt: float) -> None:
        super().set_voltage_limit_high(volt)

    def set_voltage_limit_low(self, volt: float) -> None:
        super().set_voltage_limit_low(volt)

    def set_voltage_protection(self, volt: float) -> None:
        super().set_voltage_protection(volt)

    def set_voltage_under_protection(self, volt: float) -> None:
        super().set_voltage_under_protection(volt)

    def set_power_limit_positive(self, power: float) -> None:
        super().set_power_limit_positive(power)

    def set_power_limit_negative(self, power: float) -> None:
        super().set_power_limit_negative(power)

    def set_function(self, func: str) -> None:
        super().set_function(func)

    #----------------------------------------------------------------------------------------------
    def set_resistance_mode(self, mode: int):
        """M3900 device only."""
        try:
            mode = int(mode)
            assert((mode == 1) or (mode == 0)), ValueError('Error, set_resistance_mode: only 1 or 0 allowed')
            cmd = "SINK:RES:STAT " + str(mode)
            self.send(cmd)
        except Exception as ex:
            raise

    def set_resistance(self, resist: int):
        """M3900 device only."""
        try:
            resist = int(resist)
            assert((resist > 0) and (resist < 2500)), ValueError('Error, set_resistance: only 0 ... 2500 Ohm allowed')
            cmd = "SINK:RES " + str(resist)
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:MODE <CPD>
    def set_battery_mode(self, mode: str) -> None:
        """
        This command is used to set the mode of battery test: charging or discharging.
        M3900 device only.

        Args:
            mode (str): CHAR|DISC
        """
        try:
            mode = str(mode)
            assert((mode == "CHAR") or (mode == "DISC")), ValueError('Error, set_battery_mode: only "CHAR" or "DISC" allowed')
            cmd = 'BATT:MODE ' + mode
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:MODE?
    def get_battery_mode(self) -> str:
        """
        This command is used to get the mode of battery test: charging or discharging.
        M3900 device only.

        Returns:
            str: CHAR|DISC
        """
        try:
            cmd = "BATT:MODE?"
            return str(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:CHARge:VOLTage <NRf+>
    def set_battery_charge_voltage(self, volt: float) -> None:
        """
        This command is used to set the battery charging voltage value.
        M3900 device only.

        Args:
            volt (float): voltage protection 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'BATT:CHAR:VOLT ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:CHARge:VOLTage? [MINimum|MAXimum|DEFault]
    def get_battery_charge_voltage(self) -> float:
        """
        This command is used to get the battery charging voltage value.
        M3900 device only.

        Returns:
            float: charge voltage
        """
        try:
            cmd = "BATT:CHAR:VOLT?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    def get_battery_charge_voltage_limit_low(self) -> float:
        """
        This command is used to get the battery charging voltage low limit.
        M3900 device only.

        Returns:
            float: charge voltage
        """
        try:
            cmd = "BATT:CHAR:VOLT? MIN"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    def get_battery_charge_voltage_limit_high(self) -> float:
        """
        This command is used to get the battery charging voltage high limit.
        M3900 device only.

        Returns:
            float: charge voltage
        """
        try:
            cmd = "BATT:CHAR:VOLT? MAX"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:CHARge:CURRent <NRf+>
    def set_battery_charge_current(self, curr: float) -> None:
        """
        This command is used to set the battery charging current value.
        M3900 device only.

        Args:
            curr (float): voltage protection 'XX.XX' Volts
        """
        try:
            param_str =  f"{curr:05.2f}"
            cmd = 'BATT:CHAR:CURR ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:CHARge:CURRent? [MINimum|MAXimum|DEFault]
    def get_battery_charge_current(self) -> float:
        """
        This command is used to get the battery charging current value.
        M3900 device only.

        Returns:
            float: charge current
        """
        try:
            cmd = "BATT:CHAR:CURR?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    def get_battery_charge_current_limit_low(self) -> float:
        """
        This command is used to get the battery charging current low limit.
        M3900 device only.

        Returns:
            float: charge current
        """
        try:
            cmd = "BATT:CHAR:CURR? MIN"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    def get_battery_charge_current_limit_high(self) -> float:
        """
        This command is used to get the battery charging current high limit.
        M3900 device only.

        Returns:
            float: charge current
        """
        try:
            cmd = "BATT:CHAR:CURR? MAX"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise


    def charge_mode_on(self, voltage_limit: float, curr: float) -> None:
        """
        Use to switch on battery charging mode. CC mode.
        M3900 device only.

        Args:
            voltage_limit (float): voltage limit value, Volts.
            curr (float): charging current value, Amps.
        """
        voltage_limit = float(voltage_limit)
        curr = float(curr)

        self.set_function("CURR")              # CC mode
        self.set_power_limit_positive(150.0)   # Watt
        self.set_current(curr=curr)
        self.set_voltage_limit_high(volt=voltage_limit)
        self.set_output_state(1)

    def charge_mode_off(self) -> None:
        """
        Use to switch off battery charging mode.
        M3900 device only.
        """
        self.set_output_state(0)


    def discharge_mode_on(self, voltage_limit: float, curr: float) -> None:
        """
        Use to switch on battery discharging mode. CC mode.
        M3900 device only.

        Args:
            voltage_limit (float): voltage limit value, Volts.
            curr (float): discharging current value, Amps.
        """
        voltage_limit = float(voltage_limit)
        curr = float(curr)

        self.set_function("CURR")               # CC mode
        self.set_power_limit_negative(-150.0)   # Watt
        self.set_resistance_mode(0)
        #self.set_resistance_mode(1)            # CR mode
        #resist = abs(int(voltage/curr))
        #self.set_resistance(resist)
        self.set_current(curr=curr)
        self.set_voltage_limit_low(volt=voltage_limit)
        self.set_output_state(1)

    def discharge_mode_off(self) -> None:
        self.set_output_state(0)

    # BATTery:DISCharge:VOLTage <NRf+>
    def set_battery_discharge_voltage(self, volt: float) -> None:
        """
        This command is used to set the battery discharging voltage value.
        M3900 device only.

        Args:
            volt (float): voltage 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'BATT:DISC:VOLT ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:DISCharge:VOLTage? [MINimum|MAXimum|DEFault]
    def get_battery_discharge_voltage(self) -> float:
        """
        This command is used to get the battery charging voltage value.
        M3900 device only.

        Returns:
            float: charge voltage
        """
        try:
            cmd = "BATT:DISC:VOLT?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:DISCharge:CURRent <NRf+>
    def set_battery_discharge_current(self, curr: float) -> None:
        """
        This command is used to set the battery discharging current value.
        M3900 device only.

        Args:
            curr (float): discharge current 'XX.XX' Amps
        """
        try:
            param_str =  f"{curr:05.2f}"
            cmd = 'BATT:DISC:CURR ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise

    # BATTery:DISCharge:CURRent? [MINimum|MAXimum|DEFault]
    def get_battery_discharge_current(self) -> float:
        """
        This command is used to get the battery discharging current value.
        M3900 device only.
        """
        try:
            cmd = "BATT:DISC:CURR?"
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:SHUT:VOLTage <NRf+>
    def set_battery_shut_voltage(self, volt: float) -> None:
        """
        This command is used to set the voltage value for the battery test cutoff.
        M3900 device only.

        Args:
            volt (float): cutoff voltage
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'BATT:SHUT:VOLT ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise
    # BATTery:SHUT:VOLTage? [MINimum|MAXimum|DEFault]
    def get_battery_shut_voltage(self) -> float:
        """
        This command is used to get the voltage value for the battery test cutoff.
        M3900 device only.
        """
        try:
            cmd = 'BATT:SHUT:VOLT?'
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:SHUT:CURRent <NRf+>
    def set_battery_shut_current(self, curr: float) -> None:
        """
        This command is used to set the current value for the battery test cutoff.
        M3900 device only.

        Args:
            curr (float): cutoff current
        """
        try:
            param_str =  f"{curr:05.2f}"
            cmd = 'BATT:SHUT:CURR ' + param_str
            self.send(cmd)
        except Exception as ex:
            raise
    # BATTery:SHUT:CURRent? [MINimum|MAXimum|DEFault]
    def get_battery_shut_current(self) -> float:
        """
        This command is used to get the current value for the battery test cutoff.
        M3900 device only.
        """
        try:
            cmd = 'BATT:SHUT:CURR?'
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    # BATTery:SHUT:TIME <NRf+>
    def set_battery_shut_time(self, time: int) -> None:
        """
        This command is used to set the time value for the battery test cutoff.
        M3900 device only.

        Args:
            time (int): cutoff time, sec
        """
        try:
            time =  int(time)
            cmd = 'BATT:SHUT:TIME ' + str(time)
            self.send(cmd)
        except Exception as ex:
            raise
    # BATTery:SHUT:TIME? [MINimum|MAXimum|DEFault]
    def get_battery_shut_time(self) -> float:
        """
        This command is used to get the time value for the battery test cutoff.
        M3900 device only.
        """
        try:
            cmd = 'BATT:SHUT:TIME?'
            return float(self.request(cmd, 2000))
        except Exception as ex:
            raise

    def wake_up_mode_on(self, voltage_limit: float, curr_limit: float) -> None:
        """
        Use to wake up bq40z50 or another bq chip. CV mode.
        M3900 device only.

        Args:
            voltage (float): voltage value, Volts.
            curr_limit (float): current limit, Amps
        """
        voltage_limit = float(voltage_limit)
        curr_limit = float(curr_limit)

        self.set_function("CURR")              # CC mode
        self.set_power_limit_positive(150.0)   # Watt
        self.set_current(curr=curr_limit)
        self.set_voltage_limit_high(volt=voltage_limit)
        self.set_output_state(1)

    def wake_up_mode_off(self) -> None:
        """
        Use to wake up bq40z50 or another bq chip. CV mode.
        M3900 device only.
        """
        self.set_output_state(0)


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