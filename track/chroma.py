"""
Driver for Chroma Load devices via Ethernet socket

"""

from typing import List, Tuple
from time import sleep
from rrc.eth2serial import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.1.0"

__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



class DC63600(Eth2SerialDevice):
    """Defines the Chroma DC-Load 63600 communication in a rack using a series of them with one gateway.

    Avoids need for VISA devices.s

    Args:
        SCPIRemoteDevice (_type_): _description_
    """

    def __init__(self, resource_str: str, channel: int = 1) -> None:
        """
        Initialize the object with resource string (IP name:socket).
        Example "192.168.1.101:5025"

        Args:
            resource_str (str): resource string in the format <IP>:<SOCKET>
            channel (int, optional): Selects a channel to address communication to the sub-device in range of 1..10. Defaults to 1.

        """

        super().__init__(resource_str, termination="\n", trim_termination=True, open_connection=True)  # The Chroma device can keep connection open (saves overhead time)
        self.last_cmd_written = None
        self.change_channel(channel)


    def __str__(self) -> str:
        return f"Chroma Load, V1.1, DC63600 device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"DC63600({self.resource_str}, {self.channel})"


    #----------------------------------------------------------------------------------------------

    def change_channel(self, new_channel: int):
        """
        Changes the channel number of a device instance.

        Args:
            new_slot (int): slot number (1, 2, 3)
        """
        MAX_SUB = 10  # set this to your needs
        assert (int(new_channel) > 0 and int(new_channel) < MAX_SUB+1), ValueError(f"Error, 'new_channel' must be in 1..{MAX_SUB} but was {int(new_channel)}")
        self.channel = int(new_channel)
        self._select_channel_prefix = f":CHAN {self.channel}"  # this is the prefix to address the subdevice via the connection gateway


    def select_channel(self) -> bool:
        """Selects and verifies actively the channel on the Lambda gateway.

        Returns:
            bool: true success else other channel returned
        """
        super().send(self._select_channel_prefix)
        _ch = super().request(f":CHAN?")  # verify the selected channel
        return (int(_ch) == self.channel)


    #----------------------------------------------------------------------------------------------

    def send(self, msg: str,
             timeout: float = 3.0,
             pause_after_write: int | None = 20,    # Note: this sets the delay for all calls as default
             encoding: str | None = "utf-8",
             retries: int = 1) -> None:
        """Sends command in 'msg' to the device.
        It prefixes with the channel selection if a msg is given to send the command to the correct subdevice.

        Args:
            msg (str): message string to send. Line teminator will be added.
            timeout (float, optional): _description_. Defaults to 1.0.
            encoding (str, optional): will be passed to write() function.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            bool: _description_
        """

        super().send(f"{self._select_channel_prefix};{msg}", timeout=timeout, pause_after_write=pause_after_write, encoding=encoding, retries=retries)


    #----------------------------------------------------------------------------------------------


    def request(self, msg: str | None,
                timeout: float | None = 3,
                pause_after_write: int | None = 20,    # Note: this sets the delay for all calls as default
                limit: int = 0,
                encoding: str | None = "utf-8",
                retries: int = 1) -> str:
        """Sends command in 'msg' to the device if not None, else does not send. Wait the pause_after_write if given then read from the device.
        It prefixes with the channel selection if a msg is given to send the command to the correct subdevice.

        Args:
            msg (str): _description_
            timeout (float, optional): _description_. Defaults to 3.0.
            pause_after_write (int, optional):  Pause after writing the command for a request in milliseconds,
                before reading and waiting the result. None disables it. Defaults to None.
            limit (int, optional): _description_. Defaults to 0.
            encoding (str, optional): if given will be used to decode() result from bytes. If None, bytes will be returned. Defaults to utf-8.
            retries (int, optional): Number of retries - NOT YET IMPLEMENTED - . Defaults to 1 (no retry).

        Returns:
            str: _description_
        """

        return super().request(f"{self._select_channel_prefix};{msg}", timeout=timeout, pause_after_write=pause_after_write, limit=limit, encoding=encoding, retries=retries)

    #----------------------------------------------------------------------------------------------


    def wait_response_ready(self) -> bool:
        return (int(self.request("*OPC?")) == 1)  # this will automatically delay until the response is ready


    def ident(self) -> str:
        return self.request("*IDN?")


    def reset(self) -> str:
        return self.send("*RST")    # no return!


    #----------------------------------------------------------------------------------------------


    def initialize_device(self) -> bool:
        _ok = True
        # preconfigure device
        self.send(":LOAD OFF")
        _ok &= self.wait_response_ready()
        self.send(":ACT ON")
        _ok &= self.wait_response_ready()
        self.send(":CONF:VOLT:RANG 80")
        _ok &= self.wait_response_ready()
        self.send(":CURR:RANG 80")
        _ok &= self.wait_response_ready()
        return _ok


    def _convert_to_onoff_string(self, state: int | str) -> str:
        _STATES = ["OFF", "ON"]
        if isinstance(state, str):
            assert(state.upper() in _STATES), ValueError(f"Parameter state may be in '{_STATES}' only, but was '{state}'.")
            _state_str = state.upper()
        else:
            state = int(state)  # Teststand provides float or "Number"
            assert(state in [0, 1]), ValueError(f"Parameter state may be integer of 0,1 but was '{state}'")
            _state_str = _STATES[state]
        return _state_str


    def _convert_to_onoff_int(self, state: int | str) -> int:
        _STATES = ["OFF", "ON"]
        if isinstance(state, str):
            assert(state.upper() in _STATES), ValueError(f"Parameter state may be in '{_STATES}' only, but was '{state}'.")
            _state_int = _STATES.index(state.upper())
        else:
            state = int(state)  # Teststand provides float or "Number"
            assert(state in [0, 1]), ValueError(f"Parameter state may be integer of 0,1 but was '{state}'")
            _state_int = state
        return _state_int


    def set_load_mode(self, modus: str) -> bool:
        """Set the working mode of the Load.

        Load Modes:
            CCL - Constant Current Low
            CCH - Constant Current High
            CCDL - ???
            CCDH - ???
            CRL - Constant Resitence Low
            CRH - Constant Resistence High
            CV - Constant Voltage

        Args:
            modus (str): String of "CCL", "CCH", "CCDL", "CCDH", "CRL", "CRH", "CVL", "CVH"

        Returns:
            bool: _description_
        """
        _MODES = ("CCL", "CCH", "CCDL", "CCDH", "CRL", "CRH", "CVL", "CVH")
        assert(modus in _MODES), ValueError(f"Modus was '{modus}' but need to be one of {_MODES}.")
        self.send(f":MODE {modus}")
        return self.wait_response_ready()


    def get_load_mode(self) -> str:
        return self.request(f":MODE?")


    def set_load_output(self, state: int | str) -> bool:
        _state_str = self._convert_to_onoff_string(state)
        self.send(f":LOAD {_state_str}")
        return self.wait_response_ready()


    def set_load_off(self) -> bool:  # Compatibility
        return self.set_load_output("OFF")


    def set_load_on(self) -> bool:  # Compatibility
        return self.set_load_output("ON")


    def get_voltage_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_voltage(), ndigits=int(ndigits))


    def get_voltage(self) -> float:
        """
        This command queries the present measured voltage.

        Returns:
            float: voltage in volt
        """

        self.set_measure_sense_to("UUT")
        return float(self.request(":MEAS:VOLT?"))


    def set_measure_sense_to(self, sense_target: str) -> bool:
        assert(sense_target in ["UUT", "LOAD"]), ValueError(f"Parameter sense target need to be in UUT, LOAD. It was '{sense_target}'.")
        self.send(f":MEAS:INP {sense_target}")
        return self.wait_response_ready()


    def measure_voltage(self) -> float:  # compatibility function
        return self.get_voltage()



    def get_current_rounded(self, ndigits: int = 3) -> float:
        return round(self.get_current(), ndigits=int(ndigits))


    def get_current(self) -> float:
        """
        This command queries the present current measurement.

        Returns:
            float: DC current in ampere
        """
        return float(self.request("MEAS:CURR?"))


    def measure_current(self) -> float:  # compatibility function
        return self.get_current()


    def set_load_resistance(self, resistance: float) -> bool:
        """Set the Resistance of the Load.

        We are using static load L1

        Args:
            resistance (float): _description_

        Returns:
            bool: _description_
        """
        self.send(f":RES:STAT:L1 {resistance}")  # Note: :STATic was shown in the DC63xxx manual but not in out DLL lib
        #self.send(f":RES:L1 {resistance}")  # code like in DLL
        return self.wait_response_ready()


    def set_resistance_change_ratio(self, rise_time: float | str = "MIN", fall_time: float | str = "MIN") -> bool:
        """_summary_

        Args:
            rise_time (float | str, optional): Ratio in Ohm/µs or MAX or MIN. Defaults to "MIN".
            fall_time (float | str, optional): Ratio in Ohm/µs or MAX or MIN. Defaults to "MIN".

        Returns:
            bool: _description_
        """
        # NOTE: did not find rise/fall timing for resistance but for current and power in the data sheet
        self.send(f":RES:RISE {rise_time};:RES:FALL {fall_time}")
        return self.wait_response_ready()


    def set_load_current(self, current: float) -> bool:
        self.send(f":CURR:STAT:L1 {current}")
        return self.wait_response_ready()


    def set_current_change_ratio(self, rise_time: float | str = "MIN", fall_time: float | str = "MIN") -> bool:
        """_summary_

        Args:
            rise_time (float | str, optional): Ratio in A/µs or MAX or MIN. Defaults to "MIN".
            fall_time (float | str, optional): Ratio in A/µs or MAX or MIN. Defaults to "MIN".

        Returns:
            bool: _description_
        """

        self.send(f":CURR:STAT:RISE {rise_time};:CURR:STAT:FALL {fall_time}")
        return self.wait_response_ready()


    def set_load_voltage(self, voltage) -> bool:
        self.send(f":VOLT:L1 {voltage}")
        return self.wait_response_ready()


    def set_constant_voltage_current_limit(self, current_limit) -> bool:
        self.send(f":VOLT:CURR {current_limit}")
        return self.wait_response_ready()


    def set_short_circuit(self, state: int | str) -> bool:
        _state_str = self._convert_to_onoff_string(state)
        self.send(f":LOAD:SHORT {_state_str}")
        return self.wait_response_ready()


    def activate_device_display(self) -> bool:
        """Activate the Display and show the channel inforamtion of Load Object.

        Returns:
            bool: _description_
        """

        if (self.channel & 1) != 0:
            self.send(f":SHOW:DISPLAY L")
        else:
            self.send(f":SHOW:DISPLAY R")
        return self.wait_response_ready()


    def activate_device_dual_voltage_display(self) -> bool:
        self.send(f":SHOW:DISPLAY LRV")
        return self.wait_response_ready()


    def activate_device_dual_current_display(self) -> bool:
        self.send(f":SHOW:DISPLAY LRI")
        return self.wait_response_ready()


    def set_channel_sync_mode(self, state: int | str) -> bool:
        """ Enable or Disable the channel syncronization mode.

        Args:
            state (int | str): _description_

        Returns:
            bool: _description_
        """
        _state_int = self._convert_to_onoff_int(state)
        self.send(f":CHAN:SYNC {_state_int}")
        return self.wait_response_ready()


    def all_loads_on(self) -> bool:
        self.send(f":RUN")
        return self.wait_response_ready()


    def all_loads_off(self) -> bool:
        self.send(f":ABORT")
        return self.wait_response_ready()


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class ACSource(Eth2SerialDevice):
    pass
    # do we need this ?



#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
     # quick test, just call: python chroma.py
    dev = DC63600("172.23.130.32:2101")
    print(dev.ident())


# END OF FILE