"""
Driver for Lambda ZUP devices via Ethernet socket

"""

from rrc.eth2serial import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #



class DCZPlus(Eth2SerialDevice):
    """Defines the Lambda DC ZPlus source communication in a rack using a series of them with one gateway.

    Avoids need for VISA devices.

    Args:
        SCPIRemoteDevice (_type_): _description_
    """

    def __init__(self, resource_str: str, channel: int = 1):
        """
        Initialize the object with resource string (IP name:socket).
        Example "192.168.1.101:5025"

        Args:
            resource_str (str): resource string in the format <IP>:<SOCKET>
            channel (int, optional): Selects a channel to address communication to the sub-device in range of 1..10. Defaults to 1.

        """
        super().__init__(resource_str, termination="\n", open_connection=False)  # The hioki expects to have connect/disconnect for each command
        self.change_channel(channel)
        self.response_delay_ms = 50

    def __str__(self) -> str:
        return f"DZPlus device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"DZPlus({self.resource_str}, {self.channel})"


    #----------------------------------------------------------------------------------------------


    def change_channel(self, new_channel: int) -> None:
        """
        Changes the channel number of a device instance.

        Args:
            new_slot (int): slot number (1, 2, 3)
        """
        MAX_SUB = 10  # set this to your needs
        assert (int(new_channel) > 0 and int(new_channel) < MAX_SUB+1), ValueError(f"Error, 'new_channel' must be in 1..{MAX_SUB} but was {int(new_channel)}")
        self.channel = int(new_channel)
        self._select_channel_prefix = f"INST:NSEL {self.channel:02d}"  # this is the prefix to address the subdevice via the connection gateway


    def select_channel(self) -> bool:
        """Selects and verifies actively the channel on the Lambda gateway.

        Returns:
            bool: true success else other channel returned
        """
        super().send(self._select_channel_prefix)
        _ch = super().request(f"INST:NSEL")  # verify the selected channel
        return (int(_ch) == self.channel)


    #----------------------------------------------------------------------------------------------


    def send(self, msg: str,
             timeout: float = 3.0,
             pause_after_write: int | None = None,
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

        super().send(f"{self.select_channel_prefix};{msg}", timeout=timeout, pause_after_write=pause_after_write, encoding=encoding, retries=retries)


    #----------------------------------------------------------------------------------------------


    def request(self, msg: str | None,
                timeout: float | None = 3,
                pause_after_write: int | None = None,
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

        return super().request(msg if msg is None else f"{self._select_channel_prefix};{msg}",
                               timeout=timeout, pause_after_write=pause_after_write, limit=limit, encoding=encoding, retries=retries)


    #----------------------------------------------------------------------------------------------

    def wait_response_ready(self) -> str:
        return self.request("SYST:ERR?")  # this will automatically delay until the response is ready


    def ident(self) -> str:
        return self.request("*IDN?")


    def reset(self) -> str:
        return self.send("*RST")    # no return!


    #----------------------------------------------------------------------------------------------

    def initialize_device(self) -> None:
        # preconfigure device
        self.send(":LOAD OFF")
        self.send(":ACT ON")
        self.send(":CONF:VOLT:RANG 80")
        self.send(":CURR:RANG 80")
        #sleep(0.25)

    def set_output(self, state: bool | int) -> bool:
        _st = "ON" if state else "OFF"
        self.send(f"OUTP:REL {_st}")
        self.send(f"OUTP {_st}")  # set Output AND Output Relay - The Relay disconnet the AC Source physically

    def clear_protection(self) -> bool:
        x = self.request("OUTP:PROT:CLE")
        ret = self.wait_response_ready()
        return ret == "0"

    def set_foldback(self, mode: str | int) -> bool:
        """_summary_

        Args:
            mode (int): OFF|0, CC|1, CV|2

        Returns:
            bool: _description_
        """

        _MODES = ("OFF", "CC", "CV")
        if isinstance(mode, int):
            if mode < 0 or mode > 2:
                raise ValueError(f"Mode value  is invalid '{mode}'. Allowed are 0=OFF, 1=CC or 2=CV")
            _mode_str = _MODES[mode]
        else:
            if mode.upper() not in _MODES:
                raise ValueError(f"Mode string is invalid '{mode}'. Allowed are OFF, CC or CV")
            _mode_str = mode
        self.send(f"OUTP:PROT:FOLD {_mode_str}")
        ret = self.wait_response_ready()
        return ret == "0"


    def get_foldback(self) -> str:
        return self.request("OUTP:PROT:FOLD?", pause_after_write=20)

    def set_voltage(self, voltage: float) -> bool:
        self.send(f"VOLT {voltage}")
        ret = self.wait_response_ready()
        return ret == "0"

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    dev = DCZPlus("172.23.130.33:8003")
    print(dev.ident())


# END OF FILE