"""
Driver for Chroma Load devices via Ethernet socket

"""

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

        super().__init__(resource_str, termination="\n", open_connection=False)  # The hioki expects to have connect/disconnect for each command
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
        self._select_channel_prefix = f":CHAN {self.channel:02d}"  # this is the prefix to address the subdevice via the connection gateway


    def select_channel(self) -> bool:
        """Selects and verifies actively the channel on the Lambda gateway.

        Returns:
            bool: true success else other channel returned
        """
        super().send(self._select_channel_prefix)
        _ch = super().request(f":CHAN")  # verify the selected channel
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

        # this will send the channel select in front of and wait then after
        self.send("", timeout=timeout, pause_after_write=pause_after_write, encoding=encoding, retries=retries)
        # now send request without selecting the channel again
        return super().request(msg, timeout=timeout, pause_after_write=pause_after_write, limit=limit, encoding=encoding, retries=retries)


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


    def set_load_mode(self, modus: str) -> bool:
        _MODES = ("CCL", "CCH", "CCDL", "CCDH", "CRL", "CRH", "CV")
        assert(modus in _MODES), ValueError(f"Modus was '{modus}' but need to be one of {_MODES}.")
        res = self.request(f":MODE {modus}")
        print(res)
        return True


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