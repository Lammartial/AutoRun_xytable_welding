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


    def __str__(self) -> str:
        return f"DZPlus device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"DZPlus({self.resource_str}, {self.channel})"


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
        self._select_channel_prefix = f"INST:NSEL {self.channel:02d}"  # this is the prefix to address the subdevice via the connection gateway


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

        return super().request(msg if msg is None else f"{self.select_channel_prefix};{msg}",
                               timeout=timeout, pause_after_write=pause_after_write, limit=limit, encoding=encoding, retries=retries)


    #----------------------------------------------------------------------------------------------


    def ident(self) -> str:
        return self.request("*IDN?")


    def reset(self) -> str:
        return self.send("*RST")    # no return!


    #----------------------------------------------------------------------------------------------


# END OF FILE