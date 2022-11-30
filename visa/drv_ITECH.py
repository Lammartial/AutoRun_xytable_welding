import pyvisa
from pyvisa import ResourceManager, constants



#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

#--------------------------------------------------------------------------------------------------
class ITECH_DEV(object):
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

    #def find(self, searchString):
    #    print('Find with search string \'%s\':' % searchString)
    #    devices = self.rm.list_resources(searchString)
    #    if len(devices) > 0:
    #        for device in devices:
    #            print('\t%s' % device)
    #    else:
    #        print('... didn\'t find anything!')
    #    self.rm.close()

    def connect_by_name(self, NAME_STR):
        """ Creates a connection (session) with the device by Name """
        try:
            self.session = self.rm.open_resource(NAME_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
                #self.session.write_termination = '\n'
        except pyvisa.Error as ex:
            return ex
        except NameError as ex:
            return ex
        
    def connect_by_IP(self, IP_STR):
        """ Creates a connection (session) with the device by IP """
        try:
            self.session = self.rm.open_resource(IP_STR)            
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
                #self.session.write_termination = '\n'
        except pyvisa.Error as ex:
            return ex
        except NameError as ex:
            return ex

    def set_remote_control(self):
        """ This command clears the system status register. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "SYST:REM"
                self.session.timeout = 2000
                self.session.write(cmd)
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def set_raw_command(self, cmd):
        """ Sets raw SCPI command and returns error.

            Parameters
            ----------
            cmd : str, SCPI command """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                #if (cmd is str):
                    self.session.write(cmd)
                #    return result
                #else:
                #    raise ValueError('Error, set_raw_command: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def set_raw_query(self, cmd):
        """ Sets raw SCPI query and returns the result or error.

            Parameters
            ----------
            cmd : str, SCPI command """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def get_ADC(self):
        """ This command queries the present current measurement. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "MEAS:CURR?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    def get_VDC(self):
        """ This command queries the present measured voltage. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "MEAS:VOLT?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    def get_temp(self):
        """ This command queries the measured UUT temperature. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "MEAS:UUT:TEMP?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                return float(result)
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    def get_all_meas(self):
        """ This command queries the present voltage measurement, current
            measurement and power measurement """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "MEAS?"
                self.session.timeout = 2000
                result = self.session.query(cmd)
                # 5 results - string "###, ###, ###, ###, ###"
                lst = str(result).split(',')        
                return lst
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    def set_output_state(self, state):
        """ This command sets the output state of the power supply.

            Parameters
            ----------
            state: int 1|0 or string 'ON'|'OFF' """
        # trick to use function in NI Teststand
        state = int(state)
        # Last operation completed successfully -> Connection is OK\V-Prod\Battery-PCBA-Test\src\branch\master\visa\examples\base.py
        if (self.rm.last_status == 0):    
            try:
                if (state == 0) or (state == 1) or ((state == 'ON') or (state == 'OFF')):
                    #cmd = 'OUTP {state}'
                    self.session.timeout = 2000
                    self.session.write(f'OUTP {state}')
                else:
                    raise ValueError('Error, set_output_state: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex 

    def get_output_state(self):
        """ This command sets the output state of the power supply """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "OUTP?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex 


    def set_sense_state(self, state):
        """ This command enables or disables the sense function. 

            Parameters
            ----------
            state: int 1|0 or string 'ON'|'OFF' """
        # trick to use function in NI Teststand
        state = int(state)        
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            
            try:
                if (state == 0) or (state == 1) or ((state == 'ON') or (state == 'OFF')):
                    self.session.timeout = 2000
                    self.session.write(f'SENS {state}')
                else:
                    raise ValueError('Error, set_output_state: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex 

    def get_sense_state(self):
        """ This command sets the output state of the power supply """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "SENS?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex 
   
    def get_output_reverse_state(self):
        """ This command is used to query the connection of output terminals. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "OUTP:REV?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def set_current(self, curr):
        """ This command sets the current value of the power supply. 
            The query form of this command gets the set current value of the power supply.

            Parameters
            ----------
            curr: string 'MIN', 'MAX' or 'X.XXX' Amp """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'CURR {curr}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude] <NRf+>
    def get_current(self):
        """ This command gets the current value of the power supply. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    def set_current_limit_positive(self, curr):
        """ This command sets the positive current limit value of the power supply. 

            Parameters
            ----------
            curr: string 'MIN', 'MAX' or 'XX.XX' Amps """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'CURR:LIM:POS {curr}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
    #[SOURce:]CURRent[:LEVel]:LIMit:POSitive <NRf+>
    def get_current_limit_positive(self):
        """ This command gets the positive current limit value of the power supply. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:LIM:POS?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex   

    #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    def set_current_limit_negative(self, curr):
        """ This command sets the negative current limit value of the power supply.

            Parameters
            ----------
            curr: string 'MIN', 'MAX' or '-XX.XX' Amps """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'CURR:LIM:NEG {curr}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:LEVel]:LIMit:NEGative <NRf+>
    def get_current_limit_negative(self):
        """ This command gets the negative current limit value of the power supply. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:LIM:NEG?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>
    def set_current_protection(self, curr):
        """ This command sets the over current limit of the power supply. 

            Parameters
            ----------
            curr: string 'MIN', 'MAX' or 'XX.XXX' Amps """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'CURR:PROT {curr}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent[:OVER]:PROTection[:LEVel] <NRf+>   
    def get_current_protection(self):
        """ This command gets the over current limit of the power supply. """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = "CURR:PROT?"
                self.session.timeout = 2000
                result = self.session.query(cmd)    
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]CURRent:UNDer:PROTection[:LEVel] <NRf+>
    def set_current_under_protection(self, curr):
        """ This command sets the under current limit of the power supply.

            Parameters
            ----------
            curr: string 'MIN', 'MAX' or 'XX.XXX' Amps """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'CURR:UND:PROT {curr}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude] <NRf+>   
    def set_voltage(self, volt):
        """ This command sets the voltage value of the power supply. The query form of
            this command gets the set voltage value of the power supply. 

            Parameters
            ----------
            volt: string 'MIN', 'MAX' or 'XX.XX' Volts """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'VOLT {volt}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]VOLTage[:LEVel]:LIMit[:HIGH] <NRf+>
    def set_voltage_limit(self, volt):
        """ This command sets voltage upper limit under CC priority mode. 

            Parameters
            ----------
            volt: string 'MIN', 'MAX' or 'XX.XX' Volts """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'VOLT:LIM {volt}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]VOLTage[:LEVel]:LIMit:LOW <NRf+>
    def set_voltage_limit_low(self, volt):
        """ This command sets voltage lower limit under CC priority mode. 

            Parameters
            ----------
            volt: string 'MIN', 'MAX' or 'XX.XX' Volts"""
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'VOLT:LIM:LOW {volt}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]VOLTage[:OVER]:PROTection[:LEVel] <NRf+>   
    def set_voltage_protection(self, volt):
        """ This command sets the over voltage limit of the power supply. 

            Parameters
            ----------
            volt: string 'MIN', 'MAX' or 'XX.XX' Volts """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'VOLT:PROT {volt}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    #[SOURce:]VOLTage:UNDer:PROTection[:LEVel] <NRf+>   
    def set_voltage_under_protection(self, volt):
        """ This command sets the under voltage limit of the power supply. 

            Parameters
            ----------
            volt: string 'MIN', 'MAX' or 'XX.XX' Volts """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                cmd = f'VOLT:UND:PROT {volt}'
                self.session.write(cmd)    
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex   

    def disconnect(self):
        """ Closes the connection (session) and the device """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.close()
                self.rm.close()
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex


#--------------------------------------------------------------------------------------------------