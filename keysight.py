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

    # This could be a way to avoid try ... except in each function
    #def e(methodtoRun, *args):
    #    try:
    #        methodtoRun(*args)    # pass arguments along
    #    except Exception as inst:
    #        print(type(inst))    # the exception instance
    #        print(inst.args)     # arguments stored in .args
    #        print(inst)          # __str__ allows args to be printed directly,

    def __init__(self) -> None:
        self.rm = ResourceManager()          # auto decision for backend
        pass    

    def connect_by_name(self, DAQ970A_NAME_STR: str):
        """
        Creates a connection (session) with the device by Name

        Args:
            DAQ970A_NAME_STR (str): device name

        Returns:
            _type_: exception
        """
        try:
            self.session = self.rm.open_resource(DAQ970A_NAME_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
        except Exception as ex:
            _log.error(ex)
            return ex
  
    def connect_by_IP(self, DAQ970A_IP_STR: str):
        """
        Creates a connection (session) with the device by IP.

        Args:
            DAQ970A_IP_STR (str): device IP address

        Returns:
            _type_: exception
        """
        try:
            self.session = self.rm.open_resource(DAQ970A_IP_STR)
            # For Serial and TCP/IP socket connections enable the read Termination Character, or read's will timeout
            if self.session.resource_name.startswith('ASRL') or self.session.resource_name.endswith('SOCKET'):
                self.session.read_termination = '\n'
        except Exception as ex:
            _log.error(ex)
            return ex

    def selftest(self):
        """Returns device self-test results, takes ~ 2 sec.

        Returns:
            _type_: exception
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 5000
                result = self.session.query(f"*TST?")
                self.session.timeout = 2000 
                return result
            except Exception as ex:
                _log.error(ex)
                return ex

    def selftest_all(self):
        """
        Returns device full self-test results, takes ~5 sec

        Returns:
            _type_: exception
        """   
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.timeout = 10000 
                result = self.session.query(f"TEST:ALL?")
                self.session.timeout = 2000 
                return result
            except Exception as ex:
                _log.error(ex)
                return ex

    def set_raw_command(self, cmd: str):
        """
        Sets raw SCPI command and returns the result or error.

        Args:
            cmd (str): SCPI command 

        Returns:
            _type_: exception
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                #if (cmd is str):
                    self.session.write(cmd)
                #    return result
                #else:
                #    raise ValueError('Error, set_raw_command: invalid parameters')
            except Exception as ex:
                _log.error(ex)
                return ex

    def get_resistance(self, slot: int, channel: int):
        """
        Returns resistance measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 20)

        Raises:
            ValueError: invalid argument

        Returns:
            _type_: resistance(float) or exception
        """
        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
            try:
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                cmd = "MEAS:RES? AUTO,DEF,(@" + slot_str + channel_str + ")"
                self.session.timeout = 5000
                result = self.session.query(cmd)
                self.session.timeout = 2000
                return float(result)
            except Exception as ex:
                _log.error(ex)
                return ex

    def get_4w_resistance(self, slot: int, channel: int):
        """
        Returns 4-wire resistance measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 10)

        Raises:
            ValueError: invalid argument

        Returns:
            _type_: resistance(float) or exception
        """
        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel >= 1) and (channel <= 10)), ValueError('Invalid channel. Allowed range is 1 .. 10.')
            try:
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                cmd = "MEAS:FRES? AUTO,DEF,(@" + slot_str + channel_str + ")"
                self.session.timeout = 5000
                result = self.session.query(cmd)
                self.session.timeout = 2000
                return float(result)
            except Exception as ex:
                _log.error(ex)
                return ex

    def get_VDC(self, slot: int, channel: int):
        """
        Returns DC voltage measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 20)

        Raises:
            ValueError: invalid argument

        Returns:
            _type_: VDC (float) or exception
        """
        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
            try:
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                cmd = "MEAS:VOLT:DC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                self.session.timeout = 5000
                result = self.session.query(cmd)
                self.session.timeout = 2000
                return float(result)
            except Exception as ex:
                _log.error(ex)
                return ex

    def get_VAC(self, slot: int, channel: int):
        """
        Returns AC voltage measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 20)

        Raises:
            ValueError: invalid argument

        Returns:
            _type_: VAC (float) or exception
        """
        # trick to use function code in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
            try:
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                cmd = "MEAS:VOLT:AC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                self.session.timeout = 5000
                result = self.session.query(cmd)
                self.session.timeout = 2000
                return float(result)
            except Exception as ex:
                _log.error(ex)
                return ex      

    def get_ADC(self, slot: int, channel: int):
        """
        Returns DC current measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (21 or 22)

        Raises:
            ValueError: invalid argument

        Returns:
            _type_: ADC (float) or exception
        """
        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel == 21) or (channel == 22)), ValueError('Invalid channel. Only 21 or 22 allowed.')
            try:
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                cmd = "MEAS:CURR:DC? AUTO,DEF,(@" + slot_str + channel_str + ")"
                self.session.timeout = 5000
                result = self.session.query(cmd)
                self.session.timeout = 2000
                return float(result)
            except Exception as ex:
                _log.error(ex)
                return ex  


    def get_temp(self, slot: int, channel: int, tran_type: str, rtd_resist: int, fth_type: int, tc_type: str):
        """
        Returns temperature measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 20) 
            tran_type (str): transducer type (TC, FRTD, RTD, FTH, THER or DEF(TCouple))
            rtd_resist (int): FRTD|RTD trancduser resistance (100 or 1000 Ohm), otherwise = 0
            fth_type (int): FTH|THER type (2252, 5000, 10000), otherwise = 0
            tc_type (str): TCouple type (B, E, J, K, N, R, S, or T), otherwise = 'empty string'

        Raises:
            ValueError: invalid argument 

        Returns:
            _type_: Temperature (float) or exception
        """
        # trick to use function in NI Teststand
        slot = int(slot)
        channel = int(channel)
        rtd_resist = int(rtd_resist)
        fth_type = int(fth_type)
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
            assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
            try:                    
                slot_str = str(slot)
                channel_str = str(channel).zfill(2)
                match tran_type:
                    case 'TC' | 'DEF':
                        assert (tc_type in ["B", "E", "J", "K", "N", "R", "S", "T"]), ValueError('Error, get_temp: invalid tc_type parameter')
                        cmd = "MEAS:TEMP:TC?" + " " + tc_type + ",(@" + slot_str + channel_str + ")"
                        self.session.timeout = 5000
                        result = self.session.query(cmd)
                        self.session.timeout = 2000
                        return float(result)
                    case 'FTH' | 'THER':
                        assert ((fth_type == 2252) or (fth_type == 5000) or (fth_type == 10000)), ValueError('Error, get_temp: invalid fth_type parameter')
                        cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(fth_type) + ",(@" + slot_str + channel_str + ")"
                        self.session.timeout = 5000
                        result = self.session.query(cmd)
                        self.session.timeout = 2000
                        return float(result)
                    case 'FRTD' | 'RTD':
                        assert((rtd_resist == 100) or (rtd_resist == 1000)), ValueError('Error, get_temp: invalid rtd_resist parameters')
                        cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(rtd_resist) + ",(@" + slot_str + channel_str + ")"
                        self.session.timeout = 5000
                        result = self.session.query(cmd)
                        self.session.timeout = 2000
                        return float(result)
                    case _:
                        raise ValueError('Error, get_temp: unknown parameter')
            except Exception as ex:
                _log.error(ex)
                return ex 

    def disconnect(self):
        """Closes the connection (session) and the device.

        Returns:
            _type_: exception
        """
        # Last operation completed successfully -> Connection is OK
        if (self.rm.last_status == 0):
            try:
                self.session.close()
                self.rm.close()
            except Exception as ex:
                _log.error(ex)
                return ex
