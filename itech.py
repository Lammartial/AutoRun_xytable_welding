from eth2serial.base_visa import Eth2SerialVisaDevice
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
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
class M3400_DEV(Eth2SerialVisaDevice):
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

    def __init__(self, name_ip: str, channel: int):
        """
        Initialize the object with visa IP name.
        Example "TCPIP0::192.168.1.101::inst0::INSTR"

        Args:
            host (str): visa IP name
        """
        super().__init__(name_ip, channel)
        pass    

    def set_remote_control(self) -> None:
        """
        This command clears the system status register. 
        IT M3400 and M3900 devices
        """  
        cmd = "SYST:REM"
        self.send(cmd)             

    def set_raw_command(self, cmd: str) -> None:
        """
        Sets raw SCPI command and returns error.

        Args:
            cmd (str): SCPI command
        """
        self.send(str(cmd))

    def set_raw_query(self, cmd: str) -> str:
        """
        Sets raw SCPI query and returns the result or error.

        Args:
            cmd (str): SCPI command

        Returns:
            str: response
        """
        return self.request(str(cmd))

    def get_ADC(self) -> float:
        """
        This command queries the present current measurement. 
        IT M3400 and M3900 devices

        Returns:
            float: ADC
        """
        cmd = "FETC:CURR?"
        return float(self.request(cmd, 2000))

    def get_VDC(self) -> float:
        """
        This command queries the present measured voltage. 
        IT M3400 and M3900 devices

        Returns:
            float: VDC
        """
        cmd = "FETC:VOLT?"
        return float(self.request(cmd, 2000))

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
            _log.exception(ex)
            raise

    def set_output_state(self, state: int) -> None:
        """
        This command sets the output state of the power supply.
        IT M3400 and M3900 devices.

        Args:
            state (int):  1 - On, 0 - Off 

        Raises:
            ValueError: invalid parameters
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
            _log.exception(ex)
            raise

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
            return float(self.request(cmd, 2000))    
        except Exception as ex:
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
            raise

    #[SOURce:]VOLTage[:LEVel]:LIMit[:HIGH] <NRf+>
    def set_voltage_limit(self, volt: float) -> None:
        """
        This command sets voltage upper limit under CC priority mode. 
        IT M3400 and M3900 devices.

        Args:
            volt (float): voltage limit 'XX.XX' Volts
        """
        try:
            param_str =  f"{volt:05.2f}"
            cmd = 'VOLT:LIM ' + param_str 
            self.session.write(cmd)    
        except Exception as ex:
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
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
            _log.exception(ex)
            raise   

    #def disconnect(self):
    #    """
    #    Closes the connection (session) and the device.
    #    """
    #    try:
    #        self.session.close()
    #        self.rm.close()
    #    except Exception as ex:
    #        _log.exception(ex)
    #        raise

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    M3412_IP_STR = "TCPIP0::192.168.1.101::inst0::INSTR"

    # 1. Create an instance of ITECH_DEV class
    it_m3412_1 = M3400_DEV(M3412_IP_STR, 1)
    it_m3412_2 = M3400_DEV(M3412_IP_STR, 2)
    it_m3412_3 = M3400_DEV(M3412_IP_STR, 3)
    it_m3412_4 = M3400_DEV(M3412_IP_STR, 4)
    it_m3412_5 = M3400_DEV(M3412_IP_STR, 5)
    it_m3412_6 = M3400_DEV(M3412_IP_STR, 6)

    # 2. IMPORTANT! Set remote control mode.
    it_m3412_1.set_remote_control()
    it_m3412_2.set_remote_control()                  

    # 3. Do some stuff

    print(it_m3412_1.get_ADC())
    print(it_m3412_2.get_ADC())

    print(it_m3412_1.get_VDC())
    print(it_m3412_2.get_VDC())

    # Get current
    #print(it_m3412.get_ADC())

    # Get voltage
    #print(it_m3412.get_VDC())

    # Doesn't work. Get temperature
    #print(it_m3412.get_temp())

    # Get Current, Voltage, Temperature, ...
    #print(it_m3412.get_all_meas())

    # Set SENSE state
    #it_m3412.set_sense_state(0)                        # No return value

    # Get SENSE state
    #print(it_m3412.get_sense_state())

    #Doesn't work. Get output reverse state
    #print(it_m3412.get_output_reverse_state())

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    #it_m3412.set_current(1.0005)                      # No return value

    # Get current.
    #print(it_m3412.get_current())

    # Set current limit positive. curr - string 'MIN', 'MAX' or'X.XX' Amp
    #it_m3412.set_current_limit_positive(curr = 5.000)       # No return value

    # Get current limit positive
    #print(it_m3412.get_current_limit_positive())

    # Set current limit negative. curr - string 'MIN', 'MAX' or'X.XX' Amp
    #it_m3412.set_current_limit_negative(curr = -5.000)   #(-02.000)       # No return value

    # Get current limit negative
    #print(it_m3412.get_current_limit_negative())

    # Set current protection
    #it_m3412.set_current_protection(10.000)           # No return value

    # Get current protection
    #print(it_m3412.get_current_protection())

    # Set under-current limit
    #it_m3412.set_current_under_protection(1.000)      # No return value

    # Set voltage value
    #it_m3412.set_voltage(10.00)                       # No return value

    # Set voltage upper limit
    #it_m3412.set_voltage_limit(20.00)                 # No return value

    # Set voltage lower limit under CC priority mode
    #it_m3412.set_voltage_limit_low(1.00)              # No return value

    # Set over voltage limit (MAX = 61.00)
    #it_m3412.set_voltage_protection(60.00)            # No return value

    # Set voltage under-protection
    #it_m3412.set_voltage_under_protection(10.00)      # No return value

    # 4. ERRORS 

    # Check errors
    #print(it_m3412.set_raw_query('SYST:ERR?'))

    # Check Standard Event Status Register (SESR)
    #print(it_m3412.set_raw_query('*ESR?'))

    # 5. Close connection
    #it_m3412.disconnect()

    # Set voltage value
    it_m3412_1.set_voltage(1.00)                       # No return value
    it_m3412_2.set_voltage(2.00)                       # No return value
    it_m3412_3.set_voltage(3.00)                       # No return value
    it_m3412_4.set_voltage(4.00)                       # No return value
    it_m3412_5.set_voltage(5.00)                       # No return value
    it_m3412_6.set_voltage(6.00)                       # No return value

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    it_m3412_1.set_current(0.100)                      # No return value
    it_m3412_2.set_current(0.100)                      # No return value
    it_m3412_3.set_current(0.100)                      # No return value
    it_m3412_4.set_current(0.100)                      # No return value
    it_m3412_5.set_current(0.100)                      # No return value
    it_m3412_6.set_current(0.100)                      # No return value

    # Set OUTPUT ON/OFF
    it_m3412_1.set_output_state(1)                    # No return value
    it_m3412_2.set_output_state(1)                    # No return value
    it_m3412_3.set_output_state(1)                    # No return value
    it_m3412_4.set_output_state(1)                    # No return value
    it_m3412_5.set_output_state(1)                    # No return value
    it_m3412_6.set_output_state(1)                    # No return value

    sleep(1)

    # Get OUTPUT state 
    print(it_m3412_1.get_output_state())
    print(it_m3412_2.get_output_state())
    print(it_m3412_3.get_output_state())
    print(it_m3412_4.get_output_state())
    print(it_m3412_5.get_output_state())
    print(it_m3412_6.get_output_state())

    print(it_m3412_1.get_all_meas())
    print(it_m3412_2.get_all_meas())
    print(it_m3412_3.get_all_meas())
    print(it_m3412_4.get_all_meas())
    print(it_m3412_5.get_all_meas())
    print(it_m3412_6.get_all_meas())

    # Set OUTPUT ON/OFF
    it_m3412_1.set_output_state(0)                    # No return value
    it_m3412_2.set_output_state(0)                    # No return value
    it_m3412_3.set_output_state(0)                    # No return value
    it_m3412_4.set_output_state(0)                    # No return value
    it_m3412_5.set_output_state(0)                    # No return value
    it_m3412_6.set_output_state(0)                    # No return value
    
    print("DONE.")
    
# END OF FILE