"""
This is the Python remake of our TRack CPU Card C# driver .DLLs
It implements the Logic CPU components library.

"""

from typing import Tuple
from struct import pack, unpack, unpack_from
from rrc.eth2serial.base import Eth2SerialDevice, OWN_PRIMARY_IP
from rrc.serialport import SerialComportDevice

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



class CPU_Card:

    con: Eth2SerialDevice | SerialComportDevice     # can communicate either by USB/Serial or Ethernet socket

    def __init__(self, resource_string: str) -> None:
        """Opens the connection to a CPU card device depending on the given resource string.

        All commands are exchanged in ASCII, numbers are either decimal or hex with
        NumberDecimalSeparator = "." and optional NumberGroupSeparator = "," (english convention)

        Args:
            resource_string (str): "<IP address or host name>:<port number>"  -> ethernet connection (socket)
                                   "<port name>,<baud rate (9600,115200, etc.)>,<line settings (8N1 etc.)>" -> serial connection
        """

        # we need to create the connection device
        if "," in resource_string:
            self.con = SerialComportDevice(resource_string, termination="\x04")
        else:
            self.con = Eth2SerialDevice(resource_string, termination="\n")


    def __str__(self) -> str:
        return f"TRack CPU-Card device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"CPU_Card({self.con.resource_str}, {self.channel})"


    #----------------------------------------------------------------------------------------------


    def _is_ok_response(self, res) -> bool:
        return (res == "Ok.")


    #----------------------------------------------------------------------------------------------

    # Standard SCPI commands

    def Ident(self) -> str:
        return self.con.request("*IDN?")


    #----------------------------------------------------------------------------------------------

    # I2C Master commands

    def I2C_Master_is_PEC_enabled(self) -> bool:
        _PEC = int(self.con.request(":I2C:MAS:PEC?"))
        return (_PEC == 1)

    def I2C_Master_set_PEC(self, value: int | bool) -> bool:
        res = self.con.request(f":I2C:MAS:PEC {value}")
        return self._is_ok_response(res)

    def I2C_Master_ReadBytes(self, address: int, cmd: int, count: int) -> bytearray | bytes:
        res = self.con.request(f":I2C:MAS:RDB {address},{cmd},{count}")
        b = bytes(res.split(","))
        return b

    def I2C_Master_ReadString(self, address: int, cmd: int) -> str:
        res = self.con.request(f":I2C:MAS:RDS {address},{cmd}")
        return res

    def I2C_Master_ReadWord(self, address: int, cmd: int) -> int:
        res = self.con.request(f":I2C:MAS:RDW {address},{cmd}", pause_after_write=50)
        #w = pack("<H", res)
        w = int(res)
        return w

    def I2C_Master_WriteWord(self, address: int, cmd: int, word: int) -> bool:
        res = self.con.request(f":I2C:MAS:WRW {address},{cmd},{word}")
        return self._is_ok_response(res)

    def I2C_Master_WriteBytes(self, address: int, cmd: int, buffer: bytearray | bytes) -> bool:
        s = ",".join([int(i) for i in buffer])
        res = self.con.request(f":I2C:MAS:WRB {address},{cmd},{len(s)},{s}")
        return self._is_ok_response(res)

    #----------------------------------------------------------------------------------------------

    # I2C Slave commands

    #----------------------------------------------------------------------------------------------

    # SMB commands (can use any GPIO port!)


    #----------------------------------------------------------------------------------------------

    # IO port commands






# END OF FILE