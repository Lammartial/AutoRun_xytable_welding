from rrc.visa import AdhocVisaDevice
from rrc.eth2serial import Eth2SerialDevice

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



# #--------------------------------------------------------------------------------------------------
# class DAQ970A(AdhocVisaDevice):
#     #
#     # Currently there are two backends available: The one included in pyvisa,
#     # which uses the IVI library (include NI-VISA, Keysight VISA, R&S VISA, tekVISA etc.),
#     # and the backend provided by pyvisa-py, which is a pure python implementation
#     # of the VISA library.
#     # If no backend is specified, pyvisa uses the IVI backend if any IVI library
#     # has been installed (see next section for details). Failing that, it uses the
#     # pyvisa-py backend.
#     # explicit Python backend:  rm = ResourceManager('@py')
#     # explicit IVI lib backend: rm = ResourceManager('Path to library')
# #--------------------------------------------------------------------------------------------------

#     # This could be a way to avoid try ... except in each function
#     #def e(methodtoRun, *args):
#     #    try:
#     #        methodtoRun(*args)    # pass arguments along
#     #    except Exception as inst:
#     #        print(type(inst))    # the exception instance
#     #        print(inst.args)     # arguments stored in .args
#     #        print(inst)          # __str__ allows args to be printed directly,

#     def __init__(self, resource_str: str, card_slot: int = 1):
#         """
#         Initialize the object with visa resource string (IP name).
#         Example "TCPIP0::192.168.1.101::inst0::INSTR"

#         Args:
#             resource_str (str): visa resource string
#             card_slot (int, optional): Selects a measurement channel card on slot 1..3. Defaults to 1 

#         """
#         super().__init__(resource_str, read_termination="\n", write_termination=None, pause_on_retry=10)  # configure the itech VISA device
#         self.change_card_slot(card_slot)  # also sets the self.card_slot

#     def __str__(self) -> str:
#         return f"DAQ970A VISA device on {super().__str__()}"

#     def __repr__(self) -> str:
#         return f"DAQ970A({self.resource_str}, {self.card_slot})"

#     #----------------------------------------------------------------------------------------------
#     # insert the channel to message strings for this device

#     def send(self, msg: str, timeout: int = 3000) -> None:
#         super().send(msg, pause_after_write=10, timeout=timeout, retries=3)

#     def request(self, msg: str, timeout: int = 5000) -> str:
#         return super().request(msg, pause_after_write=80, timeout=timeout, retries=5).strip()

