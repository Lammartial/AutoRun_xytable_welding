"""
This is the Python remake of our TRack CPU Card C# driver .DLLs
It implements the Logic CPU components library.

"""

from typing import Tuple
from time import sleep, monotonic_ns
from binascii import hexlify
from struct import pack, unpack, unpack_from
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

        self._smb_num_of_ifc = 2
        self._smb_ifc_config = dict([(i, {
                "i2c_modus": None,
                "use_hex": False,
                "use_pec": False
            }) for i in range(self._smb_num_of_ifc)])

    def __str__(self) -> str:
        return f"TRack CPU-Card device on {super().__str__()}"

    def __repr__(self) -> str:
        return f"CPU_Card({self.con.resource_str})"


    #----------------------------------------------------------------------------------------------


    def _is_ok_response(self, res) -> bool:
        return ("OK" in res.upper()) and ("ERROR" not in res.upper())


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


    def reset(self) -> str:
        return self.con.request(f"*RES")


    #----------------------------------------------------------------------------------------------

    def _convert_cpu_answer_to_bytes(self, answer) -> bytearray:
        a = answer.split(",")
        bar = bytearray([int(n) for n in a])    # Problem if values are in hex!
        return bar


    #----------------------------------------------------------------------------------------------

    # I2C Master commands

    def I2C_Master_is_PEC_enabled(self) -> bool:
        _PEC = int(self.con.request(":I2C:MAS:PEC?"))
        return (_PEC == 1)


    def I2C_Master_set_PEC(self, value: int | bool) -> bool:
        res = self.con.request(f":I2C:MAS:PEC {1 if value else 0}")
        return self._is_ok_response(res)


    def I2C_Master_ReadBytes(self, address: int, cmd: int, count: int) -> bytearray | bytes:
        res = self.con.request(f":I2C:MAS:RDB {int(address)},{int(cmd)},{int(count)}")
        b = bytes(res.split(","))
        return b


    def I2C_Master_ReadString(self, address: int, cmd: int) -> str:
        res = self.con.request(f":I2C:MAS:RDS {int(address)},{int(cmd)}")
        return res


    def I2C_Master_ReadWord(self, address: int, cmd: int) -> int:
        res = self.con.request(f":I2C:MAS:RDW {int(address)},{int(cmd)}", pause_after_write=50)
        #res = self.con.request(f":I2C:MAS:RDB {int(address)},{int(cmd)},2", pause_after_write=50)
        #buf = bytes(res.split(","))
        #w = unpack("<H", buf)[0]  # this is platform independent; buf is always little endian
        #w = pack("<H", int(res))  # Platform independent
        w = int(res)
        return int(w)


    def I2C_Master_WriteWord(self, address: int, cmd: int, word: int) -> bool:
        #buffer = pack("<H", int(word))  # platform independent
        #s = ",".join([str(int(i)) for i in buffer])
        #res = self.con.request(f":I2C:MAS:WRB {int(address)},{int(cmd)},{s}")
        res = self.con.request(f":I2C:MAS:WRW {int(address)},{int(cmd)},{int(word)}")
        return self._is_ok_response(res)


    def I2C_Master_WriteBytes(self, address: int, cmd: int, buffer: bytearray | bytes) -> bool:
        s = ",".join([str(int(i)) for i in buffer])
        res = self.con.request(f":I2C:MAS:WRB {int(address)},{int(cmd)},{len(s)},{s}")
        return self._is_ok_response(res)


    #----------------------------------------------------------------------------------------------

    # I2C Slave commands

    def I2C_Slave_setBatterySimulationCfg(self) -> bool:
        res = self.con.request(f":I2C:SLA:BATSIMulation")
        return self._is_ok_response(res)

    def I2C_Slave_setAddr(self, slave_address: int) -> bool:
        res = self.con.request(f":I2C:SLA:ADR {int(slave_address)}")
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

        b = ",".join([str(int(i)) for i in bytes_to_send])
        req = f":I2C:SLA:CFG {int(cmd)},{int(mod)},{int(cnt)},{b}"
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
        res = self.con.request(f":I2C:SLA:REQ? {int(cmd)}")
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

    # SMB commands (can use any GPIO port and thus can provide multiple ports)


    def SMB_Config(self, id: int, port_pin_clk: str, port_pin_dat: str) -> bool:
        """Configure a SMB interface using two IO pins.

        Args:
            id (int): Number of the logic interface 0, ..., 1
            port_pin_clk (str): The CLOCK pin as a string of [A0, A1, A2 ... F6, F7]
		                        The port is a letter from [A,B,C,D,E,F] followed by the pin number [0,1,2,..7]
            port_pin_dat (str): The DATA pin as a string of [A0, A1, A2 ... F6, F7]
		                        The port is a letter from [A,B,C,D,E,F] followed by the pin number [0,1,2,..7]

        Returns:
            bool: _description_
        """

        self._verify_port_exists(port_pin_clk[0])
        self._verify_bit_in_range(int(port_pin_clk[1]))
        self._verify_port_exists(port_pin_dat[0])
        self._verify_bit_in_range(int(port_pin_dat[1]))
        res = self.con.request(f":SMB:CFG {int(id)},{port_pin_clk},{port_pin_dat}")
        return self._is_ok_response(res)


    def SMB_deactivate(self, id: int) -> bool:
        res = self.con.request(f":SMB:DIS {int(id)}")
        return self._is_ok_response(res)


    def SMB_ReadBytes(self, id: int, address: int, cmd: int, count: int) -> bytearray | bytes:
        res = self.con.request(f":SMB:RDB {int(id)},{int(address)},{int(cmd)},{int(count)}")
        b = bytes(res.split(","))
        return b


    def SMB_ReadBlock(self, id: int, address: int, cmd: int, count_limit: int) -> bytearray | bytes:
        res = self.con.request(f":SMB:BLR {int(id)},{int(address)},{int(cmd)},{int(count_limit)}")
        b = bytes(res.split(","))
        return b


    def SMB_ReadString(self, id: int, address: int, cmd: int) -> str:
        res = self.con.request(f":SMB:RDS {int(id)},{int(address)},{int(cmd)}")
        return res


    def SMB_ReadWord(self, id: int, address: int, cmd: int) -> int:
        """Read a word and converts it into 64bit integer.

        Args:
            id (int): _description_
            address (int): _description_
            cmd (int): _description_

        Returns:
            int: _description_
        """
        res = self.con.request(f":SMB:RDW {int(id)},{int(address)},{int(cmd)}", pause_after_write=50)
        #w = pack("<H", int(res))  # Platform independent
        w = int(res)
        return w


    def SMB_WriteWord(self, id: int, address: int, cmd: int, word: int) -> bool:
        """Write a word as 16bits max value.

        Args:
            id (int): _description_
            address (int): _description_
            cmd (int): _description_
            word (int): _description_

        Returns:
            bool: _description_
        """

        #h = pack()
        res = self.con.request(f":SMB:WRW {int(id)},{int(address)},{int(cmd)},{int(word)}")
        return self._is_ok_response(res)


    def SMB_WriteBytes(self, id: int, address: int, cmd: int, buffer: bytearray | bytes) -> bool:
        """ Write Bytes to the slave without length information as first byte.

        Difference to WriteBlock: the length byte is not sent.

        STA ADR CMD RST ADR DAT0, DAT1, ... DATn, [PEC] STP

        Args:
            id (int): _description_
            address (int): _description_
            cmd (int): _description_
            buffer (bytearray | bytes): _description_

        Returns:
            bool: _description_
        """

        s = ",".join([str(int(i)) for i in buffer])
        res = self.con.request(f":SMB:WRB {int(id)},{int(address)},{int(cmd)},{len(s)},{s}")
        return self._is_ok_response(res)


    def SMB_WriteBlock(self, id: int, address: int, cmd: int, buffer: bytearray | bytes) -> bool:
        """Write Bytes to the slave prepended with a length information as first byte.

        STA ADR CMD RST ADR LEN, DAT0, DAT1, ... DATn, [PEC] STP

        Args:
            id (int): _description_
            address (int): _description_
            cmd (int): _description_
            buffer (bytearray | bytes): _description_

        Returns:
            bool: _description_
        """
        
        s = ",".join([str(int(i)) for i in buffer])
        res = self.con.request(f":SMB:BLW {int(id)},{int(address)},{int(cmd)},{len(s)},{s}")
        return self._is_ok_response(res)


    def SMB_ModeSet(self, id: int, use_length: bool, use_pec: bool, poll_ack: bool, check_presence: bool, spare: bool, numbers_in_hex: bool) -> bool:
        _mode = f"{1 if use_length else 0},{1 if use_pec else 0},{1 if poll_ack else 0},{1 if check_presence else 0},{1 if spare else 0},{1 if numbers_in_hex else 0}"
        res = self.con.request(f":SMB:MODE {int(id)},{_mode}")
        # map info to internal interface
        ifc = self._smb_ifc_config[int(id)]
        ifc["i2c_modus"] = _mode
        ifc["use_hex"] = numbers_in_hex
        ifc["use_pec"] = use_pec
        return self._is_ok_response(res)


    def SMB_ModeRead(self, id: int) -> Tuple[str, bytes]:
        res = self.con.request(f":SMB:MODE? {int(id)}")
        _PATTERNS = ["IFACE=", "PEC=", "HEX="]
        print(res)
        return res, bytes()


    def SMB_SimpleCmd(self, id: int, address: int, cmd: int) -> bool:
        """Send out a quick command on the SMB-bus.
		This is different from write a byte to a register. Normally it is used to activate something on the i²c slave.
		No further parameters are sent to the SMB-bus slave

        Args:
            id (int): _description_
            address (int): _description_
            cmd (int): _description_

        Returns:
            bool: _description_
        """
        res = self.con.request(f":SMB:CMD {int(id)},{int(address)},{int(cmd)}")
        return self._is_ok_response(res)


    def SMB_GetLastPEC(self, id: int) -> int:
        """Return the last PEC calculated by the CpuCard.
		This is useful in case of problems during communication using PEC.

        Args:
            id (int): _description_

        Returns:
            int: _description_
        """
        res = self.con.request(f":SMB:GPEC {int(id)}")
        w = int(res)
        return w


    #----------------------------------------------------------------------------------------------

    # IO port commands


    def _verify_port_exists(self, port_letter: str) -> None:
        assert(port_letter in ["A", "C", "F", "D", "E"]), ValueError(f"Error. Port {port_letter} does not exist.")


    def _verify_bit_in_range(self, bit_number: int, max_bit: int = 7) -> None:
        assert(bit_number >= 0 and bit_number <= max_bit), ValueError(f"Error. Bit parameter '{bit_number}' not in 0..{max_bit}.")


    def IO_Get_Portstatus(self, port_letter: str) -> str:
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter}?")
        return res

    def IO_Set_Cfg_Pin(self, port_letter: str, bit: int, cfg: int) -> bool:
        """Set Configuration for a specific port pin/bit.

        Args:
            port_letter (str): one of A, C
            bit (int): port number to set 0..7.
            cfg (int): 0 input, 1 outputt, 2 output OC, 3 output OC with internal pullup
        Returns:
            bool: true on success, fail on any error.
        """

        bit = int(bit)  # Tribute to Teststands crumpy interface
        cfg = int(cfg)  # Tribute to Teststands crumpy interface
        self._verify_port_exists(port_letter)
        self._verify_bit_in_range(bit)
        self._verify_bit_in_range(cfg, max_bit=3)
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

        cfg = int(cfg)  # Tribute to Teststands crumpy interface
        self._verify_port_exists(port_letter)
        self._verify_bit_in_range(cfg, max_bit=3)
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

        value = int(value)  # Tribute to Teststands crumpy interface
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter} 0x{f'{value:02x}'.upper()}")
        return self._is_ok_response(res)


    def IO_Read_Port_bit(self, port_letter: str, bit: int) -> int:
        bit = int(bit)  # Tribute to Teststands crumpy interface
        self._verify_port_exists(port_letter)
        res = self.con.request(f":IO:P{port_letter}:IN {bit}")
        return int(res)


    def IO_Write_Port_bit(self, port_letter: str, bit: int, value: int) -> bool:
        bit = int(bit)  # Tribute to Teststands crumpy interface
        value = int(value)  # Tribute to Teststands crumpy interface
        self._verify_port_exists(port_letter)
        self._verify_bit_in_range(bit)
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