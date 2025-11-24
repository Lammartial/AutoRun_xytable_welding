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
from binascii import unhexlify
from os import urandom
from hashlib import sha1
from itertools import chain
from struct import unpack_from, iter_unpack
from collections import OrderedDict
#from rrc.battery_errors import BatteryError
from rrc.smbus import BusMaster
from rrc.smartbattery import Cmd
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
        return super().is_sealed(refresh=refresh)


    def seal(self) -> bool:
        """Seals the battery to disable write access to critical parameters.

        Returns:
            bool: True if successful
        """
        # Petalite uses same seal command as BQ40Z50
        return super().seal()


    def enable_full_access(self) -> bool:
        return super().enable_full_access()
    

    #---HELPER FOR PRODUCTION----------------------------------------------------------------------


    def __manufacturing_dastatus1(self, hexi: bool | str | None = None) -> tuple:
        """Read DAStatus1 and return the registers as they come.

        Raises:
            BatteryError: _description_

        Returns:
            OrderedDict: _description_
        """

        for _retry in range(5):
            try:
                buf = self.read_manufacturer_block(command=0x0071, length=32)
                self._manufacturing_dastatus1 = OrderedDict({
                    "block": self._maybe_hexlify(buf, hexi),
                    # data come little endian
                    "cell_voltage_1": unpack_from("<H", buf,  0)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_2": unpack_from("<H", buf,  2)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_3": unpack_from("<H", buf,  4)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_4": unpack_from("<H", buf,  6)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_5": unpack_from("<H", buf,  8)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_6": unpack_from("<H", buf, 10)[0] * 1e-3,  # mV, unsigned short, little endian
                    "cell_voltage_7": unpack_from("<H", buf, 12)[0] * 1e-3,  # mV, unsigned short, little endian
                    #
                    # what is with the rest of the data?
                    #
                })
                if _retry > 1:  # force two times read
                    return _od2t(self._manufacturing_dastatus1)  # Teststand interface
                sleep(0.005)
            except Exception as ex:
                sleep(0.020)
                _last_exception = ex
        raise Exception(f"DASTATUS 1: {_last_exception}")  # pass throuhg the last exeption



    def manufacturing_dastatus(self) -> Tuple[List[int], List[int]]:
        """Reads all DAStatus 1 to 3

        Args:
            hexi (bool | str | None, optional): _description_. Defaults to None.

        Returns:
            Tuple[List[int], List[int]]: _description_
        """

        buf1 = self.read_manufacturer_block(command=0x0071, length=32)  # DASTATUS1
        buf2 = self.read_manufacturer_block(command=0x0072, length=32)  # DASTATUS2
        buf3 = self.read_manufacturer_block(command=0x0073, length=32)  # DASTATUS3
        #buf4 = self.read_manufacturer_block(command=0x0074, length=32)  # DASTATUS4

        _fmt = "<L"  # unsigned long, 4 bytes
        all_items = [n[0] for n in list(chain.from_iterable([iter_unpack(_fmt, bytes(buffer)) for buffer in [buf1, buf2, buf3]]))]
        self.cell_voltage_counts = all_items[::2]  # every 2nd is a voltage count, starting from first element
        self.cell_current_counts = all_items[1::2]  # every 2nd is a current count, starting from 2nd element
        #print(self.cell_voltage_counts)
        #print(self.cell_current_counts)
        return self.cell_voltage_counts, self.cell_current_counts




    def shutdown(self) -> None:
        super().shutdown()
    

    def read_pcba_udi_block(self) -> str:
        """Reads the PCBA UDI block from the battery.

        Note: This uses Manufacturer Block Access 0x44.

        Returns:
            bytes: PCBA UDI data block
        """

        # Petalite uses same PCBA UDI command as BQ40Z50
        return super().read_pcba_udi_block()
    

    def read_serial_number_block(self) -> str:
        return super().read_serial_number_block()


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