#--------------------------------------------------------------------------------------------------
class DAQ970A(Eth2SerialDevice):
    """Defines the Keysight DAQ970A datalogger interface as a simple socket communication.

    Avoids need for VISA devices.

    Args:
        SCPIRemoteDevice (_type_): _description_
    """
  
    def __init__(self, resource_str: str, card_slot: int = 1):
        """
        Initialize the object with resource string (IP name:socket).
        Example "192.168.1.101:5025"

        Args:
            resource_str (str): resource string in the format IP[:SOCKET]
            card_slot (int, optional): Selects a measurement channel card on slot 1..3. Defaults to 1 

        """
        super().__init__(resource_str, termination="\n", open_connection=False)  # The hioki expects to have connect/disconnect for each command
        self.change_card_slot(card_slot)  # also sets the self.card_slot

    def __str__(self) -> str:
        return f"DAQ970A device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"DAQ970A({self.resource_str}, {self.card_slot})"

    #----------------------------------------------------------------------------------------------
    # insert the channel to message strings for this device

    def send(self, msg: str, timeout: int = 3000) -> None:
        super().send(msg, timeout=timeout, pause_after_write=10, retries=3)

    def request(self, msg: str, timeout: int = 5000) -> str:
        return super().request(msg, timeout=timeout, pause_after_write=80, retries=5).strip()

    
    #----------------------------------------------------------------------------------------------
    def selftest(self) -> int:
        """
        Returns device self-test results, takes ~ 2 sec.

        Returns:
            int: 0 (pass) or 1 (one or more tests failed)
        """
        cmd = f"*TST?"
        return int(self.request(cmd))

    def selftest_all(self) -> int:
        """
        Returns device full self-test results, takes ~5 sec

        Returns:
            int: 0 (pass) or 1 (one or more tests failed)
        """
        cmd = f"TEST:ALL?"
        return int(self.request(cmd, timeout=10000))

    def set_raw_request(self, cmd: str):
        """
        Sets raw SCPI command and returns the result or error.

        Args:
            cmd (str): SCPI command

        Returns:
            str: response
        """
        return self.request(str(cmd), timeout=2000)
    
    def set_raw_command(self, cmd: str):
        """
        Sets raw SCPI command.

        Args:
            cmd (str): SCPI command

        Returns:
            str: response
        """
        return self.send(str(cmd), timeout=2000)

    #----------------------------------------------------------------------------------------------
    
    def _meas_chan(self, slot: int, channel: int) -> str:
        return f"{slot if slot > 0 else self.card_slot}{channel:02d}"
        
    #----------------------------------------------------------------------------------------------

    def change_card_slot(self, new_slot: int):
        """
        Changes the slot number of a device instance.

        Args:
            new_slot (int): slot number (1, 2, 3)
        """
        assert (int(new_slot) > 0 and int(new_slot) < 4), ValueError(f"Error, 'card_slot' must be in 1..3 but was {int(new_slot)}")        
        self.card_slot = int(new_slot)

    #----------------------------------------------------------------------------------------------
    
    def get_resistance_rounded(self, channel: int, ndigits: int = 3, scale: str | float = "AUTO", resolution: str | float = "DEF") -> float:
        """See doc of get_resistance."""
        return round(self.get_resistance(int(channel)), ndigits=int(ndigits), scale=scale, resolution=resolution)
    
    def get_resistance(self, channel: int, scale: str | float = "AUTO", resolution: str | float = "DEF") -> float:
        """Returns resistance measurement.

        Args:
            channel (int): channel number (1 ... 20)
            scale (str | float, optional): Measurement range or scale. 
                        Possible values: A string of "AUTO", "MIN", "MAX", "DEF", "100 Ω", "1 kΩ", "100 kΩ", "1 MΩ", "10 MΩ", "1 GΩ" 
                        or float value specifying the range in ohm.
                        Defaults to "AUTO".
            resolution (str | float, optional): Measurement resolution. 
                        Possible values: A string of "MIN", "MAX", "DEF" or float value specifying the resolution in ohm.
                        <resolution> = 1 PLC (0.000003 x Range)
                        Defaults to "DEF".
        
        Raises:
            ValueError: invalid argument
        
        Returns:
            float: Resistance in ohms.

        """

        channel = int(channel)
        scale_str_list = ("AUTO", "MIN", "MAX", "DEF", "100 Ω", "1 kΩ", "100 kΩ", "1 MΩ", "10 MΩ", "1 GΩ")
        resolution_str_list = ("MIN", "MAX", "DEF")
        assert ((channel >= 1) and (channel <= 20)), ValueError('Error, get_resistance: Allowed channel range is 1 .. 20.')
        assert(isinstance(scale, float) or (isinstance(scale, str) and scale in scale_str_list)), \
            ValueError('Invalid scale. Check the available scale values in the function description.')
        assert(isinstance(resolution, float) or (isinstance(resolution, str) and resolution in resolution_str_list)), \
            ValueError('Invalid resolution. Check the available resolution values in the function description.')
        cmd = f"MEAS:RES? {scale},{resolution},(@{self._meas_chan(0, channel)})"
        return float(self.request(cmd))
        

    def get_4w_resistance_rounded(self, channel: int, ndigits: int = 3, scale: str | float = "AUTO", resolution: str | float = "DEF") -> float:
        """See doc of get_4w_resistance."""
        return round(self.get_4w_resistance(int(channel)), ndigits=int(ndigits), scale=scale, resolution=resolution)
    
    def get_4w_resistance(self, channel: int, scale: str | float = "AUTO", resolution: str | float = "DEF") -> float:
        """
        Returns 4-wire resistance measurement.

        Args:
            channel (int): channel number (1 ... 10)
            scale (str | float, optional): Measurement range or scale. 
                        Possible values: A string of "AUTO", "MIN", "MAX", "DEF", "100 Ω", "1 kΩ", "100 kΩ", "1 MΩ", "10 MΩ", "1 GΩ" 
                        or float value specifying the range in ohm.
                        Defaults to "AUTO".
            resolution (str | float, optional): Measurement resolution. 
                        Possible values: A string of "MIN", "MAX", "DEF" or float value specifying the resolution in ohm.
                        <resolution> = 1 PLC (0.000003 x Range)
                        Defaults to "DEF".
        
        Raises:
            ValueError: invalid argument
        
        Returns:
            float: Resistance in ohms.
        """
        
        channel = int(channel)
        scale_str_list = ("AUTO", "MIN", "MAX", "DEF", "100 Ω", "1 kΩ", "100 kΩ", "1 MΩ", "10 MΩ", "1 GΩ")
        resolution_str_list = ("MIN", "MAX", "DEF")
        assert ((channel >= 1) and (channel <= 10)), ValueError('Error, get_4w_resistance: Allowed channel range is 1 .. 10.')
        assert(isinstance(scale, float) or (isinstance(scale, str) and scale in scale_str_list)), \
            ValueError('Invalid scale. Check the available scale values in the function description.')
        assert(isinstance(resolution, float) or (isinstance(resolution, str) and resolution in resolution_str_list)), \
            ValueError('Invalid resolution. Check the available resolution values in the function description.')
        cmd = f"MEAS:FRES? {scale},{resolution},(@{self._meas_chan(0, channel)})"
        return float(self.request(cmd))
       
    
    def get_VDC_rounded(self, channel: int, ndigits: int = 3) -> float:
        return round(self.get_VDC(int(channel)), ndigits=int(ndigits))
    
    def get_VDC(self, channel: int) -> float:
        """
        Returns DC voltage measurement.

        Args:
            channel (int): channel number (1 ... 20)

        Raises:
            ValueError: invalid argument

        Returns:
            float: VDC
        """
        # trick to use function in NI Teststand
        channel = int(channel)
        assert ((channel >= 1) and (channel <= 20)), ValueError('Error, get_VDC: Allowed channel range is 1 .. 20.')
        try:
            cmd = "MEAS:VOLT:DC? AUTO,DEF,(@" + self._meas_chan(0, channel) + ")"
            #return abs(float(self.request(cmd)))  # we need to clear the sign as some adapters have swapped +/- senses
            return float(self.request(cmd))
        except Exception as ex:
            #_log.exception(ex)
            raise
    
    def get_VAC_rounded(self, channel: int, ndigits: int = 3) -> float:
        return round(self.get_VAC(int(channel)), ndigits=int(ndigits))
    
    def get_VAC(self, channel: int) -> float:
        """
        Returns AC voltage measurement.

        Args:
            channel (int): channel number (1 ... 20)

        Raises:
            ValueError: invalid argument

        Returns:
            float: VAC
        """
        # trick to use function code in NI Teststand
        channel = int(channel)
        assert ((channel >= 1) and (channel <= 20)), ValueError('Error, get_VAC: Allowed channel range is 1 .. 20.')
        try:
            cmd = "MEAS:VOLT:AC? AUTO,DEF,(@" + self._meas_chan(0, channel) + ")"
            return float(self.request(cmd))
        except Exception as ex:
            #_log.exception(ex)
            raise


    def get_ADC_rounded(self, channel: int, ndigits: int = 3) -> float:
        return round(self.get_ADC(int(channel)), ndigits=int(ndigits))
    
    def get_ADC(self, channel: int, scale: str = "1 A") -> float:
        """
        Returns DC current measurement.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (21 or 22)
            scale: AUTO, "1 uA", "10 uA", "100 uA", "1 mA", "10 mA", "100 mA", "1 A"

        Raises:
            ValueError: invalid argument

        Returns:
            float: ADC
        """
        
        channel = int(channel)
        scale_str_list = ("AUTO", "1 uA", "10 uA", "100 uA", "1 mA", "10 mA", "100 mA", "1 A")
        assert ((channel == 21) or (channel == 22)), ValueError('Invalid channel. Only 21 or 22 allowed.')
        assert(scale in scale_str_list), ValueError('Invalid scale. Check the available scale values in the function description.')
        try:
            cmd = f"MEAS:CURR:DC? {scale},(@{self._meas_chan(0, channel)})"
            return float(self.request(cmd))
        except Exception as ex:
            #_log.exception(ex)
            raise

    def get_temp_rounded(self, channel: int, tran_type: str, rtd_resist: int, fth_type: int, tc_type: str, ndigits: int = 3) -> float:
        return round(self.get_temp(int(channel), tran_type, int(rtd_resist), int(fth_type), tc_type), ndigits=int(ndigits))
    
    def get_temp(self, channel: int, tran_type: str, rtd_resist: int, fth_type: int, tc_type: str) -> float:
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
            float: Temperature
        """
        # trick to use function in NI Teststand
        channel = int(channel)
        rtd_resist = int(rtd_resist)
        fth_type = int(fth_type)
        assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
        try:
            match tran_type:
                case 'TC' | 'DEF':
                    assert (tc_type in ["B", "E", "J", "K", "N", "R", "S", "T"]), ValueError('Error, get_temp: incorrect tc_type parameter')
                    cmd = "MEAS:TEMP:TC?" + " " + tc_type + ",(@" + self._meas_chan(0, channel) + ")"
                    return float(self.request(cmd))
                case 'FTH' | 'THER':
                    assert ((fth_type == 2252) or (fth_type == 5000) or (fth_type == 10000)), ValueError('Error, get_temp: incorrect fth_type parameter')
                    cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(fth_type) + ",(@" + self._meas_chan(0, channel) + ")"
                    return float(self.request(cmd))
                case 'FRTD' | 'RTD':
                    assert((rtd_resist == 100) or (rtd_resist == 1000)), ValueError('Error, get_temp: incorrect rtd_resist parameters')
                    cmd = "MEAS:TEMP:"+ tran_type +"?" + " " + str(rtd_resist) + ",(@" + self._meas_chan(0, channel) + ")"
                    return float(self.request(cmd))
                case _:
                    raise ValueError('Error, get_temp: unknown parameter')
        except Exception as ex:
            #_log.exception(ex)
            raise

    #def disconnect(self):
    #    """Closes the connection (session) and the device.
    #
    #    Returns:
    #        _type_: exception
    #    """
    #    # Last operation completed successfully -> Connection is OK
    #    if (self.rm.last_status == 0):
    #        try:
    #            self.session.close()
    #            self.rm.close()
    #        except Exception as ex:
    #            _log.exception(ex)
    #            raise
#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # TESTS have been moved out to module: test_keysight.py
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   
    print("DONE.")

# END OF FILE