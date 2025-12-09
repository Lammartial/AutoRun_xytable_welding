"""Petalit battery chipset specific commands as extebntion 
of a Standard SmartBattery command set.

Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

#import errno
from typing import Tuple, List
from time import sleep
from binascii import unhexlify, hexlify
from os import urandom
from hashlib import sha1
from itertools import chain
from struct import unpack, unpack_from, iter_unpack
from collections import OrderedDict
from datetime import datetime as dt
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
#from rrc.battery_errors import BatteryError
from rrc.smbus import BusMaster
from rrc.smartbattery import Cmd, BatteryError
from rrc.chipsets.base import Chipset
from rrc.chipsets.bq40z50 import BQ40Z50R1
from datetime import datetime


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

def _od2t(d: OrderedDict) -> tuple:
    """To convert an ordered dict to a tuple of values for TestStand Container.

    Args:
        d (OrderedDict): _description_

    Returns:
        tuple: _description_
    """

    return tuple([t for t in d.values()])



#--------------------------------------------------------------------------------------------------


class PetaliteChipset(BQ40Z50R1):
    """
    Chipset class for Petalite BMS-IC containing all common functions.

    """

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)

    def __init__(self, smbus: BusMaster, slvAddress: int = 0x0b, pec: bool = False):
        # Note: explicitely replicate the parameters here for having
        # option in teststand to change them on call
        super().__init__(smbus, slvAddress=slvAddress, pec=pec)

    def __str__(self) -> str:
        return f"SmartBattery with Petalite-chipset at 0x{(self.address & 0xff):02X} on {str(self.bus)}"

    def __repr__(self) -> str:
        return f"PetaliteBMS({repr(self.bus)}, slvAddress={(self.address & 0xff):02X}, pec={self.pec})"

    #----------------------------------------------------------------------------------------------
    @property
    def name(self):
        """Returns the battery chipset name."""
        return "Petalite BMS"

    def autodetect(self):
        """Identifies the presence of a chipset of this type."""
        pass


    def isReady(self):
        #return super().isReady()
        # return self.bus.isReady(self.address)
        ok = False
        try:
            _, ok = self.bus.readWord(self.address, Cmd.VOLTAGE, self.pec)
        except OSError as ex:
            #if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
            #    # only expected exception is "device not present" or "timed out"
            #    # -> forward this exception
            #    raise ex
            pass
        return ok


    def _read_sealed_status(self) -> bytearray:
        buf = self._read_manufacturer_block(0x20da)
        if buf and len(buf) >= 1:
            afe = int(buf[0])  # 0 = unsealed, 1 = sealed
            gg = int(buf[1])   # 0 = unsealed, 1 = sealed
        buf, ok = self.readBlock(0xC2)  # 0 = unsealed, 1 = sealed
        mcu = int(buf[0])
        return mcu, afe, gg


    def is_sealed(self, refresh: bool = True) -> bool:
        """Checks if the battery is sealed to disable write access to critical parameters.

        Returns:
            bool: True if sealed
        """
        
        mcu, afe, gg = self._read_sealed_status()
        return afe != 0 and gg != 0 and mcu != 0
        

    def is_unsealed(self, check_fullaccess: bool = False, refresh: bool = False) -> bool:
        mcu, afe, gg = self._read_sealed_status()
        return afe == 0 and gg == 0 and mcu == 0


    def seal(self) -> bool:
        """Seals the full chipset: AFE, GG and MCU to disable write access to critical parameters.

        Returns:
            bool: True if successful
        """
        # Petalite uses same seal command as BQ40Z50
        return super().seal()
    


    def enable_full_access(self) -> bool:
        # unseal MCU
        ok = self.writeBlock(0xC2, bytes([ 
                                0xF3, 0xD8, 0x58, 0x94, 0x2E, 0x9B, 0x68, 0x02, 
                                0x02, 0xE6, 0xD8, 0xD9, 0xE1, 0x55, 0x17, 0x5A, 
                                0xD5, 0xAE, 0x49, 0x39, 0xCC, 0xB7, 0x87, 0x38, 
                                0x8D, 0x2F, 0x3E, 0x7D, 0x16, 0x69, 0x1F, 0xDA]))
        # unseal AFE and GG
        # ...
        return ok
    

    def cell_voltages(self) -> tuple:
        """ Returns the cell voltage registers of the chip as array.

            Independent how many cells are connected, all four registers
            are always read and returned. The array is [vcell1,vcell2,vcell3,vcell4,vcell5,vcell6,vcell7].
        Returns:
            array: integers
        """
        return (
            self.readWordVerified(Cmd.CELL1_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL2_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL3_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL4_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL5_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL6_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL7_VOLTAGE)[0]
        )

    #---HELPER FOR PRODUCTION----------------------------------------------------------------------


    def _write_manufacturer_block(self, command: int, data: bytearray | bytes) -> None:
        """
        Sends a command via Manufacturer Block Access and reads data.
        Repeats up to 5 times if the command has been sent and recieved are not equal.

        Args:
            command (int): command number
            length (int): length of the data buffer or None if unknown or may vary

        Returns:
            bytearray: data buffer
        """

        command = int(command)
        buf = bytearray([command & 0xFF, (command >> 8) & 0xFF]) + bytearray(data)
        #print("WB:", hexlify(buf))   # DEBUG
        self.manufacturer_block_access = buf


    def _read_manufacturer_block(self, command: int, length: int | None = None) -> bytearray:
        """
        Sends a command via Manufacturer Block Access and reads data.
        Repeats up to 5 times if the command has been sent and recieved are not equal.

        Args:
            command (int): command number
            length (int): length of the data buffer or None if unknown or may vary

        Returns:
            bytearray: data buffer
        """
        
        command = int(command)
        if (length is not None):
            length = int(length)   # tribute to Teststand
        # ok = self.writeBlock(0x44, command.to_bytes(2, "little"))  # try to update the value(s)
        # res, ok = self.readBlock(0x44)
        self.manufacturer_block_access = command
        buf = self.manufacturer_block_access  # read from 0x44
        #print("RB:", hexlify(res))   # DEBUG
        rcv_command = unpack("<H", buf[:2])[0]
        if (length is not None) and (len(buf) > length + 2):
            res = buf[2:2+length]  # slice the command and limit to length
        else:
            res = buf[2:]  # slice the command and return all data
        # if the expected length may variy you need to pass None to length
        if (rcv_command == command):
            return res
        raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(res)}, {len(res)}")

    
    #----------------------------------------------------------------------------------------------


    def manufacturing_daqstatus1(self, hexi: bool | str | None = None) -> tuple:
        """Read DAQ Status 1 and return the registers as they come.

        Stores a OrderedDict in self._manufacturing_daqstatus1 with the converted data.

        Raises:
            BatteryError: _description_

        Returns:
            tuple: all values in order as a tuple for TestStand interface
        """

        for _retry in range(5):
            try:
                #buf = self._read_manufacturer_block(0x20d6)
                # workaround for NCD.io 16 bytes read restriction
                buf1 = self._read_manufacturer_block(0xda10)
                buf2 = self._read_manufacturer_block(0xda11)
                buf3 = self._read_manufacturer_block(0xda12)
                buf = buf1 + buf2 + buf3
                self._manufacturing_daqstatus1 = OrderedDict({
                    "block": self._maybe_hexlify(buf, hexi),
                    # data come little endian
                    "cell_voltage_1": round(unpack_from("<H", buf, 0)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_2": round(unpack_from("<H", buf, 2)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_3": round(unpack_from("<H", buf, 4)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_4": round(unpack_from("<H", buf, 6)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_5": round(unpack_from("<H", buf, 8)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_6": round(unpack_from("<H", buf, 10)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "cell_voltage_7": round(unpack_from("<H", buf, 12)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "afe_tos_voltage":    round(unpack_from("<H", buf, 14)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "afe_pack_voltage":   round(unpack_from("<H", buf, 16)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "afe_ld_pin_voltage": round(unpack_from("<H", buf, 18)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "gg_voltage": round(unpack_from("<H", buf, 20)[0] * 1e-3, 3),  # mV, unsigned short, little endian
                    "afe_cc2_current": round(unpack_from("<h", buf, 22)[0] * 1e-3, 3),  # mA, signed short, little endian
                    "afe_cc3_current": round(unpack_from("<h", buf, 24)[0] * 1e-3, 3),  # mA, signed short, little endian
                    "gg_current":   round(unpack_from("<h", buf, 26)[0] * 1e-3, 3),  # mA, signed short, little endian
                    # 2 words reserve
                })
                return _od2t(self._manufacturing_daqstatus1)  # Teststand interface
            except Exception as ex:
                sleep(0.020)
                _last_exception = ex
        raise Exception(f"DAQSTATUS 1: {_last_exception}")  # pass throuhg the last exeption


    def manufacturing_daqstatus2(self, celsius: bool = True, hexi: bool | str | None = None) -> tuple:
        """Read DAQ Status 2 and return the registers as they come.

        Stores a OrderedDict in self._manufacturing_daqstatus2 with the converted data.

        Raises:
            BatteryError: _description_

        Returns:
            tuple: all values in order as a tuple for TestStand interface
        """

        for _retry in range(5):
            try:
                buf = self._read_manufacturer_block(0x20d7)
                self._manufacturing_daqstatus2 = OrderedDict({
                    "block": self._maybe_hexlify(buf, hexi),
                    # data come little endian
                    "ts1_temperature": round(unpack_from("<H", buf, 0)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian
                    "ts3_temperature": round(unpack_from("<H", buf, 2)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian
                    "afe_hdq_temperature": round(unpack_from("<H", buf, 4)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian
                    "afe_dchg_temperature": round(unpack_from("<H", buf, 6)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian                    
                    "afe_ddsg_temperature": round(unpack_from("<H", buf, 8)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian
                    "gg_temperature":    round(unpack_from("<H", buf, 10)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0), 1),  # 0.1K, unsigned short, little endian
                    # 10 words reserve                    
                })
                return _od2t(self._manufacturing_daqstatus2)  # Teststand interface
            except Exception as ex:
                sleep(0.020)
                _last_exception = ex
        raise Exception(f"DAQSTATUS 2: {_last_exception}")  # pass throuhg the last exeption


    def pushbutton_state(self) -> int:
        """Reads the current state of the push button.

        Note: this is the direct reading of the buttons input pin.

        Returns:
            int: 1=pressed, 0=not pressed
        """

        buf = self._read_manufacturer_block(0x20db)
        btn_state = unpack_from("<B", buf, 0)[0]
        return btn_state


    def setup_rtc(self) -> float:
        """Returns readback check time difference in s

        Returns:
            float: _description_
        """
        now = dt.now()
        print(now)
        buf = bytes([ 
                    ((now.year - 2000) & 0xFF), (now.month & 0xFF), (now.day & 0xFF),
                    (now.hour & 0xFF), (now.minute & 0xFF), (now.second& 0xFF)
                    ])
        #print(hexlify(buf))   # DEBUG
        self._write_manufacturer_block(0x20d9, buf)
        return self.check_rtc_against_systemtime()
        ##print("DIFF:", d) # DEBUG 
        #return (d < 2.0)  # within 2 seconds
        
    
    def read_rtc(self) -> Tuple[dt, str]:
        buf = self._read_manufacturer_block(0x20d9)        
        _fmt = "<B"
        year = unpack_from(_fmt, buf, offset=0)[0] + 2000
        month = unpack_from(_fmt, buf, offset=1)[0]
        day = unpack_from(_fmt, buf, offset=2)[0]
        hour = unpack_from(_fmt, buf, offset=3)[0]
        minute = unpack_from(_fmt, buf, offset=4)[0]
        second = unpack_from(_fmt, buf, offset=5)[0]
        d = dt(year, month, day, hour, minute, second)
        return d, d.isoformat(sep=" ")


    def check_rtc_against_systemtime(self) -> float:
        now = dt.now()
        rtc, rtc_str = self.read_rtc()
        _diff = now-rtc
        return _diff.total_seconds()
       

    #----------------------------------------------------------------------------------------------


    def read_manufacturer_info_block(self, hexi: bool | str | None = None) -> bytearray | str:
        """Reads the Manufacturer Info block (MIB) from the battery.

        Note: This uses Manufacturer Block Access 0x44 and limits to 32 bytes.

        Returns:
            bytearray: Manufacturer Info data block
        """

        #buf = self._read_manufacturer_block(0x0070, 32)
        # workaround for NCD.io 16 bytes read restriction
        buf1 = self._read_manufacturer_block(0xda30)
        buf2 = self._read_manufacturer_block(0xda31)
        buf3 = self._read_manufacturer_block(0xda32)
        buf = buf1 + buf2 + buf3
        print("rMIB:", hexlify(buf))   # DEBUG
        return self._maybe_hexlify(buf, hexi)
    
    
    def write_manufacturer_info_block(self, data: bytearray | bytes | str) -> bool:
        """Writes the Manufacturer Info block (MIB) to the battery.

        Note: This uses Manufacturer Block Access 0x44 and limits to 32 bytes.
              If provided data is less than 32 bytes it is padded with zeroes.

        Args:
            data (bytearray | bytes | str): Manufacturer Info data block. If provided as str it must be hex string.
        """

        if isinstance(data, str):
            _data = unhexlify(data)
        else:
            _data = data
        if len(_data) > 32:
            raise ValueError(f"Manufacturer Info block must be maximum 32 bytes long. You provided {len(_data)} bytes.")
        buf = _data.ljust(32, b'\x00')  # pad to 32 bytes
        print("wMIB:", hexlify(buf))   # DEBUG
        self._write_manufacturer_block(0x0070, buf)
        return True


   
    #----------------------------------------------------------------------------------------------


    def read_pcba_udi_block(self, insertstr_pcba: bool = False, hexi: bool | str | None = None) -> str:
        """Reads the PCBA UDI block from the Manufacturer info block (MIB):
        
        A01-A15, 15 bytes
        stripping 0's at the end.
                
        Args:
            insertstr_pcba (bool): If true, inserts "PCBA" after first character.
            hexi (bool | str | None, optional): If set to true, returns hex string. Defaults to None.

        Returns:
            bytes: UDI data block of max. 15 bytes either as bytearray or hex string.
        
        """

        mib = self.read_manufacturer_info_block()  # read the full block (32 bytes)
        if insertstr_pcba:
            _udi =mib[:1] + b'PCBA' + mib[1:15] # insert PCBA after first character/byte
        else:
            _udi = mib[:15]
        if hexi:
            udi = self._maybe_hexlify(_udi, hexi)
        else:
            udi = _udi.rstrip(b'\x00').decode(encoding="utf-8") # get the first 15 bytes and strip trailing zeroes
        #print(udi)  # DEBUG       
        return udi
        

    def write_pcba_udi_block(self, udi_block: str | bytes | bytearray) -> bool:
        """Writes the UDI block to the battery's MIB which strips the "PCBA" term to save space.
       
        A01-A15, 15 bytes
        padding 0's at the end.

        Args:
            udi_block (str): UDI to be written to the battery, potentially including the "PCBA" prefix.             
        """

        if isinstance(udi_block, str):
            if "PCBA" in udi_block:
                # strip PCBA from udi
                _data = bytes(udi_block.replace("PCBA", ""), encoding="utf-8")
            else:
                _data = bytes(udi_block, encoding="utf-8")
        else:
            pass  # is already bytes or bytearray
        assert (len(_data) >= 2 and len(_data) <= 15), ValueError(f"Clean UDI length={len(_data)} not between 2 and 15.")
        mib = self.read_manufacturer_info_block()  # read the full block (32 bytes)
        buf = _data.ljust(15, b'\x00') + mib[15:32]  # preserve bytes 15..31 of MIB
        #print(hexlify(buf))   # DEBUG
        ok = self.write_manufacturer_info_block(buf)
        sleep(0.090) # wait for FLASH WRITE DONE: 80 ms worst case
        return ok
    
    
    #----------------------------------------------------------------------------------------------


    def read_serial_number_block(self, hexi: bool | str | None = None) -> str:
        """Reads our serial number block from the Manufacturer info block (MIB): 
        
        A17-A30, 14bytes

        Args:
            hexi (bool | str | None, optional): If set to true, returns hex string. Defaults to None.

        Returns:
            bytes: UDI data block of 14 bytes either as bytearray or hex string.
        """
    
        mib = self.read_manufacturer_info_block()  # read the full block (32 bytes)
        sn = mib[16:30]  # get bytes 16..29
        return self._maybe_hexlify(sn, hexi).decode(encoding="utf-8").rstrip('\x00')
    

    def write_serial_number_block(self, data: bytearray | bytes | str) -> bool:
        """Writes serial number to the Manufacturer info block MIB at:
        
        A17-A30, 14 bytes
            
        Args:
            data (bytearray | bytes | str): UDI data block of 16 bytes either as bytearray or string.
        """
    
        if isinstance(data, str):
            _data = bytes(data, encoding="utf-8")
        else:
            _data = bytes(data)
        assert (len(_data) <= 16), ValueError(f"Manufacturer Info block must be maximum 16 bytes long. You provided {len(_data)} bytes.")
        mib = self.read_manufacturer_info_block()  # read the full block (32 bytes)
        buf = mib[:16] + _data.ljust(14, b'\x00') + mib[30:32]  # preserve bytes 0..15 and 30..31 of MIB
        return self.write_manufacturer_info_block(buf)        
        

    #----------------------------------------------------------------------------------------------


    def set_pack_sn(self, sn: str) -> bool:
        return super().set_pack_sn(sn)
    

    def set_manufacturer_date(self):
        """Writes the current date to the battery as manufacture date.

        Returns:
            bool: True if successful
        """
        return super().set_manufacturer_date()


    def operation_status(self, hexi: bool | str | None = None) -> tuple:
        """This command returns the AFE BatteryStatus as OperationStatus() flags. 

        Args:
            hexi (bool | str | None, optional): activates a conversion of data into "blocks"
                if not None or bool and False. If bool and True "blocks" contains ascii hex nibbles.
                Defaults to None.

        Returns:
            tuple: (
                block: bytes or str with hex as ascii string, depending on hexi
                value: the bitflag register as singned 64bit integer
                bitflags: 0 or 1 values in descending bit order bit15 ... bit0
            )
        """

        buf = self._read_manufacturer_block(0x0054)
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 2):
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}, {buf}")
        os = unpack_from("<H", buf)[0]
        self._operation_status = OrderedDict({
            "block"     : self._maybe_hexlify(buf, hexi),
            #"value"     : os,
            # data come little endian
            "SLEEP":     ((os>>15) & 1),
            "RSVD1":     ((os>>14) & 1),
            "SDM":       ((os>>13) & 1),
            "PF":        ((os>>12) & 1),
            "SS":        ((os>>11) & 1),
            "FUSE":      ((os>>10) & 1),
            "SEC1":      ((os>>9) & 1),
            "SEC0":      ((os>>8) & 1),
            "OTPB":      ((os>>7) & 1),
            "OTPW":      ((os>>6) & 1),
            "COW_CHK":   ((os>>5) & 1),
            "WD":        ((os>>4) & 1),
            "POR":       ((os>>3) & 1),
            "SLEEP_EN":  ((os>>2) & 1),
            "PCHG_MODE": ((os>>1) & 1),
            "CFGUPDATE": ((os>>0) & 1),
        })
        return _od2t(self._operation_status)   


    def manufacturing_status(self, hexi: bool | str | None = None) -> tuple:
        """This command returns the AFE ManufacturingStatus as ManufacturingStatus() flags.

        Args:
            hexi (bool | str | None, optional): activates a conversion of data into "blocks"
                if not None or bool and False. If bool and True "blocks" contains ascii hex nibbles.
                Defaults to None.

        Returns:
            tuple: (
                block: bytes or str with hex as ascii string, depending on hexi
                value: the bitflag register as singned 64bit integer
                bitflags: 0 or 1 values in descending bit order bit15 ... bit0
            )
        """

        buf = self._read_manufacturer_block(0x0057)       
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 1):
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}")
        os = unpack("<B", buf)[0]
        self._manufacturing_status = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            #"value"     : os,
            # data come little endian
            "OTPW_EN": ((os>>7) & 1),
            "PF_EN": ((os>>6) & 1),
            "PDSG_TEST": ((os>>5) & 1),
            "FET_EN": ((os>>4) & 1),
            "RSVD": ((os>>3) & 1),
            "DSG_TEST": ((os>>2) & 1),
            "CHG_TEST": ((os>>1) & 1),
            "PCHG_TEST": ((os>>0) & 1),
        })        
        return _od2t(self._manufacturing_status)


    def gauging_status(self, hexi: bool | str | None = None) -> tuple:
        """This command returns the GaugingStatus as GG combined flags.

        Args:
            hexi (bool | str | None, optional): activates a conversion of data into "blocks"
                if not None or bool and False. If bool and True "blocks" contains ascii hex nibbles.
                Defaults to None.

        Returns:
            tuple: (
                block: bytes or str with hex as ascii string, depending on hexi
                value: the bitflag register as singned 64bit integer
                bitflags: 0 or 1 values in descending bit order bit15 ... bit0
            )   
        """

        buf = self._read_manufacturer_block(0x0056)       
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 6):
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}")        
        os = unpack_from("<Q", buf + bytes([0,0]))[0]  # unsigned long long need 8 bytes: pad by 2 zero bytes
        self._gauging_status = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            #"value"     : os,
            # data come little endian
            # bits 48 .. 63 reserved and 0
            # Control Status
            "RSVD1": ((os>>47) & 1),   # Reserved
            "FAS": ((os>>46) & 1),     # Status bit that indicates the BQ34Z100-R2 is in FULL ACCESS SEALED state. Active when set.
            "SS": ((os>>45) & 1),      # Status bit that indicates the BQ34Z100-R2 is in the SEALED State. Active when set.
            "CALEN": ((os>>44) & 1),   # Status bit that indicates the BQ34Z100-R2 calibration function is active. True when set. Default is 0.
            "CCA": ((os>>43) & 1),     # Status bit that indicates the BQ34Z100-R2 Coulomb Counter Calibration routine is active. Active when set.
            "BCA": ((os>>42) & 1),     # Status bit that indicates the BQ34Z100-R2 Board Calibration routine is active. Active when set.
            "CSV": ((os>>41) & 1),      # Status bit that indicates a valid data flash checksum has been generated. Active when set.
            "RSVD2": ((os>>40) & 1),    # Reserved
            "RSVD3": ((os>>39) & 1),    # Reserved
            "RSVD4": ((os>>38) & 1),    # Reserved
            "FULLSLEEP": ((os>>37) & 1), # Status bit that indicates the BQ34Z100-R2 is in FULL SLEEP mode. True when set. The state can only be detected by monitoring the power used by the BQ34Z100-R2 because any communication will automatically clear it.
            "SLEEP": ((os>>36) & 1),    # Status bit that indicates the BQ34Z100-R2 is in SLEEP mode. True when set.
            "LDMD": ((os>>35) & 1),     # Status bit that indicates the BQ34Z100-R2 Impedance Track algorithm using constant-power mode. True when set. Default is 0 (CONSTANT CURRENT mode).
            "RUP_DIS": ((os>>34) & 1),  # Status bit that indicates the BQ34Z100-R2 Ra table updates are disabled. True when set.
            "VOK": ((os>>33) & 1),      # Status bit that indicates cell voltages are OK for Qmax updates. True when set.
            "QEN": ((os>>32) & 1),      # Status bit that indicates the BQ34Z100-R2 Qmax updates are enabled. True when set.
            # Flags A
            "OTC": ((os>>31) & 1),      # Overtemperature in Charge condition is detected. True when set
            "OTD": ((os>>30) & 1),      # Overtemperature in Discharge condition is detected. True when set
            "BATHI": ((os>>29) & 1),    # Battery High bit that indicates a high battery voltage condition. Refer to the data flash Cell BH parameters for threshold settings. True when set
            "BATLOW": ((os>>28) & 1),   # Battery Low bit that indicates a low battery voltage condition. Refer to the data flash Cell BL parameters for threshold settings. True when set
            "CHG_INH": ((os>>27) & 1),  # Charge Inhibit: unable to begin charging. Refer to the data flash [Charge Inhibit Temp Low, Charge Inhibit Temp High] parameters for threshold settings. True when set
            "XCHG": ((os>>26) & 1), # Charging not allowed.
            "FC": ((os>>25) & 1),    # (Fast) charging allowed. True when set
            "CHG": ((os>>24) & 1),   # Instruction Flash Checksum Failure
            "RESET": ((os>>23) & 1), # Set when OCV Reading is taken, cleared when not in RELAX or OCV Reading Not Taken.
            "RSVD5": ((os>>22) & 1), # Reserved
            "RSVD6": ((os>>21) & 1), # Reserved
            "CF": ((os>>20) & 1),    # Condition Flag indicates that the gauge needs to run through an update cycle to optimize accuracy.
            "RSVD7": ((os>>19) & 1), # Reserved
            "SOC1": ((os>>18) & 1),  # State-of-Charge Threshold 1 reached. True when set
            "SOCF": ((os>>17) & 1),  # State-of-Charge Threshold Final reached. True when set
            "DSG": ((os>>16) & 1),   # Discharging detected. True when set
            # Flags B
            "SOH": ((os>>15) & 1),     # StateOfHealth() calculation is active.
            "LIFE": ((os>>14) & 1),    # Indicates that LiFePO4 RELAX is enabled
            "FIRSTDOD": ((os>>13) & 1),  # Set when RELAX mode is entered and then cleared upon valid DOD measurement for QMAX update or RELAX exit.
            "RSVD8": ((os>>12) & 1),   # Battery Low bit that indicates a low battery voltage condition. Refer to the data flash Cell BL parameters for threshold settings. True when set
            "RSVD9": ((os>>11) & 1),   # Charge Inhibit: unable to begin charging. Refer to the data flash [Charge Inhibit Temp Low, Charge Inhibit Temp High] parameters for threshold settings. True when set
            "DODEOC": ((os>>10) & 1),  # DOD at End-of-Charge is updated.
            "DTRC": ((os>>9) & 1),     # Indicates RemainingCapacity() has been changed due to change in temperature.
            "RSVD10": ((os>>8) & 1),    # Instruction Flash Checksum Failure
            "RSVD_BYTE": (os & 0xFF),  # Reserved Byte 
        })        
        return _od2t(self._gauging_status)

    
    #----------------------------------------------------------------------------------------------


    def _decode_safety_status_or_alert(self, buf: bytearray| bytes, hexi: bool | str | None = None) -> OrderedDict:        
        os = unpack_from("<L", buf.ljust(4, b'\x00'), 0)[0]
        d_0 = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            #"value": os,
        })
        os = unpack_from("<B", buf, 0)[0]
        d_A = OrderedDict({
            # data come little endian
            "SCD": ((os>>7) & 1),  #
            "OCD2": ((os>>6) & 1),  #
            "OCD1": ((os>>5) & 1),  #
            "OCC": ((os>>4) & 1),  #
            "COV": ((os>>3) & 1),  #
            "CUV": ((os>>2) & 1),  #
            "RSVD1": ((os>>1) & 1),  # Reserved. Do not use.
            "RSVD2": ((os>>0) & 1),  # Reserved. Do not use.
        })
        os = unpack_from("<B", buf, 1)[0]
        d_B = OrderedDict({
            # data come little endian
            "OTF": ((os>>7) & 1),  #
            "OTINT": ((os>>6) & 1),  #
            "OTD": ((os>>5) & 1),  #
            "OTC": ((os>>4) & 1),  #
            "RSVD3": ((os>>3) & 1),  # Reserved. Do not use.
            "UTINT": ((os>>2) & 1),  #
            "UTD": ((os>>1) & 1),  #
            "UTC": ((os>>0) & 1),  #
        })
        os = unpack_from("<B", buf, 2)[0]
        d_C = OrderedDict({
            # data come little endian
            "OCD3": ((os>>7) & 1),  #
            "SCDL": ((os>>6) & 1),  #
            "OCDL": ((os>>5) & 1),  #
            "COVL": ((os>>4) & 1),  #
            "RSVD4": ((os>>3) & 1),  # Reserved. Do not use.
            "PTO": ((os>>2) & 1),  #
            "HWDF": ((os>>1) & 1),  #
            "RSVD5": ((os>>0) & 1),  # Reserved. Do not use.
        })
        # combine the ordered dicts
        d = d_0 | d_A | d_B | d_C
        return d

    # these are functions to provide AFE specific bitflags
    def safety_alert(self, hexi: bool | str | None = None) -> tuple:
        buf = self._read_manufacturer_block(0x0050)
        self._safety_alert = self._decode_safety_status_or_alert(buf, hexi=hexi)
        return _od2t(self._safety_alert)

    def safety_status(self, hexi: bool | str | None = None) -> tuple:
        buf = self._read_manufacturer_block(0x0051)
        self._safety_status = self._decode_safety_status_or_alert(buf, hexi=hexi)
        return _od2t(self._safety_status)


    #----------------------------------------------------------------------------------------------

    def _decode_pf_status_or_alert(self, buf: bytearray| bytes, hexi: bool | str | None = None) -> OrderedDict:        
        os = unpack_from("<L", buf, 0)[0]
        d_0 = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            #"value": os,
        })
        os = unpack_from("<B", buf, 0)[0]
        d_A = OrderedDict({
            # data come little endian
            "CUDEP": ((os>>7) & 1),
            "SOTF": ((os>>6) & 1),
            "RSVD0": ((os>>5) & 1),  # Reserved. Do not use.
            "SOT": ((os>>4) & 1),
            "SOCD": ((os>>3) & 1),
            "SOCC": ((os>>2) & 1),
            "SOV": ((os>>1) & 1),
            "SUV": ((os>>0) & 1),
        })
        os = unpack_from("<B", buf, 1)[0]
        d_B = OrderedDict({
            # data come little endian
            "SCDL": ((os>>7) & 1),
            "RSVD1": ((os>>6) & 1),
            "RSVD2": ((os>>5) & 1),
            "VIMA": ((os>>4) & 1),
            "VIMR": ((os>>3) & 1),
            "2LVL": ((os>>2) & 1),
            "DFETF": ((os>>1) & 1),
            "CFETF": ((os>>0) & 1),
        })
        os = unpack_from("<B", buf, 2)[0]
        d_C = OrderedDict({
            # data come little endian
            "CMDF": ((os>>7) & 1),
            "HWMX": ((os>>6) & 1),
            "VSSF": ((os>>5) & 1),
            "VREF": ((os>>4) & 1),
            "LFOF": ((os>>3) & 1),
            "IRMF": ((os>>2) & 1),
            "DRMF": ((os>>1) & 1),
            "OTPF": ((os>>0) & 1),
        })
        os = unpack_from("<B", buf, 3)[0]
        d_D = OrderedDict({
            # data come little endian
            "RSVD3": ((os>>7) & 1),
            "RSVD4": ((os>>6) & 1),
            "RSVD5": ((os>>5) & 1),
            "RSVD6": ((os>>4) & 1),
            "RSVD7": ((os>>3) & 1),
            "RSVD8": ((os>>2) & 1),
            "RSVD9": ((os>>1) & 1),
            "TOSF": ((os>>0) & 1),
        })

        # combine the ordered dicts
        d = d_0 | d_A | d_B | d_C | d_D
        return d

    def pf_alert(self, hexi: bool | str | None = None) -> tuple:
        buf = self._read_manufacturer_block(0x0052)
        self._pf_alert = self._decode_pf_status_or_alert(buf, hexi=hexi)
        return _od2t(self._safety_alert)

    
    def pf_status(self,hexi: bool | str | None = None) -> tuple:
        buf = self._read_manufacturer_block(0x0053)
        self._pf_status = self._decode_pf_status_or_alert(buf, hexi=hexi)
        return _od2t(self._pf_status)
    
  
    #----------------------------------------------------------------------------------------------
  

    def check_no_errors(self) -> bool:
        """Checks Safety Status and Permanent Fail Status.

        Returns:
            bool: True - no errors, False - errors detected.
        """
        no_errs = True
        # Safety status
        buf =  self._read_manufacturer_block(0x0051)
        if not all(v == 0 for v in buf):
            no_errs = False
        # PF status
        buf =  self._read_manufacturer_block(0x0053)
        if not all(v == 0 for v in buf):            
            no_errs = False
        return no_errs

    
    #----------------------------------------------------------------------------------------------

    def reset_device(self) -> bool:
        ok1 = self.afe_reset()
        ok2 = self.gg_reset()
        # ... ? more ? ...
        return ok1 and ok2


    def reset_errors(self) -> bool:
        return self.afe_reset()
        

    #----------------------------------------------------------------------------------------------
  

    def toggle_chg_fet(self):
        raise NotImplementedError("toggle_chg_fet() not implemented yet for Petalite chipset.")
        self._write_manufacturer_block(0x001f, bytes([0x01]))


    def toggle_dsg_fet(self):
        raise NotImplementedError("toggle_dsg_fet() not implemented yet for Petalite chipset.")
        self._write_manufacturer_block(0x0020, bytes([0x01]))


    def toggle_fuse(self):
        raise NotImplementedError("toggle_fuse() not implemented yet for Petalite chipset.")
        self._write_manufacturer_block(0x001d, bytes([0x01]))


    def toggle_led(self):
        raise NotImplementedError("toggle_led() not implemented yet for Petalite chipset.")
        self._write_manufacturer_block(0x002d, bytes([0x01]))


    def set_led_onoff(self, color: int) -> bool:
        _cmap = [
            (0,0,0),      # off
            (0,0,255),    # blue
            (0,255,0),    # green
            (255,0,0),    # red
        ]
        buf = b''.join([bytes(_cmap[color]) for _ in range(4)])
        self._write_manufacturer_block(0x20d8, buf)
        return True
        #return super().set_led_onoff(enable)


    def is_led_on(self) -> bool:
        buf = self._read_manufacturer_block(0x20d8)
        # check if any of the RGB values is non-zero
        for i in range(0, len(buf), 3):
            r = buf[i]
            g = buf[i+1]
            b = buf[i+2]
            if (r != 0) or (g != 0) or (b != 0):
                return True
        return False
    

    #----------------------------------------------------------------------------------------------

    
    def shutdown(self) -> None:
        """Sets the battery into shioping mode.
        If you want to check the effect, use shipping_mode() function instead.
        """
        super().shutdown()


    def shipping_mode(self, ship_delay: float = 2.0) -> bool:
        return super().shipping_mode(ship_delay)


    #----------------------------------------------------------------------------------------------


    # specials for chipset control
    def afe_reset(self) -> bool:
        #self.manufacturer_access = 0x0012
        self.manufacturer_block_access = 0x0012
       

    def gg_reset(self) -> bool:
        #self.manufacturer_access = 0x0041
        self.manufacturer_block_access = 0x0041  # uses the TI reset command code
       


    #----------------------------------------------------------------------------------------------


    def enable_impedance_track(self) -> bool:
        """Send IT enable to the GG chip.

        Returns:
            bool: _description_
        """
        
        self.manufacturer_block_access = 0x0021
        
    
    def lifetime_data(self, hexi = None):
        # 0x0060
        raise NotImplementedError("lifetime_data() not implemented yet for Petalite chipset.")


    def reset_lifetime_data_collection(self) -> bool:
        return self.writeWord(0xC3, 0x6666)  # Reset lifetime logging


    def is_lifetime_logging_enabled(self) -> bool:  
        lt_logging, ok = self.readWord(0xC3)  # read back lifetime logging status
        return (ok and (lt_logging != 0))
    

    #----------------------------------------------------------------------------------------------

    # --- SmartBattery forwards for Teststand ---

    def manufacturer_access_func(self):
        return super().manufacturer_access_func()
    
    def manufacturer_data_func(self):
        return super().manufacturer_data_func()


    def battery_status(self):
        return super().battery_status()

    def battery_mode(self):
        return super().battery_mode()

    def battery_mode(self):
        return super().battery_mode()

    def voltage(self):
        return super().voltage()
    
    def current(self):
        return super().current()

    def temperature(self) -> tuple:
        return super().temperature() 
    
    def relative_state_of_charge(self) -> tuple:
        return super().relative_state_of_charge()
    
    def soc(self) -> tuple:
        return super().soc()
    
    def full_charge_capacity(self) -> tuple:
        return super().full_charge_capacity()

    def soh(self) -> tuple:
        return super().soh()

    def remaining_capacity(self) -> tuple:
        return super().remaining_capacity()

    def serial_number(self):
        return super().serial_number()

    def manufacture_date(self):
        return super().manufacture_date()
    
    def serial_number(self):
        return super().serial_number()
    
    def device_name(self):
        return super().device_name()
    

    def cell1_voltage(self):
        return super().cell1_voltage()

    def cell2_voltage(self):
        return super().cell2_voltage()
    
    def cell3_voltage(self):
        return super().cell3_voltage()

    def cell4_voltage(self):
        return super().cell4_voltage()

    def cell5_voltage(self):
        return super().cell5_voltage()  
        
    def cell6_voltage(self):
        return super().cell6_voltage()

    def cell7_voltage(self):
        return super().cell7_voltage()


    def get_current(self):
        return super().get_current()

    def get_rsoc(self):
        return super().get_rsoc()


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ### Initialize the logging
    #logger_init(filename_base=None)  ## init root logger
    #_log = getLogger(__name__, DEBUG)

    print("NO TESTS: ", __file__)

    #
    # to test please setup a "test_xxx.py" module !
    #

# END OF FILE
