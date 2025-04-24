
"""
Driver for Keysight and Agilent datalogger devices via Ethernet socket

"""

from rrc.eth2serial import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "1.0.0"

__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



#--------------------------------------------------------------------------------------------------

class DAQ970A(Eth2SerialDevice):
    """
    Defines the Keysight DAQ970A datalogger interface as a simple socket communication.

    Avoids need for VISA devices.

    """

    def __init__(self, resource_str: str, card_slot: int = 1):
        """
        Initialize the object with resource string (IP name:socket).
        Example "192.168.1.101:5025"

        Args:
            resource_str (str): resource string in the format IP[:SOCKET]
            card_slot (int, optional): Selects a measurement channel card on slot 1..3. Defaults to 1

        """
        super().__init__(resource_str, termination="\n", open_connection=False)  # The Keysight expects to have connect/disconnect for each command
        self.change_card_slot(card_slot)  # also sets the self.card_slot
        self._channel_delay_map = {}  # this map's values can be adjusted by the setup_channel_delay_preset() function later on
        self._voltage_range_map = {}  # this map's values can be adjusted by the setup_voltage_range_and_resolution_preset() function later on
        self._voltage_resolution_map = {}  # this map's values can be adjusted by the setup_voltage_range_and_resolution_preset() function later on


    def __str__(self) -> str:
        return f"DAQ970A device on {super().__str__()}"


    def __repr__(self) -> str:
        return f"DAQ970A({self._resource_str}, {self.card_slot})"


    #----------------------------------------------------------------------------------------------
    # insert the channel to message strings for this device


    def send(self, msg: str, timeout: int = 3000) -> None:
        super().send(msg, timeout=timeout/1000, pause_after_write=10, retries=3)


    def request(self, msg: str, timeout: int = 5000) -> str:
        return super().request(msg, timeout=timeout/1000, pause_after_write=80, retries=5).strip()


    #----------------------------------------------------------------------------------------------

    def ident(self) -> str:
        return self.request("*IDN?")

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

    def setup_channel_delay_preset(self, channel: int | str, delay_in_s: str | float = "AUTO") -> None:
        """
        Sets the route delay preset internally for the channel either to this value if > 0 and <= 60.0 or AUTO otherwise.
        The delay will than later be used if the channel is being measured for voltage.

        Args:
            channel (str | int): either single channel number as integer or a comma separated list of channels in a string.
            delay_in_s (str | float): either "AUTO" or a positive float 0 > value <= 60.0 in seconds. Defaults to "AUTO".

        """

        assert((isinstance(delay_in_s, float) and (delay_in_s > 0) and (delay_in_s <= 60.0)) or (isinstance(delay_in_s, str) and (delay_in_s == "AUTO"))), \
            ValueError('Invalid delay. Check the available delay values in the function description.')
        assert(isinstance(channel, (int, float, str))), \
            ValueError('Invalid channel. Check the available channel values in the function description.')

        if isinstance(channel, (float, int)):
            _ch = self._meas_chan(0, int(channel))
            self._channel_delay_map[_ch] = delay_in_s
        else:
            # need to be a string -> process a list of channels
            _list_of_channels = str(channel).split(",")
            for c in _list_of_channels:
                _ch = self._meas_chan(0, int(c))
                self._channel_delay_map[_ch] = delay_in_s


    def setup_voltage_range_and_resolution_preset(self, channel: int | str, scale: str | float = "AUTO", resolution: str | float = "DEF") -> None:
        """_summary_

        Args:
            channel (int): _description_
            scale (str | float, optional): _description_. Defaults to "AUTO".
            resolution (str | float, optional): _description_. Defaults to "DEF".
        """

        scale_str_list = ("AUTO", "MIN", "MAX", "DEF", "100 mV" ,"1 V", "10 V", "100 V", "300 V")
        resolution_str_list = ("MIN", "MAX", "DEF")
        assert(isinstance(scale, float) or (isinstance(scale, str) and scale in scale_str_list)), \
            ValueError('Invalid scale. Check the available scale values in the function description.')
        assert(isinstance(resolution, float) or (isinstance(resolution, str) and resolution in resolution_str_list)), \
            ValueError('Invalid resolution. Check the available resolution values in the function description.')
        assert(isinstance(channel, (int, float, str))), \
            ValueError('Invalid channel. Check the available channel values in the function description.')

        if isinstance(channel, (float, int)):
            _ch = self._meas_chan(0, int(channel))
            self._voltage_range_map[_ch] = scale
            self._voltage_resolution_map[_ch] = resolution
        else:
            # need to be a string -> process a list of channels
            _list_of_channels = str(channel).split(",")
            for c in _list_of_channels:
                _ch = self._meas_chan(0, int(c))
                self._voltage_range_map[_ch] = scale
                self._voltage_resolution_map[_ch] = resolution



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
            _ch = self._meas_chan(0, channel)
            _scale = self._voltage_range_map[_ch] if _ch in self._voltage_range_map else "AUTO"
            _resolution = self._voltage_resolution_map[_ch] if _ch in self._voltage_resolution_map else "DEF"
            cmd = f"CONF:VOLT:DC {_scale},{_resolution},(@{_ch})"
            self.send(cmd)  # this command automatically set the trigger source to IMMediate and RESETS all other measurement settings to DEFAULT (also the delays)
            if _ch in self._channel_delay_map:
                cmd = f"ROUT:CHAN:DEL {self._channel_delay_map[_ch]},(@{_ch})"
                # we have a delay setting which needs to be send to the device as it will be reset by the config above
                self.send(cmd)
            return float(self.request("READ?"))
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


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class AGILENT34972A(Eth2SerialDevice):  
    """
    Defines the older Agilent / Keysight AGILENT34972A datalogger interface as a simple socket communication.

    Avoids need for VISA devices.

    """

    def __init__(self, resource_str: str, card_slot: int = 1):
        """
        Initialize the object with resource string (IP name:socket).
        Example "192.168.1.101:5025"

        Args:
            resource_str (str): resource string in the format IP[:SOCKET]
            card_slot (int, optional): Selects a measurement channel card on slot 1..3. Defaults to 1

        """
        
        super().__init__(resource_str, termination="\n", open_connection=True)  # The Keysight expects to have connect/disconnect for each command
        self.change_card_slot(card_slot)  # also sets the self.card_slot
        self._channel_delay_map = {}  # this map's values can be adjusted by the setup_channel_delay_preset() function later on
        self._voltage_range_map = {}  # this map's values can be adjusted by the setup_voltage_range_and_resolution_preset() function later on
        self._voltage_resolution_map = {}  # this map's values can be adjusted by the setup_voltage_range_and_resolution_preset() function later on

    def __str__(self) -> str:
        return f"DAQ970A device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"DAQ970A({self._resource_str}, {self.card_slot})"

    #----------------------------------------------------------------------------------------------
    # insert the channel to message strings for this device

    def send(self, msg: str, timeout: int = 3000) -> None:
        super().send(msg, timeout=timeout/1000, pause_after_write=10, retries=3)

    def request(self, msg: str, timeout: int = 5000) -> str:
        return super().request(msg, timeout=timeout/1000, pause_after_write=80, retries=5).strip()


    #----------------------------------------------------------------------------------------------

    def ident(self) -> str:
        return self.request("*IDN?")


    def read_error_status(self) -> str:
        return self.request("SYSTEM:ERROR?")


    def wait_response_ready(self) -> bool:
        return (int(self.request("*OPC?")) == 1)  # this will automatically delay until the response is ready    

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

    def setup_channel_delay_preset(self, channel: int | str, delay_in_s: str | float = "AUTO") -> None:
        """
        Sets the route delay preset internally for the channel either to this value if > 0 and <= 60.0 or AUTO otherwise.
        The delay will than later be used if the channel is being measured for voltage.

        Args:
            channel (str | int): either single channel number as integer or a comma separated list of channels in a string.
            delay_in_s (str | float): either "AUTO" or a positive float 0 > value <= 60.0 in seconds. Defaults to "AUTO".

        """

        assert((isinstance(delay_in_s, float) and (delay_in_s > 0) and (delay_in_s <= 60.0)) or (isinstance(delay_in_s, str) and (delay_in_s == "AUTO"))), \
            ValueError('Invalid delay. Check the available delay values in the function description.')
        assert(isinstance(channel, (int, float, str))), \
            ValueError('Invalid channel. Check the available channel values in the function description.')

        if isinstance(channel, (float, int)):
            _ch = self._meas_chan(0, int(channel))
            self._channel_delay_map[_ch] = delay_in_s
        else:
            # need to be a string -> process a list of channels
            _list_of_channels = str(channel).split(",")
            for c in _list_of_channels:
                _ch = self._meas_chan(0, int(c))
                self._channel_delay_map[_ch] = delay_in_s


    def setup_voltage_range_and_resolution_preset(self, channel: int | str, scale: str | float = "AUTO", resolution: str | float = "DEF") -> None:
        """_summary_

        Args:
            channel (int): _description_
            scale (str | float, optional): _description_. Defaults to "AUTO".
            resolution (str | float, optional): _description_. Defaults to "DEF".
        """

        scale_str_list = ("AUTO", "MIN", "MAX", "DEF", "100 mV" ,"1 V", "10 V", "100 V", "300 V")
        resolution_str_list = ("MIN", "MAX", "DEF")
        assert(isinstance(scale, float) or (isinstance(scale, str) and scale in scale_str_list)), \
            ValueError('Invalid scale. Check the available scale values in the function description.')
        assert(isinstance(resolution, float) or (isinstance(resolution, str) and resolution in resolution_str_list)), \
            ValueError('Invalid resolution. Check the available resolution values in the function description.')
        assert(isinstance(channel, (int, float, str))), \
            ValueError('Invalid channel. Check the available channel values in the function description.')

        if isinstance(channel, (float, int)):
            _ch = self._meas_chan(0, int(channel))
            self._voltage_range_map[_ch] = scale
            self._voltage_resolution_map[_ch] = resolution
        else:
            # need to be a string -> process a list of channels
            _list_of_channels = str(channel).split(",")
            for c in _list_of_channels:
                _ch = self._meas_chan(0, int(c))
                self._voltage_range_map[_ch] = scale
                self._voltage_resolution_map[_ch] = resolution



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
        # NI Teststand does provide numbers as float, need to cast
        channel = int(channel)
        assert ((channel >= 1) and (channel <= 20)), ValueError('Error, get_VDC: Allowed channel range is 1 .. 20.')
        try:
            _ch = self._meas_chan(0, channel)
            _scale = self._voltage_range_map[_ch] if _ch in self._voltage_range_map else "AUTO"
            _resolution = self._voltage_resolution_map[_ch] if _ch in self._voltage_resolution_map else "DEF"
            cmd = f"CONF:VOLT:DC {_scale},{_resolution},(@{_ch})"
            self.send(cmd)  # this command automatically set the trigger source to IMMediate and RESETS all other measurement settings to DEFAULT (also the delays)
            if _ch in self._channel_delay_map:
                cmd = f"ROUT:CHAN:DEL {self._channel_delay_map[_ch]},(@{_ch})"
                # we have a delay setting which needs to be send to the device as it will be reset by the config above
                self.send(cmd)
            return float(self.request("READ?"))
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

    def get_temp(self, channel: int, tran_type: str, rtd_resist: int, fth_type: int, tc_type: str, alpha: int = 85) -> float:
        """
        Returns temperature measurement.

        From Tutorial 7, Keysight 34970A/34972A User's Guide 279
            RTD Measurements
            An RTD is constructed of a metal (typically platinum) that changes resistance with
            a change in temperature in a precisely known way. The internal DMM measures
            the resistance of the RTD and then calculates the equivalent temperature.
            An RTD has the highest stability of the temperature transducers. The output from
            an RTD is also very linear. This makes an RTD a good choice for high-accuracy,
            long-term measurements. The 34970A/34972A supports RTDs with alpha = 0.00385
            (DIN / IEC 751) using ITS-90 software conversions and alpha = 0.00391 using IPTS-68
            software conversions. "PT100" is a special label that is sometimes used to refer to
            an RTD with alpha = 0.00385 and R 0 = 100Ω.
            The resistance of an RTD is nominal at 0 °C and is referred to as R 0 . The 34970A/
            34972A can measure RTDs with R 0 values from 49Ω to 2.1 kΩ.
            You can measure RTDs using a 2-wire or 4-wire measurement method. The 4-wire
            method provides the most accurate way to measure small resistances. Connection
            lead resistance is automatically removed using the 4-wire method.

        Args:
            slot (int): slot number (1, 2, 3)
            channel (int): channel number (1 ... 20)
            tran_type (str): transducer type (TC, FRTD, RTD, FTH, THER or DEF(TCouple))
            rtd_resist (int): FRTD|RTD trancduser resistance (100 or 1000 Ohm), otherwise = 0
            fth_type (int): FTH|THER type (2252, 5000, 10000), otherwise = 0
            tc_type (str): TCouple type (B, E, J, K, N, R, S, or T), otherwise = 'empty string'
            alpha (int): additional parameter for older Agilent Datalogger. usually 85 or 91. Defaults to 85

        Raises:
            ValueError: invalid argument

        Returns:
            float: Temperature
        """

        channel = int(channel)
        rtd_resist = int(rtd_resist)
        fth_type = int(fth_type)          
        assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
        _ch = self._meas_chan(0, channel)
        try:
            match tran_type:
                case 'TC' | 'DEF':
                    assert (tc_type in ["B", "E", "J", "K", "N", "R", "S", "T"]), ValueError('Error, get_temp: incorrect tc_type parameter')
                    cmd = f"MEAS:TEMP? TC,{tc_type},(@{_ch})" 
                    return float(self.request(cmd))
                case 'FTH' | 'THER':
                    assert ((fth_type == 2252) or (fth_type == 5000) or (fth_type == 10000)), ValueError('Error, get_temp: incorrect fth_type parameter')
                    self.send(f"SENS:TEMP:TRAN:THERM:TYPE {str(fth_type)},(@{_ch})")
                    cmd = f"MEAS:TEMP? {tran_type},{str(fth_type)},(@{_ch})"
                    return float(self.request(cmd))
                case 'FRTD' | 'RTD':
                    assert((alpha == 85) or (alpha == 91)), ValueError('Error alpha: incorrect alpha parameter')
                    assert((rtd_resist == 100) or (rtd_resist == 1000)), ValueError('Error, get_temp: incorrect rtd_resist parameters')
                    self.send(f"SENS:TEMP:TRAN:FRTD:TYPE {alpha},(@{_ch})")
                    self.send(f"SENS:TEMP:TRAN:FRTD:RES {str(rtd_resist)},(@{_ch})")
                    cmd = f"MEAS:TEMP? {tran_type},{alpha},(@{_ch})"
                    return float(self.request(cmd))
                case _:
                    raise ValueError('Error, get_temp: unknown parameter')
        except Exception as ex:
            #_log.exception(ex)
            raise


    # some functions found in DataloggerLXI class
    def preselect_channel_measure_VDC(self, channel: int) -> None:
        assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
        _ch = self._meas_chan(0, channel)
        _scale = self._voltage_range_map[_ch] if _ch in self._voltage_range_map else "AUTO"
        _resolution = self._voltage_resolution_map[_ch] if _ch in self._voltage_resolution_map else "DEF"
        cmd = f"CONF:VOLT:DC {_scale},{_resolution},(@{_ch})"
        self.send(cmd)
        self.send("TRIG:SOUR IMM")


    def read_configured_channel_measure(self) -> float:
        return float(self.request("READ?"))


    def set_monitor_channel(self, channel: int) -> None:
        assert ((channel >= 1) and (channel <= 20)), ValueError('Invalid channel. Allowed range is 1 .. 20.')
        cmd = "ROUT:MON (@" + self._meas_chan(0, channel) + ")"
        self.send(cmd)

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

def daq_class_selector(resource_str: str, card_slot: int) -> DAQ970A | AGILENT34972A:
    c = DAQ970A(resource_str, card_slot=card_slot)
    s = c.ident()
    if "AGILENT" in s.upper():
        c.close_connection(force=True)
        c = AGILENT34972A(resource_str, card_slot=card_slot)
    return c


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