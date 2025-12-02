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

    def is_sealed(self, refresh: bool = True) -> bool:
        """Checks if the battery is sealed to disable write access to critical parameters.

        Returns:
            bool: True if sealed
        """
        # Petalite uses same seal command as BQ40Z50
        #return super().is_sealed(refresh=refresh)
        return False  # Peta-Patch: always unsealed


    def seal(self) -> bool:
        """Seals the battery to disable write access to critical parameters.

        Returns:
            bool: True if successful
        """
        # Petalite uses same seal command as BQ40Z50
        return super().seal()


    def enable_full_access(self) -> bool:
        #return super().enable_full_access()
        return True  # Peta-Patch: always unsealed
    

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


    def write_manufacturer_block(self, command: int, data: bytearray | bytes) -> None:
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
        self.manufacturer_block_access = buf


    def read_manufacturer_block(self, command: int, length: int | None, max_retries: int = 5) -> bytearray:
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
            length = int(length)
        for i in range(int(max_retries)):
            #self.manufacturer_access = command  # write word to 0x00
            # self.manufacturer_access = ((command >> 8) & 0xff) | ((command << 8) & 0xff00)  # swap enidaness
            # res, ok = self.bus.readBytes(self.address, 0x23, length, use_pec=False)
            # print(list(res))
            self.manufacturer_block_access = command
            #res, ok = self.bus.readBytes(self.address, 0x44, length, use_pec=False)
            res = self.manufacturer_block_access  # read from 0x44
            #print(list(res))  # DEBUG          
            rcv_command = unpack("<H", res[:2])[0]
            res = res[2:]  # slice the command
            # if the expected length may variy you need to pass None to length
            if (rcv_command == command) and (((length is not None) and (len(res) == length)) or (length is None)):
                return res
        raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(res)}, {len(res)}")


    def manufacturing_daqstatus1(self, hexi: bool | str | None = None) -> tuple:
        """Read DAQ Status 1 and return the registers as they come.

        Raises:
            BatteryError: _description_

        Returns:
            OrderedDict: _description_
        """

        for _retry in range(5):
            try:
                buf = self.read_manufacturer_block(command=0x20d6, length=None)
                self._manufacturing_daqstatus1 = OrderedDict({
                    "block": self._maybe_hexlify(buf, hexi),
                    # data come little endian
                    "cell_voltage_1": unpack_from("<H", buf, 0)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_2": unpack_from("<H", buf, 2)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_3": unpack_from("<H", buf, 4)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_4": unpack_from("<H", buf, 6)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_5": unpack_from("<H", buf, 8)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_6": unpack_from("<H", buf, 10)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_7": unpack_from("<H", buf, 12)[0] * 1e-3,  # mV, unsigned short, little endian
                    "afe_tos_voltage":    unpack_from("<H", buf, 14)[0] * 1e-3,  # mV, unsigned short, little endian
                    "afe_pack_voltage":   unpack_from("<H", buf, 16)[0] * 1e-3,  # mV, unsigned short, little endian
                    "afe_led_pin_voltage": unpack_from("<H", buf, 18)[0] * 1e-3,  # mV, unsigned short, little endian
                    "gg_voltage": unpack_from("<H", buf, 20)[0] * 1e-3,  # mV, unsigned short, little endian
                    "afe_cc2_current": unpack_from("<h", buf, 22)[0] * 1e-3,  # mA, signed short, little endian
                    "afe_cc3_current": unpack_from("<h", buf, 24)[0] * 1e-3,  # mA, signed short, little endian
                    "gg_current":   unpack_from("<h", buf, 26)[0] * 1e-3,  # mA, signed short, little endian
                    # 2 words reserve
                })
                return _od2t(self._manufacturing_daqstatus1)  # Teststand interface
            except Exception as ex:
                sleep(0.020)
                _last_exception = ex
        raise Exception(f"DAQSTATUS 1: {_last_exception}")  # pass throuhg the last exeption


    def manufacturing_daqstatus2(self, celsius: bool = True, hexi: bool | str | None = None) -> tuple:
        for _retry in range(5):
            try:
                buf = self.read_manufacturer_block(command=0x20d7, length=None)
                self._manufacturing_daqstatus2 = OrderedDict({
                    "block": self._maybe_hexlify(buf, hexi),
                    # data come little endian
                    "ts1_temperature": unpack_from("<H", buf, 0)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
                    "ts3_temperature": unpack_from("<H", buf, 2)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
                    "afe_hdq_temperature": unpack_from("<H", buf, 4)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
                    "afe_dchg_temperature": unpack_from("<H", buf, 6)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian                    
                    "afe_ddsg_temperature": unpack_from("<H", buf, 8)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
                    "gg_temperature":    unpack_from("<H", buf, 10)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
                    # 10 words reserve                    
                })
                return _od2t(self._manufacturing_daqstatus2)  # Teststand interface
            except Exception as ex:
                sleep(0.020)
                _last_exception = ex
        raise Exception(f"DAQSTATUS 2: {_last_exception}")  # pass throuhg the last exeption


    def setup_rtc(self) -> bool:
        now = dt.now()
        print(now)
        buf = bytes([ 
                    ((now.year - 2000) & 0xFF), (now.month & 0xFF), (now.day & 0xFF),
                    (now.hour & 0xFF), (now.minute & 0xFF), (now.second& 0xFF)
                    ])
        print(hexlify(buf))   # DEBUG
        return self.write_manufacturer_block(0x20d9, buf)
        

    def read_rtc(self) -> Tuple[dt, str]:
        buf = self.read_manufacturer_block(0x20d9, None)
        _fmt = "<B"
        year = unpack_from(_fmt, buf, offset=0)[0] - 41 + 2025
        month = unpack_from(_fmt, buf, offset=1)[0]
        day = unpack_from(_fmt, buf, offset=2)[0]
        hour = unpack_from(_fmt, buf, offset=3)[0]
        minute = unpack_from(_fmt, buf, offset=4)[0]
        second = unpack_from(_fmt, buf, offset=5)[0]
        print("BUG WARNING IN RTC YEAR! Offset of 41 ??") # DEBUG       
        d = dt(year, month, day, hour, minute, second)
        return d, d.isoformat(sep=" ")


    def check_rtc_against_systemtime(self) -> float:
        now = dt.now()
        rtc, rtc_str = self.read_rtc()
        _diff = now-rtc
        return _diff.total_seconds()





    def shutdown(self) -> None:
        super().shutdown()
    

    def read_pcba_udi_block(self) -> str:
        """Reads the PCBA UDI block from the battery.

        Note: This uses Manufacturer Block Access 0x44.

        Returns:
            bytes: PCBA UDI data block
        """

        #return super().read_pcba_udi_block()
        # self.manufacturer_block_access = 0xXXXX
        # block = self.manufacturer_block_access
        # udi = block.decode()
        udi = "0PCBA01234567891"
        return udi
        


    
    def read_serial_number_block(self) -> str:
        """
        Reads serial number from the Manufacturer info block.
        Addresses: xx 

        Returns:
            str: serial number block
        """
        
        # self.manufacturer_block_access = 0xXXXX
        # block = self.manufacturer_block_access
        # serial = block.decode()
        serial = "0123456789012345"  # Peta-Patch: dummy serial
        return serial

    def write_serial_number_block(self, sn: str) -> bool:
        return super().write_serial_number_block(sn)


    def set_pack_sn(self, sn: str) -> bool:
        return super().set_pack_sn(sn)
    
    def set_manufacturer_date(self):
        """Writes the current date to the battery as manufacture date.

        Returns:
            bool: True if successful
        """
        return super().set_manufacturer_date()


    def set_led_onoff(self, enable: bool) -> bool:
        return super().set_led_onoff(enable)

    def is_led_on(self) -> bool:
        return super().is_led_on()


    def set_lifetime_data_collection(self, enable: bool) -> bool:
        return super().set_lifetime_data_collection(enable)


    def shipping_mode(self, ship_delay: float = 2.0) -> bool:
        return super().shipping_mode(ship_delay)



    # def check_no_errors(self) -> bool:
    #     return super().check_no_errors()
    


    # SmartBattery forwards for Teststand

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
