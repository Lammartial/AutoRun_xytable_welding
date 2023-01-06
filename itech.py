from pyvisa import ResourceManager
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
class M3400_DEV(object):
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

    def __init__(self) -> None:
        self.rm = ResourceManager()          # auto decision for backend
        pass    

    def connect_by_name(self, NAME_STR: str) -> None:
        """
        Creates a connection (session) with the device by Name.

        Args:
            NAME_STR (str): device name
        """
        try:
            self.session = self.rm.open_resource(NAME_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
                #self.session.write_termination = '\n'
        except Exception as ex:
            _log.exception(ex)
            raise
    def connect_by_IP(self, IP_STR: str) -> None:
        """
        Creates a connection (session) with the device by IP

        Args:
            IP_STR (str): device IP address
        """
        
        try:
            self.session = self.rm.open_resource(IP_STR)            
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
                #self.session.write_termination = '\n'
        except Exception as ex:
            _log.exception(ex)
            raise

    def set_remote_control(self) -> None:
        """
        This command clears the system status register. 
        IT M3400 and M3900 devices
        """  
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "SYST:REM"
                self.session.timeout = 2000
                self.session.write(cmd)
            except Exception as ex:
                _log.exception(ex)
                raise

    def set_raw_command(self, cmd: str) -> None:
        """
        Sets raw SCPI command and returns error.

        Args:
            cmd (str): SCPI command
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                #if (cmd is str):
                    self.session.write(str(cmd))
                #    return result
                #else:
                #    raise ValueError('Error, set_raw_command: invalid parameters')
            except Exception as ex:
                _log.exception(ex)
                raise

    def set_raw_query(self, cmd: str) -> str:
        """
        Sets raw SCPI query and returns the result or error.

        Args:
            cmd (str): SCPI command

        Returns:
            str: response
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return result
            except Exception as ex:
                _log.exception(ex)
                raise

    def get_ADC(self) -> float:
        """
        This command queries the present current measurement. 
        IT M3400 and M3900 devices

        Returns:
            float: ADC
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "FETC:CURR?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except Exception as ex:
                _log.exception(ex)
                raise

    def get_VDC(self) -> float:
        """
        This command queries the present measured voltage. 
        IT M3400 and M3900 devices

        Returns:
            float: VDC
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "FETC:VOLT?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except Exception as ex:
                _log.exception(ex)
                raise

    def get_temp(self) -> float:
        """
        This command queries the measured UUT temperature. 
        IT M3400 devices

        Returns:
            float: temperature
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "FETC:UUT:TEMP?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except Exception as ex:
                _log.exception(ex)
                raise

    def get_all_meas(self) -> list:
        """
        This command queries the present voltage measurement, current
        measurement and power measurement. 
        IT M3400 and M3900 devices

        Returns:
            list[5], float:  voltage, current, power, amp-hour, watt-hour
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "FETC?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
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
        # Last operation completed successfully -> Connection is OK\V-Prod\Battery-PCBA-Test\src\branch\master\visa\examples\base.py
        if (self.rm.last_status == 0):    
            assert ((state == 0) or (state == 1)), ValueError('Error, set_output_state: only 1 or 0 allowed')
            try:
                #cmd = 'OUTP {state}'
                self.session.timeout = 2000
                self.session.write(f'OUTP {state}')
            except Exception as ex:
                _log.exception(ex)
                raise 

    def get_output_state(self) -> int:
        """
        This command sets the output state of the power supply.
        IT M3400 and M3900 devices.

        Returns:
            int: state, 1 - On, 0 - Off
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "OUTP?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return int(result)
            except Exception as ex:
                _log.exception(ex)
                raise 

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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert((state == 0) or (state == 1)), ValueError('Error, set_output_state: only 1 or 0 allowed')
            try:
                self.session.timeout = 2000
                self.session.write(f'SENS {state}')
            except Exception as ex:
                _log.exception(ex)
                raise 

    def get_sense_state(self) -> int:
        """
        This command sets the output state of the power supply 
        IT M3400 devices.

        Returns:
            int: sense, 1 - On, 0 - Off
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "SENS?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return int(result)
            except Exception as ex:
                _log.exception(ex)
                raise 
   
    def get_output_reverse_state(self) -> int:
        """
        This command is used to query the connection of output terminals. 
        IT M3400 devices

        Returns:
            int: state, 1 - On, 0 - Off
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "OUTP:REV?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return int(result)
            except Exception as ex:
                _log.exception(ex)
                raise

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_current(self, curr: float) -> None:
        """
        This command sets the current value of the power supply. 
        The query form of this command gets the set current value of the power supply.
        IT M3400 and M3900 devices

        Args:
            curr (float): current 'XX.XXX' Amp
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{curr:06.3f}"
                #cmd = f'CURR {curr}'
                cmd = 'CURR ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except Exception as ex:
                _log.exception(ex)
                raise

    #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    def set_current_limit_positive(self, curr: float) -> None:
        """
        This command sets the positive current limit value of the power supply. 
        IT M3400 and M3900 devices.

        Args:
            curr (float): current limit 'XX.XXX' Amps
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{curr:06.3f}"
                #cmd = f'CURR:LIM:POS {curr}'
                cmd = 'CURR:LIM:POS ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:LIM:POS?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return float(result)
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{curr:07.3f}"
                #cmd = f'CURR:LIM:NEG {curr}'
                cmd = 'CURR:LIM:NEG ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:LIM:NEG?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return float(result)
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{curr:06.3f}"
                #cmd = f'CURR:PROT {curr}'
                cmd = 'CURR:PROT ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:PROT?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return float(result)
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{curr:06.3f}"
                #cmd = f'CURR:UND:PROT {curr}'
                cmd = 'CURR:UND:PROT ' + param_str
                self.session.write(cmd)    
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

        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{volt:05.2f}"
                #cmd = f'VOLT {volt}'
                cmd = 'VOLT ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = 'VOLT?'
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return float(result)    
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

        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{volt:05.2f}"
                #cmd = f'VOLT:LIM {volt}'
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{volt:05.2f}"
                #cmd = f'VOLT:LIM:LOW {volt}'
                cmd = 'VOLT:LIM:LOW ' + param_str
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{volt:05.2f}"
                #cmd = f'VOLT:PROT {volt}'
                cmd = 'VOLT:PROT ' + param_str 
                self.session.write(cmd)    
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
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                param_str =  f"{volt:05.2f}"
                #cmd = f'VOLT:UND:PROT {volt}'
                cmd = 'VOLT:UND:PROT ' + param_str
                self.session.write(cmd)    
            except Exception as ex:
                _log.exception(ex)
                raise   

    def disconnect(self):
        """
        Closes the connection (session) and the device.
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.close()
                self.rm.close()
            except Exception as ex:
                _log.exception(ex)
                raise

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    #M3412_IP_STR = "TCPIP0::169.254.208.73::inst0::INSTR" 
    M3412_IP_STR = "TCPIP0::192.168.1.101::inst0::INSTR" 
    #M3412_NAME_STR = "TCPIP0::K-DAQ970A-17481.local::inst0::INSTR"

    # 1. Create an instance of ITECH_DEV class
    it_m3412 = M3400_DEV()

    # 2. Connect to the device
    #it_m3412.connect_by_name(DAQ970A_NAME_STR)
    # or
    print(it_m3412.connect_by_IP(M3412_IP_STR))

    # 3. IMPORTANT! Set remote control mode.
    it_m3412.set_remote_control()                   # No return value

    # 4. Do some stuff

    # Set OUTPUT ON/OFF
    it_m3412.set_output_state(1)                    # No return value

    sleep(1)

    # Get OUTPUT state 
    print(it_m3412.get_output_state())

    # Get current
    print(it_m3412.get_ADC())

    # Get voltage
    print(it_m3412.get_VDC())

    # Doesn't work. Get temperature
    #print(it_m3412.get_temp())

    # Get Current, Voltage, Temperature, ...
    print(it_m3412.get_all_meas())

    # Set SENSE state
    it_m3412.set_sense_state(0)                        # No return value

    # Get SENSE state
    print(it_m3412.get_sense_state())

    #Doesn't work. Get output reverse state
    #print(it_m3412.get_output_reverse_state())

    # Set current. curr - string 'MIN', 'MAX' or'XX.XXX' Amp
    it_m3412.set_current(1.0005)                      # No return value

    # Get current.
    print(it_m3412.get_current())

    # Set current limit positive. curr - string 'MIN', 'MAX' or'X.XX' Amp
    it_m3412.set_current_limit_positive(curr = 5.000)       # No return value

    # Get current limit positive
    print(it_m3412.get_current_limit_positive())

    # Set current limit negative. curr - string 'MIN', 'MAX' or'X.XX' Amp
    it_m3412.set_current_limit_negative(curr = -5.000)   #(-02.000)       # No return value

    # Get current limit negative
    print(it_m3412.get_current_limit_negative())

    # Set current protection
    it_m3412.set_current_protection(10.000)           # No return value

    # Get current protection
    #print(it_m3412.get_current_protection())

    # Set under-current limit
    it_m3412.set_current_under_protection(1.000)      # No return value

    # Set voltage value
    it_m3412.set_voltage(10.00)                       # No return value

    # Set voltage upper limit
    it_m3412.set_voltage_limit(20.00)                 # No return value

    # Set voltage lower limit under CC priority mode
    it_m3412.set_voltage_limit_low(1.00)              # No return value

    # Set over voltage limit (MAX = 61.00)
    it_m3412.set_voltage_protection(60.00)            # No return value

    # Set voltage under-protection
    it_m3412.set_voltage_under_protection(10.00)      # No return value

    # 4. ERRORS 

    # Check errors
    #print(it_m3412.set_raw_query('SYST:ERR?'))

    # Check Standard Event Status Register (SESR)
    #print(it_m3412.set_raw_query('*ESR?'))

    # 5. Close connection
    it_m3412.disconnect()
    
    print("DONE.")
    
# END OF FILE