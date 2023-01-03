
import pyvisa
from pyvisa import ResourceManager, constants

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

#--------------------------------------------------------------------------------------------------
class DAQ970A(object):
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
    def __init__(self) -> None:
        self.rm = ResourceManager()          # auto decision for backend
        pass    

    def connect_by_name(self, DAQ970A_NAME_STR):
        """ Creates a connection (session) with the device by Name """
        try:
            self.session = self.rm.open_resource(DAQ970A_NAME_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
        except pyvisa.Error as ex:
            return ex
        except NameError as ex:
            return ex
        
    def connect_by_IP(self, DAQ970A_IP_STR):
        """ Creates a connection (session) with the device by IP """
        try:
            self.session = self.rm.open_resource(DAQ970A_IP_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
        except pyvisa.Error as ex:
            return ex
        except NameError as ex:
            return ex

    def selftest(self):
        """ Returns device self-test results, takes ~ 2 sec """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 5000
                result = self.session.query(f"*TST?")
                self.session.timeout = 2000 
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:     
                return ex

    def selftest_all(self):
        """ Returns device full self-test results, takes ~5 sec """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 10000 
                result = self.session.query(f"TEST:ALL?")
                self.session.timeout = 2000 
                return result
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex

    def set_raw_command(self, cmd):
        """ Sets raw SCPI command and returns the result or error

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

    def get_resistance(self, slot, channel):
        """ Returns resistance measurement 
        
        Parameters
        ----------
        slot : int, slot number (1, 2, 3)
        channel : int, channel number (1 ... 20) """

        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (1 <= channel <= 20):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    cmd = "MEAS:RES? AUTO,DEF,(@" + slot_str + channel_str + ")"
                    self.session.timeout = 5000
                    result = self.session.query(cmd)
                    self.session.timeout = 2000
                    return float(result)
                else:
                    raise ValueError('Error, get_resistance: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def get_4w_resistance(self, slot, channel):
        """ Returns 4-wire resistance measurement 
        
        Parameters
        ----------
        slot : int, slot number (1, 2, 3)
        channel : int, channel number (1 ... 10) """

        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (1 <= channel <= 10):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    cmd = "MEAS:FRES? AUTO,DEF,(@" + slot_str + channel_str + ")"
                    self.session.timeout = 5000
                    result = self.session.query(cmd)
                    self.session.timeout = 2000
                    return float(result)
                else:
                    raise ValueError('Error, get_4w_resistance: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def get_VDC(self, slot, channel):
        """ Returns DC voltage measurement 
        
        Parameters
        ----------
        slot : int, slot number (1, 2, 3)
        channel : int, channel number (1 ... 20) """

        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (1 <= channel <= 20):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    cmd = "MEAS:VOLT:DC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                    self.session.timeout = 5000
                    result = self.session.query(cmd)
                    self.session.timeout = 2000
                    return float(result)
                else:
                    raise ValueError('Error, get_VDC: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex

    def get_VAC(self, slot, channel):
        """ Returns AC voltage measurement 
        
        Parameters
        ----------
        slot : int, slot number (1, 2, 3)
        channel : int, channel number (1 ... 20) """

        # trick to use function code in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (1 <= channel <= 20):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    cmd = "MEAS:VOLT:AC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                    self.session.timeout = 5000
                    result = self.session.query(cmd)
                    self.session.timeout = 2000
                    return float(result)
                else:
                    raise ValueError('Error, get_VAC: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex      

    def get_ADC(self, slot, channel):
        """ Returns DC current measurement 
        
        Parameters
        ----------
        slot : int, slot number (1, 2, 3)
        channel : int, channel number (21 or 22) """

        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (21 <= channel <= 22):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    cmd = "MEAS:CURR:DC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                    self.session.timeout = 5000
                    result = self.session.query(cmd)
                    self.session.timeout = 2000
                    return float(result)
                else:
                    raise ValueError('Error, get_ADC: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
                return ex  

    def get_temp(self, slot, channel, tran_type, rtd_resist, fth_type, tc_type):
        """ Returns temperature measurement 
        
        Parameters
        ----------
        slot       : int, slot number (1, 2, 3)
        channel      : int, channel number (1 ... 20) 
        tran_type  : str, transducer type (TC, FRTD, RTD, FTH, THER or DEF(TCouple))
        rtd_resist : int, FRTD|RTD trancduser resistance (100 or 1000 Ohm), otherwise = 0
        fth_type   : int, FTH|THER type (2252, 5000, 10000), otherwise = 0
        tc_type    : str, TCouple type (B, E, J, K, N, R, S, or T), otherwise = 'empty string' """

        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        rtd_resist = int(rtd_resist)
        fth_type = int(fth_type)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                if (1 <= slot <= 3) and (1 <= channel <= 20):
                    slot_str = str(slot)
                    channel_str = str(channel).zfill(2)
                    match tran_type:
                        case 'TC' | 'DEF':
                            if (tc_type in ["B", "E", "J", "K", "N", "R", "S", "T"]):
                                cmd = "MEAS:TEMP:TC?" + " " + tc_type + ",(@" + slot_str + channel_str + ")"
                                self.session.timeout = 5000
                                result = self.session.query(cmd)
                                self.session.timeout = 2000
                                return float(result)
                            else:
                                raise ValueError('Error, get_temp: invalid parameters')
                        case 'FTH' | 'THER':
                            if (fth_type == 2252) or (fth_type == 5000) or (fth_type == 10000):
                                cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(fth_type) + ",(@" + slot_str + channel_str + ")"
                                self.session.timeout = 5000
                                result = self.session.query(cmd)
                                self.session.timeout = 2000
                                return float(result)
                            else:
                                raise ValueError('Error, get_temp: invalid parameters')
                        case 'FRTD' | 'RTD':
                            if (rtd_resist == 100) or (rtd_resist == 1000):
                                cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(rtd_resist) + ",(@" + slot_str + channel_str + ")"
                                self.session.timeout = 5000
                                result = self.session.query(cmd)
                                self.session.timeout = 2000
                                return float(result)
                            else:
                                raise ValueError('Error, get_temp: invalid parameters')
                        case _:
                            raise ValueError('Error, get_temp: invalid parameters')
                else:
                    raise ValueError('Error, get_temp: invalid parameters')
            except pyvisa.Error as ex:
                return ex
            except NameError as ex:
                return ex
            except ValueError as ex:
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