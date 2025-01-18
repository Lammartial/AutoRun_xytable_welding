"""
This is the Python remake of our TRack CPU Card C# driver .DLLs
It implements the Logic CPU components library.

"""

from typing import Tuple
from time import sleep
from rrc.eth2serial.base import Eth2SerialDevice, OWN_PRIMARY_IP
from rrc.serialport import SerialComportDevice

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
            self.con = SerialComportDevice(resource_string, termination="\x04", xonxff=True)
        else:
            self.con = Eth2SerialDevice(resource_string, termination="\n")


    def __str__(self) -> str:
        return f"TRack CPU-Card device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"CPU_Card({self.con.resource_str})"


    #----------------------------------------------------------------------------------------------


    def _is_ok_response(self, res) -> bool:
        return (res == "Ok.")


    #----------------------------------------------------------------------------------------------

    # Standard SCPI commands

    def ident(self) -> str:
        """Returns the identification string of the application.

        Returns:
            str: _description_
        """
        return self.con.request("*IDN")  # Note: *IDN? returns string of 0xff, probably unflashed area


    def ident_boot(self) -> str:
        """Reads the identification string of the bootloader by switching the CPU into bootloader
        then read IDN and after that return to the application.

        Returns:
            str: Identification string of the bootloader.
        """
        r1 = self.con.request("*BOO")
        sleep(0.050)  #  Give CPUcard time to start bootloader and re-init UART
        res = self.con.request("*IDN")  # Note: *IDN? returns string of 0xff, probably unflashed area
        r2 = self.con.request(f"*RES")
        sleep(0.050)  # Give CPUcard time to start application and re-init UART
        return res


    def help(self) -> str:
        """Returns the identification string of the application.

        Returns:
            str: _description_
        """
        hlp = "\r".join([f"{q}:\n{self.con.request(q)}" for q in ("*HEL", "*HEL:IO", "*HEL:I2C", "*HEL:SMB", "*HEL:SPI", "*HEL:PRO", "*HEL:PRO:AVR", "*HEL:PRO:OBE")])
        return hlp


    def Reset(self) -> str:
        return self.con.request(f"*RES")


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

    def I2C_Slave_setBatterySimulationCfg(self) -> bool:
        res = self.con.request(f":I2C:SLA:BATSIMulation")
        return self._is_ok_response(res)

    def I2C_Slave_setAddr(self, slave_address: int) -> bool:
        res = self.con.request(f":I2C:SLA:ADR {slave_address}")
        return self._is_ok_response(res)

    def I2C_Slave_setCfg(self, cmd: int, mod: int, cnt: int, bytes_to_send: bytearray) -> bool:
        """Configurate I2C Slave command entry.
		Args:
            cmd (int): Command on the CPU card shell react.
            mod (int): Read/Write/PEC modes
            cnt (int): count of bytes 0...8
            byte (_type_): byte(s) to send on request

        Returns:
            bool: _description_
        """

        b = ",".join([int(i) for i in bytes_to_send])
        req = f":I2C:SLA:CFG {cmd},{mod},{cnt},{b}"
        res = self.con.request(req)
        return self._is_ok_response(res)

    def I2C_Slave_getCfg(self) -> str:
        res = self.con.request(":I2C:SLA:CFG?")
        return res

    def I2C_Slave_clearAllCmds(self) -> bool:
        res = self.con.request(f":I2C:SLA:CLE!")
        return self._is_ok_response(res)

    def I2C_Slave_clearAllRequests(self) -> bool:
        res = self.con.request(f":I2C:SLA:REQ!")
        return self._is_ok_response(res)

    def I2C_Slave_CmdRequest(self, cmd: int) -> str:
        res = self.con.request(f":I2C:SLA:REQ? {cmd}")
        return res

    def I2C_Slave_enablePEC(self, enable: bool) -> bool:
        res = self.con.request(f":I2C:SLA:PEC {1 if enable else 0}")
        return self._is_ok_response(res)

    def I2C_Slave_getPEC(self) -> bool:
        """get slave PEC status.

        Returns:
            bool: true if PEC enable, false if not
        """
        res = self.con.request(f":I2C:SLA:PEC?")
        return (res == "1")


    #----------------------------------------------------------------------------------------------

    # Global commands

    def I2C_Reset(self) -> bool:
        """Resets the I2C hardware interface (unblocking lines).

        Returns:
            bool: _description_
        """
        res = self.con.request(f":I2C:RES")
        return self._is_ok_response(res)

    def CPU_Reset(self) -> bool:
        # compatibility function
        return self.Reset()

    #----------------------------------------------------------------------------------------------

    # SMB commands (can use any GPIO port!)


    #----------------------------------------------------------------------------------------------

    # IO port commands

    def _verify_port_exists(self, port_letter: str) -> None:
        assert(port_letter in ["A", "C", "F", "D", "E"]), ValueError(f"Error. Port {port_letter} does not exist.")

    def IO_Get_Portstatus(self, port_letter: str) -> str:
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter}?")
        return res

    def IO_Set_Cfg(self, port_letter: str, bit: int, cfg: int) -> bool:
        """Set Configuration for a specific port bit.

        Args:
            port_letter (str): one of A, C
            bit (int): port number to set 0..7.
            cfg (int): 0 input, 1 outputt, 2 output OC, 3 output OC with internal pullup
        Returns:
            bool: true on success, fail on any error.
        """

        self._verify_port_exists(port_letter)
        assert(bit < 8), ValueError(f"Error. Bit paramater '{bit}' not in 0..7.")
        assert(cfg < 4), ValueError(f"Error. Cfg paramater '{cfg}' not in 0..3.")
        res = self.con.request(f":IO:P{port_letter}:CFG b{bit}={cfg}")
        return self._is_ok_response(res)

    def IO_Set_Cfg(self, port_letter: str, cfg: int) -> bool:
        """Set all Bits of a specific port to the same configuration.

        Args:
            port_letter (str): one of A, C
            cfg (int): 0 input, 1 outputt, 2 output OC, 3 output OC with internal pullup

        Returns:
            bool: true on success, fail on any error.
        """
        self._verify_port_exists(port_letter)
        assert(cfg < 4), ValueError(f"Error. Cfg paramater '{cfg}' not in 0..3.")
        res = self.con.request(f":IO:P{port_letter}:CFG {','.join([f'b{i}={cfg}' for i in range(8)])}")
        return self._is_ok_response(res)

    def IO_Get_Cfg(self, port_letter: str) -> str:
        """Get the configuration of a Port.

        Args:
            port_letter (str): One of A, C, F, D or E

        Returns:
            str: returns the configuration of the whole port
        """
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter}:CFG?")
        return res

    def IO_Set_Port(self, port_letter: str, value: int) -> bool:
        """Set a whole Port with a defined byte/word depending on the port size.

        Args:
            port_letter (str): One of A, C, F, D or E
            value (int): _description_

        Returns:
            bool: _description_
        """
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter} 0x{f'{value:02x}'.upper()}")
        return self._is_ok_response(res)

    def IO_Read_Port_bit(self, port_letter: str, bit: int) -> int:
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter}:IN {bit}")
        return int(res)

    def IO_Write_Port_bit(self, port_letter: str, bit: int, value: int) -> bool:
        self._verify_port_exists(port_letter)
        assert(bit < 8), ValueError(f"Error. Bit paramater '{bit}' not in 0..7.")
        res = self.con.request(f":IO:P{port_letter}:O b{bit}={value}")
        return self._is_ok_response(res)

    #----------------------------------------------------------------------------------------------



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    # quick test, just call: python cpu_card.py
    dev = CPU_Card("COM8,115200,8N1")
    print(dev.ident())
    print(dev.ident_boot())
    print(dev.help().replace("\r","\n\r"))


# END OF FILE