#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    DAQ970A_IP_STR = "TCPIP0::192.168.1.184::inst0::INSTR" #"TCPIP0::169.254.196.86::inst0::INSTR"
    DAQ970A_NAME_STR = "TCPIP0::K-DAQ970A-17481.local::inst0::INSTR"

    # 1. Create an instance of DAQ970A class
    daq970a = DAQ970A()

    # 2. Connect to the device
    #daq970a.connect_by_name(DAQ970A_NAME_STR)
    # or
    daq970a.connect_by_IP(DAQ970A_IP_STR)

    # 3. Do some stuff
    print(daq970a.selftest())

    res = daq970a.get_resistance(1,1)
    print(res)

    #print(daq970a.get_4w_resistance(1,2))

    #print(daq970a.get_VDC(1,3))

    #print(daq970a.get_VAC(1,4))

    #print(daq970a.get_ADC(1,21))

    #print(daq970a.get_temp(1, 1, "DEF", 0, 0, "B"))

    # 4. ERRORS 
    # Value error (channel = 25):
    #print(daq970a.get_resistance(1,25))

    # Value error (tran_type is not a string)
    #print(daq970a.get_temp(1, 1, 0, 0, 0, "B"))

    # Value error (tc_type is not a string)
    #print(daq970a.get_temp(1, 1, "DEF", 0, 0, 0))

    # 4. Close connection
    daq970a.disconnect()
    
    print("DONE.")
    
# END OF FILE