"""Battery BMS-IC specific commands (called chipset)

   Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904
from typing import Tuple
import errno
#from battery.smartbattery import Battery
from time import sleep, monotonic_ns
from binascii import hexlify
from struct import pack, unpack, unpack_from
#from uos import urandom
#from uhashlib import sha1
from collections import OrderedDict
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from humanfriendly import format_size
from rrc.bincopy import BinFile
from rrc.battery_errors import BatteryError, BatterySecurityError
from rrc.smbus import BusMaster
from rrc.smartbattery import Cmd
from rrc.chipsets.bq import ChipsetTexasInstruments
import struct
from datetime import datetime
import numpy as np

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


###################################################################################################
#
#  BQ 40 Z 50
#
###################################################################################################

# -R1-
class BQ40Z50R1(ChipsetTexasInstruments):

    def __init__(self, smbus: BusMaster, slvAddress: int = 0x0b, pec: bool = False):
        # Note: explicitely replicate the parameters here for having
        # option in teststand to change them on call
        super().__init__(smbus, slvAddress=slvAddress, pec=pec)
        self._firmware_version = None
        self._operation_status = None  # shadow copy of operation_status() read to avoid redundant reads for seal/unseal checks
        self._manufacturing_status = None  # shadow copy of manufacturing_status()
        self._ccadc_cal = None  # shadow copy

    def __str__(self) -> str:
        return f"SmartBattery with BQ40Z50 chipset at 0x{self.address} on {str(self.bus)}"

    def __repr__(self) -> str:
        return f"BQ40Z50R1({repr(self.bus)}, slvAddress={self.address}, pec={self.pec})"

    #----------------------------------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Returns the battery chipset name in lower case."""
        return "bq40z50r1"

    def autodetect(self) -> bool:
        """Identifies the presence of a chipset of this type.

           We need to use some kind of SIGNATURE functions or check known responses.
           This differs from chipset to chipset.

        """
        #print(self.name)
        yesno=False
        try:
            self.operation_status() # if other chipset, this read will raise exception
            dev = self.device_type()
            self.firmware_version()            
            if dev == 0x4500: # RRC2054xx, RRC21xx
                if self._firmware_version["version"] & 0xff00 == 0x0100: # RRC2054, RRC2054-2, ...
                    yesno=True
        except BatteryError:
            # not the right chipset
            pass
        except OSError as ex:
            if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                # -> forward this exception
                raise ex
        return yesno

    def device_type(self) -> int:
        """Returns the BQ IC part number."""
        self.manufacturer_access = 0x0001
        buf = self.manufacturer_data
        value = unpack("<H", buf)[0]  # data come litte endian
        return value

    def firmware_version(self, hexi: bool | str | None = None) -> tuple:
        """Returns the chip firmware version."""
        _log = getLogger(__name__, 2)
        self.manufacturer_access = 0x0002
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 11):
            raise BatteryError(f"Readings implausible: Unexpected return value {type(buf)}, {len(buf)}")
        self._firmware_version = OrderedDict({
            "value": self._maybe_hexlify(buf, hexi),
            # data come big endian - they SUCK!
            "device_number": unpack_from(">H", buf, 0)[0],
            "version":       unpack_from(">H", buf, 2)[0],
            "build_number":  unpack_from(">H", buf, 4)[0],
            "firmware_type": unpack_from(">B", buf, 6)[0],
            "impedance_track_version": unpack_from(">H", buf, 7)[0],
            "reserved1":     unpack_from(">B", buf, 9)[0],
            "reserved2":     unpack_from(">B", buf, 10)[0],
        })
        _log.debug(f"FIRMWARE_VERSION: {self._firmware_version}")
        return _od2t(self._firmware_version)

    def hardware_version(self) -> int:
        """Returns the chip hardware version."""
        self.manufacturer_access = 0x0003
        buf = self.manufacturer_data
        value = unpack("<H", buf)[0]  # data come litte endian
        return value

    def chemistry_id(self) -> int:
        """Returns the OCV table chemistry ID of the battery."""
        self.manufacturer_access = 0x0006
        buf = self.manufacturer_data
        value = unpack("<H", buf)[0]  # data come litte endian
        return value

    def manufacturer_status(self) -> int:
        raise NotImplementedError("manufacturer_status() only available for bq20z65.")


    # def _operation_status_int(self) -> int:
    #     """This command returns the OperationStatus() flags only as int.
    #     It is intended for use in other functions here.
    #     """
    #     self.manufacturer_access = 0x0054
    #     buf = self.manufacturer_data
    #     return int.from_bytes(buf, "little")

    def operation_status(self, hexi: bool | str | None = None) -> tuple:
        """This command returns the OperationStatus() flags.

        SIGNATURE function: We can use this function to identify the chipset type,
                            by checking the Exception()

        Args:
            hexi (bool | str | None, optional): activates a conversion of data into "blocks"
                if not None or bool and False. If bool and True "blocks" contains ascii hex nibbles.
                Defaults to None.

        Returns:
            tuple: (
                block: bytes or str with hex as ascii string, depending on hexi
                value: the bitflag register as singned 64bit integer
                bitflags: 0 or 1 values in descending bit order bit29 ... bit0
            )
        """

        self.manufacturer_access = 0x0054
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 4):
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}, {buf}")
        #os = int.from_bytes(buf, "little")
        os = unpack("<L", buf)[0]
        self._operation_status = OrderedDict({
            "block"     : self._maybe_hexlify(buf, hexi),
            "value"     : os,
            "emshut"    : ((os>>29) & 1), # (os & (1<<29)) != 0,
            "cb"        : ((os>>28) & 1), # (os & (1<<28)) != 0,
            "slpcc"     : ((os>>27) & 1), # (os & (1<<27)) != 0,
            "slpad"     : ((os>>26) & 1), # (os & (1<<26)) != 0,
            "smbcal"    : ((os>>25) & 1), # (os & (1<<25)) != 0,
            "init"      : ((os>>24) & 1), # (os & (1<<24)) != 0,
            "sleepm"    : ((os>>23) & 1), # (os & (1<<23)) != 0,
            "xl"        : ((os>>22) & 1), # (os & (1<<22)) != 0,
            "cal_offset": ((os>>21) & 1), # (os & (1<<21)) != 0,
            "cal"       : ((os>>20) & 1), # (os & (1<<20)) != 0,
            "autocalm"  : ((os>>19) & 1), # (os & (1<<19)) != 0,
            "auth"      : ((os>>18) & 1), # (os & (1<<18)) != 0,
            "led"       : ((os>>17) & 1), # (os & (1<<17)) != 0,
            "sdm"       : ((os>>16) & 1), # (os & (1<<16)) != 0,
            "sleep"     : ((os>>15) & 1), # (os & (1<<15)) != 0,
            "xchg"      : ((os>>14) & 1), # (os & (1<<14)) != 0,
            "xdsg"      : ((os>>13) & 1), # (os & (1<<13)) != 0,
            "pf"        : ((os>>12) & 1), # (os & (1<<12)) != 0,
            "ss"        : ((os>>11) & 1), # (os & (1<<11)) != 0,
            "sdv"       : ((os>>10) & 1), # (os & (1<<10)) != 0,
            "sec1"      : ((os>>9) & 1), # (os & (1<<9)) != 0,
            "sec0"      : ((os>>8) & 1), # (os & (1<<8)) != 0,
            "sec"       : (os>>8) & 0x03,
            "btp_int"   : ((os>>7) & 1), # (os & (1<<7)) != 0,
            "fuse"      : ((os>>5) & 1), # (os & (1<<5)) != 0,
            "pchg"      : ((os>>3) & 1), # (os & (1<<3)) != 0,
            "chg"       : ((os>>2) & 1), # (os & (1<<2)) != 0,
            "dsg"       : ((os>>1) & 1), # (os & (1<<1)) != 0,
            "pres"      : ((os>>0) & 1), # (os & (1<<0)) != 0
        })
        return _od2t(self._operation_status)

    # def operation_status_ts(self) -> str:
    #     self.operation_status(True)
    #     return self._operation_status["block"]


    def manufacturing_status(self, hexi: bool | str | None = None) -> tuple:
        """This command returns the ManufacturingStatus() flags.

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
        self.manufacturer_access = 0x0057
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 2):
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}")
        #os = int.from_bytes(buf, "little")
        os = unpack("<H", buf)[0]
        self._manufacturing_status = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            "value": os,
            # bitflags
            "cal_test":  ((os>>15) & 1),
            "lt_test":   ((os>>14) & 1),
            #"reserved4": ((os>>13) & 1),
            #"reserved3": ((os>>12) & 1),
            #"reserved2": ((os>>11) & 1),
            #"reserved1": ((os>>10) & 1),
            "led_en":    ((os>>9) & 1),
            "fuse_en":   ((os>>8) & 1),
            "bbr_en":    ((os>>7) & 1),
            "pf_en":     ((os>>6) & 1),
            "lf_en":     ((os>>5) & 1),
            "fet_en":    ((os>>4) & 1),
            "gauge_en":  ((os>>3) & 1),
            "dsg_en":    ((os>>2) & 1),
            "chg_en":    ((os>>1) & 1),
            "pchg_en":   ((os>>0) & 1),
        })
        return _od2t(self._manufacturing_status)

    def is_sealed(self, refresh: bool = False) -> bool:
        """check if batetry is sealed

        Args:
            refresh (bool, optional): if True, the operation_status shadow will be read fresh from battery before analyze its flags. Defaults to False.

        Returns:
            bool: True, if sealed False otherwise
        """
        if refresh or self._operation_status is None: self.operation_status()
        # using shadow copy to avoid bus access
        #print("s_SEC:", self._operation_status["sec"])
        return self._operation_status["sec"] == 0x03 # using shadow copy to avoid bus access


    def is_unsealed(self, check_fullaccess: bool = False, refresh: bool = False) -> bool:
        """Checks if the battery is sealed.

        NOTE: Something is wrong in the manual.
              Reality: SEC = 10 -> UNSEAL, SEC = 01 -> FULL_ACCESS
              Manual says 10 -> FULL_ACCESS, SEC = 01 -> UNSEAL

           Args:
             check_fullaccess (bool): if check_fullaccess is true, it also checks if battery is in full access mode.
             refresh (bool): if True, the operation_status shadow will be read fresh from battery before analyze its flags

           Returns
              (bool): true of the device is NOT sealed if check_fullaccess is true,
                      else only true if battery is unsealed and in full access mode.
        """
        if refresh or self._operation_status is None: self.operation_status()
        # using shadow copy to avoid bus access
        #print("u_SEC:", self._operation_status["sec"])
        if check_fullaccess:
            return (int(self._operation_status["sec"]) == 1) # full access
        return (int(self._operation_status["sec"]) in [1, 2]) # unsealed OR full access

    #---UNSEALED HELPER FOR PRODUCTION-------------------------------------------------------------

    # ...

    def enable_full_access(self) -> bool:
        #
        # no encrypted keys here!
        #
        return self.unseal(0x8D21FAC3, 0x63DB2CE4)  # low-word goes first to battery

    
    def wait_for_operation_status_flag(self, os_key: str, state: bool, retries: int = 20, pause_on_retry: float = 0.1) -> bool:
        """Wait for flags on operation_status()."""
        retries = int(retries)
        while (retries >= 0):
            try:
                self.operation_status()  # => update the self._operation_status attribute
                if bool(self._operation_status[os_key]) == state:
                    break                                                           
                sleep(pause_on_retry)  
            except OSError as ex:
                sleep(pause_on_retry)
            finally:
                retries -= 1
        return bool(self._operation_status[os_key]) == state


    def lifetime_datablock(self, hexi: bool | str | None = None):
        """Compatibility function: reading just first block of lifetimedata for use e.g. in production.

        Returns:
            dict: decoded lifetime data of block 1 according the datasheet
        """
        b1 = self.read_manufacturer_block(command=0x0060, length=32)
        return _od2t(OrderedDict({
            "block": self._maybe_hexlify(b1, hexi), # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
            # decode block 1
            "cell1_vmax":          unpack_from("<H", b1, 0)[0]*1e-3, # mV, unsigned short, little endian
            "cell2_vmax":          unpack_from("<H", b1, 2)[0]*1e-3, # mV, unsigned short, little endian
            "cell3_vmax":          unpack_from("<H", b1, 4)[0]*1e-3, # mV, unsigned short, little endian
            "cell4_vmax":          unpack_from("<H", b1, 6)[0]*1e-3, # mV, unsigned short, little endian
            "cell1_vmin":          unpack_from("<H", b1, 8)[0]*1e-3, # mV, unsigned short, little endian
            "cell2_vmin":          unpack_from("<H", b1, 10)[0]*1e-3, # mV, unsigned short, little endian
            "cell3_vmin":          unpack_from("<H", b1, 12)[0]*1e-3, # mV, unsigned short, little endian
            "cell4_vmin":          unpack_from("<H", b1, 14)[0]*1e-3, # mV, unsigned short, little endian
            "max_delta_v_cell":    unpack_from("<H", b1, 16)[0]*1e-3, # mV, unsigned short, little endian
            "max_i_charge":        unpack_from("<h", b1, 18)[0]*1e-3, # mA, signed short, little endian
            "max_i_discharge":     unpack_from("<h", b1, 20)[0]*1e-3, # mA, signed short, little endian
            "max_avg_i_discharge": unpack_from("<h", b1, 22)[0]*1e-3, # mA, signed short, little endian
            "max_avg_p_discharge": unpack_from("<h", b1, 24)[0]*1e-2, # 10mW signed short, little endian
            "max_cell_temp":       unpack_from("<b", b1, 26)[0]*1e-0, # °C, signed char, little endian
            "min_cell_temp":       unpack_from("<b", b1, 27)[0]*1e-0, # °C, signed char, little endian
            "max_delta_cell_temp": unpack_from("<b", b1, 28)[0]*1e-0, # °C, signed char, little endian
            "max_temp_int_sensor": unpack_from("<b", b1, 29)[0]*1e-0, # °C, signed char, little endian
            "min_temp_int_sensor": unpack_from("<b", b1, 30)[0]*1e-0, # °C, signed char, little endian
            "min_temp_fet":        unpack_from("<b", b1, 31)[0]*1e-0, # °C, signed char, little endian
        }))

    def lifetime_data(self, hexi: bool | str | None = None) -> tuple:
        """Returns the life time data block (blocks 1 - 5) as decoded dict.

        Note: from datasheet
              ManufacturerBlockAccess() provides a method of reading and writing data in the
              Manufacturer Access System (MAC). This block MAC access method is a new standard
              for the bq40zxy family. The MAC command is sent via ManufacturerBlockAccess() by
              the SMBus block protocol. The result is returned on ManufacturerBlockAccess()
              via an SMBus block read.
        Returns:
            dict: decoded lifetime data according the datasheet
        """
        d = {}
        h = {}
        lencheck = [32,8,16,32,32] # expected bytes length for each block
        for i in range(0,5): # read 5 blocks
            self.manufacturer_block_access = 0x0060 + i # lifetime data block 1-5 (32 bytes)
            data = self.manufacturer_block_access
            #print("DATA", type(data), data)
            if not isinstance(data, bytearray):
                raise BatteryError("No correct lifetime data from battery for block {}. Got {} expected bytesarray".format(i+1, type(data)))
            else:
                if (len(data) != lencheck[i] + 2): # Note: the "new" manufacturer_block_access returns the written address in the first two byte - we need to add here and slice them later
                    raise BatteryError("No correct lifetime data from battery for block {}. Got {} bytes expected {}".format(i+1, len(data), lencheck[i]))
                # all fine, store the data
                d["blk_"+str(i+1)] = data[2:] # slice the command word which is read back in the two first bytes
                h["blk_"+str(i+1)] = self._maybe_hexlify(data[2:], hexi)
        b1 = d["blk_1"]
        b2 = d["blk_2"]
        b3 = d["blk_3"]
        b4 = d["blk_4"]
        b5 = d["blk_5"]
        #
        # ATTENTION: The provided dict is NOT sorted and the order of keys is NOT as seen here in the code!
        #            To have the dict sorted, the caller can use OrderedDict from collections module:
        #                OrderedDict(sorted(lifetime_data().items()))
        #
        return _od2t(OrderedDict({
            "block": h, # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
            # decode block 1
            "cell1_vmax":          unpack_from("<H", b1, 0)[0]*1e-3, # mV, unsigned short, little endian
            "cell2_vmax":          unpack_from("<H", b1, 2)[0]*1e-3, # mV, unsigned short, little endian
            "cell3_vmax":          unpack_from("<H", b1, 4)[0]*1e-3, # mV, unsigned short, little endian
            "cell4_vmax":          unpack_from("<H", b1, 6)[0]*1e-3, # mV, unsigned short, little endian
            "cell1_vmin":          unpack_from("<H", b1, 8)[0]*1e-3, # mV, unsigned short, little endian
            "cell2_vmin":          unpack_from("<H", b1, 10)[0]*1e-3, # mV, unsigned short, little endian
            "cell3_vmin":          unpack_from("<H", b1, 12)[0]*1e-3, # mV, unsigned short, little endian
            "cell4_vmin":          unpack_from("<H", b1, 14)[0]*1e-3, # mV, unsigned short, little endian
            "max_delta_v_cell":    unpack_from("<H", b1, 16)[0]*1e-3, # mV, unsigned short, little endian
            "max_i_charge":        unpack_from("<h", b1, 18)[0]*1e-3, # mA, signed short, little endian
            "max_i_discharge":     unpack_from("<h", b1, 20)[0]*1e-3, # mA, signed short, little endian
            "max_avg_i_discharge": unpack_from("<h", b1, 22)[0]*1e-3, # mA, signed short, little endian
            "max_avg_p_discharge": unpack_from("<h", b1, 24)[0]*1e-2, # 10mW signed short, little endian
            "max_cell_temp":       unpack_from("<b", b1, 26)[0]*1e-0, # °C, signed char, little endian
            "min_cell_temp":       unpack_from("<b", b1, 27)[0]*1e-0, # °C, signed char, little endian
            "max_delta_cell_temp": unpack_from("<b", b1, 28)[0]*1e-0, # °C, signed char, little endian
            "max_temp_int_sensor": unpack_from("<b", b1, 29)[0]*1e-0, # °C, signed char, little endian
            "min_temp_int_sensor": unpack_from("<b", b1, 30)[0]*1e-0, # °C, signed char, little endian
            "min_temp_fet":        unpack_from("<b", b1, 31)[0]*1e-0, # °C, signed char, little endian
            # decode block 2
            "num_of_shutdowns":      unpack_from("<B", b2, 0)[0]*1e-0, # number, unsigned char, little endian
            "num_of_partial_resets": unpack_from("<B", b2, 1)[0]*1e-0, # number, unsigned char, little endian
            "num_of_full_resets":    unpack_from("<B", b2, 2)[0]*1e-0, # number, unsigned char, little endian
            "num_of_wdt_resets":     unpack_from("<B", b2, 3)[0]*1e-0, # number, unsigned char, little endian
            "cb_time_cell1":         unpack_from("<B", b2, 4)[0]*3600*2, # 2h, unsigned char, little endian
            "cb_time_cell2":         unpack_from("<B", b2, 5)[0]*3600*2, # 2h, unsigned char, little endian
            "cb_time_cell3":         unpack_from("<B", b2, 6)[0]*3600*2, # 2h, unsigned char, little endian
            "cb_time_cell4":         unpack_from("<B", b2, 7)[0]*3600*2, # 2h, unsigned char, little endian
            # decode block 3
            "total_fw_runtime":   unpack_from("<H", b3, 0)[0]*3600*2, # 2h, unsigned short, little endian
            "time_spent_in_ut":   unpack_from("<H", b3, 2)[0]*3600*2, # 2h, unsigned short, little endian
            "time_spent_in_lt":   unpack_from("<H", b3, 4)[0]*3600*2, # 2h, unsigned short, little endian
            "time_spent_in_stl":  unpack_from("<H", b3, 6)[0]*3600*2, # 2h unsigned short, little endian
            "time_spent_in_sth":  unpack_from("<H", b3, 8)[0]*3600*2, # 2h unsigned short, little endian
            "time_spent_in_ht":   unpack_from("<H", b3, 10)[0]*3600*2, # 2h unsigned short, little endian
            "time_spent_in_ot":   unpack_from("<H", b3, 12)[0]*3600*2, # 2h unsigned short, little endian
            # decode block 4
            "num_of_cov_events":  unpack_from("<H", b4, 0)[0], # events, unsigned short, little endian
            "last_cov_event":     unpack_from("<H", b4, 2)[0], # cycles, unsigned short, little endian
            "num_of_cuv_events":  unpack_from("<H", b4, 4)[0], # events, unsigned short, little endian
            "last_cuv_event":     unpack_from("<H", b4, 6)[0], # cycles, unsigned short, little endian
            "num_of_ocd1_events": unpack_from("<H", b4, 8)[0], # events, unsigned short, little endian
            "last_ocd1_event":    unpack_from("<H", b4, 10)[0], # cycles, unsigned short, little endian
            "num_of_ocd2_events": unpack_from("<H", b4, 12)[0], # events, unsigned short, little endian
            "last_ocd2_event":    unpack_from("<H", b4, 14)[0], # cycles, unsigned short, little endian
            "num_of_occ1_events": unpack_from("<H", b4, 16)[0], # events, unsigned short, little endian
            "last_occ1_event":    unpack_from("<H", b4, 18)[0], # cycles, unsigned short, little endian
            "num_of_occ2_events": unpack_from("<H", b4, 20)[0], # events, unsigned short, little endian
            "last_occ2_event":    unpack_from("<H", b4, 22)[0], # cycles, unsigned short, little endian
            "num_of_aold_events": unpack_from("<H", b4, 24)[0], # events, unsigned short, little endian
            "last_aold_event":    unpack_from("<H", b4, 26)[0], # cycles, unsigned short, little endian
            "num_of_ascd_events": unpack_from("<H", b4, 28)[0], # events, unsigned short, little endian
            "last_ascd_event":    unpack_from("<H", b4, 30)[0], # cycles, unsigned short, little endian
            # decode block 5
            "num_of_ascc_events":     unpack_from("<H", b5, 0)[0], # events, unsigned short, little endian
            "last_ascc_event":        unpack_from("<H", b5, 2)[0], # cycles, unsigned short, little endian
            "num_of_otc_events":      unpack_from("<H", b5, 4)[0], # events, unsigned short, little endian
            "last_otc_event":         unpack_from("<H", b5, 6)[0], # cycles, unsigned short, little endian
            "num_of_otd_events":      unpack_from("<H", b5, 8)[0], # events, unsigned short, little endian
            "last_otd_event":         unpack_from("<H", b5, 10)[0], # cycles, unsigned short, little endian
            "num_of_otf_events":      unpack_from("<H", b5, 12)[0], # events, unsigned short, little endian
            "last_otf_event":         unpack_from("<H", b5, 14)[0], # cycles, unsigned short, little endian
            "num_valid_charge_term":  unpack_from("<H", b5, 16)[0], # events, unsigned short, little endian
            "last_valid_charge_term": unpack_from("<H", b5, 18)[0], # cycles, unsigned short, little endian
            "num_of_qmax_updates":    unpack_from("<H", b5, 20)[0], # events, unsigned short, little endian
            "last_qmax_update":       unpack_from("<H", b5, 22)[0], # cycles, unsigned short, little endian
            "num_of_ra_updates":      unpack_from("<H", b5, 24)[0], # events, unsigned short, little endian
            "last_ra_update":         unpack_from("<H", b5, 26)[0], # cycles, unsigned short, little endian
            "num_of_ra_disable":      unpack_from("<H", b5, 28)[0], # events, unsigned short, little endian
            "last_ra_disable":        unpack_from("<H", b5, 30)[0], # cycles, unsigned short, little endian
        }))

    def soh(self) -> tuple:
        self.manufacturer_access = 0x0077
        buf = self.manufacturer_data
        return _od2t(OrderedDict({
            "fcc_ah": unpack_from("<H", buf, 0)[0]*1e-3, # mAh -> Ah (is not in SI but also allowed as unit)
            "fcc_wh": unpack_from("<H", buf, 2)[0]*1e+2, # cWh -> Wh (is not in SI but also allowed as unit)
        }))

    def shipping_mode(self, ship_delay: float = 2.0) -> bool:
        """Enter shipping mode which is equal to shutdown mode but repects different timing of sealed and unsealed modes.

        If sealed, waits ship_delay seconds then checks for another ship_delay seconds time if
        battry is still responsive.

        From Manual:
           After sending this command, the OperationStatus()[SDM] = 1, an internal counter will start,
           the CHG and DSG FETs will be turned off when the counter reaches Ship FET Off Time.
           When the counter reaches Ship Delay time, the device will enter SHUTDOWN mode if no charger present is detected.

           If the device is SEALED, this feature requires the command to be sent twice in a row within 4 seconds (for
           safety purposes).
           If the device is in UNSEALED or FULL ACCESS mode, sending the command the
           second time will cancel the delay and enter shutdown immediately.

        Args:
            ship_delay (float, optional): [description]. Defaults to 5.0.

        Returns:
            True if battery is not responding anymore, False else
        """
        wassealed = self.is_sealed(refresh=True)
        self.shutdown()
        if ship_delay is not None:
            if wassealed: sleep(ship_delay)
            # now check until battery does not respond anymore and wait max ship_delay fro that
            return self.waitForReady(timeout_ms=(ship_delay * 1e+3), invert=True)
        else:
            # no waits requested
            if not self.isReady(): return True
        return False

    def shutdown(self) -> None:
        """Sends a shutdown command to the battery.

        Available in seald AND unsealed but with different delay times. (See Note)

        NOTE: from Datasheet
              If the device is SEALED, this feature requires the command to be sent twice in a row
              within 4 seconds (for safety purposes).
              If the device is in UNSEALED or FULL ACCESS mode, sending the command the
              second time will cancel the delay and enter shutdown immediately.

        Exceptions:
            OSError on smbus communication fail
        """
        self.manufacturer_access = 0x0010
        self.manufacturer_access = 0x0010

    # ------------------------------------------------
    # --- commands that work only in unsealed mode ---
    # ------------------------------------------------

    def seal(self) -> bool:
        """Seals the battery."""
        if self.is_sealed(refresh=True): return True
        self.manufacturer_access = 0x0030 # this is chipset specific!
        sleep(0.1)
        if not self.is_sealed(refresh=True): return False
        # After sealing quite a few commands are not recognised by the bq.
        # Therefore we explicitly wait before proceeding with further script
        # actions.
        sleep(0.5) # was 5s !!!
        return True

    def change_keys(self, new_unseal_key: bytes | bytearray, new_fullaccess_key: bytes | bytearray) -> None:
        """Change unseal and fullaccess keys.

        To be compatible with newer chipsets like the bq40z50, we need to write both keys together.

        Args:
            new_unseal_key (bytes | bytearray): 4 bytes key
            new_fullaccess_key (bytes | bytearray): 4 bytes key
        """
        new_unseal_key = self._validate_buffer(new_unseal_key, length=4, name="new_unseal_key")
        new_fullaccess_key = self._validate_buffer(new_fullaccess_key, length=4, name="new_fullaccess_key")
        if not self.is_unsealed(check_fullaccess=True):
            raise BatterySecurityError("Device is sealed, cannot change fullaccess key.")
        # ....
        pass

    def sleep(self) -> None:
        """Enter sleepmode if the conditions are met.

        From Datasheet:
            Instructs the bq20z60-R1/bq20z65-R1 to verify and enter sleep mode if no other command is sent after
            the Sleep command. Any SMB transition wakes up the bq20z60-R1/bq20z65-R1. It takes about 1 minute
            before the device goes to sleep. This command is only available when the bq20z60-R1/bq20z65-R1 is in
            Unsealed or Full Access mode.
        """
        if self.is_sealed(refresh=True): raise BatterySecurityError("Device is sealed, cannot set sleep mode.")
        self.manufacturer_access = 0x0011


    def read_flash_subclass(self, subclassid: str, hexi: bool | str | None = None) -> str | bytearray:
        raise NotImplementedError("read_flash_page() only available for bq20z65, use read_flash_block() instead for bq40z50")

    def write_flash_subclass(self, subclassid: str, data: bytes | bytearray) -> str | bytearray:
        raise NotImplementedError("write_flash_page() only available for bq20z65, use write_flash_block() instead for bq40z50")

    def read_flash_block(self, flash_address: int, length: int = 32,  hexi: bool | str | None = None) -> str | bytearray:
        """Reads the bq chip data flash at a flash address with given length.
        The length may be up to 8192 bytes (full flash)

        Uses manufacturer block command 0x44, readback address is verified.

        Args:
            flash_address (int): flash location to start reasing from 0x4000 .. 0x5fff
            length (int, optional): length of bytes to read 1 .. 8192. Defaults to 32.
            hexi (None | bool | str, optional): If not none returns the data as hex encoded string with hexi as separator if it is a string. Defaults to None.

        Raises:
            ValueError: if flash_address or flash_adress + length is out of range (0x4000 - 0x6000)
            BatterySecurityError: if device is sealed
            BatteryError: if readBlock has failed
            BatteryError: if returned address does not match the requested one
            BatteryError: if total bytes length does not match the requested length

        Returns:
            bytearray:  Array of bytes read from given address with length given.
        """
        flash_address = int(flash_address)
        length = int(length)
        if (flash_address < 0x4000) or (flash_address+length > 0x6000):
            raise ValueError("Flash block area [{},{}] out of range [{},{}]".format(flash_address, flash_address+length,  0x4000, 0x6000))
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot read flash.")
        # action
        buf = pack("<H", flash_address)
        self.writeBlock(0x44, buf) # write NOT verified (cannot read same data from same address)
        #sleep(0.010)
        self.waitForReady(timeout_ms=50, throw=True)
        # now we can read all requested data in a loop as the bq40z50 is increasing its internal address pointer by the bytes returned
        flash = bytearray()
        address = flash_address
        while address < flash_address+length:
            data, ok = self.readBlock(0x44) # this chipset increments the internal pointer after read so we cannot do verified read here!
            if not ok or len(data)<2: raise BatteryError("Cannot read flash from battery at address {}.".format(address))
            radr = unpack_from("<H", data, 0)[0] # TUPPPPPEL - LECK MICH!!!!!!
            if radr != address:
                raise BatteryError("Read back address {} does not match written address {}.".format(radr, address))
            block = data[2:] # return arry slice without leading address bytes
            flash = flash + block
            address = address + len(block)
        if len(flash) < length:
            raise BatteryError("Returned data length {} matches not expected length {}.".format(len(flash), length))
        if len(flash) > length:
            # last block may have had less than 32 bytes -> cut it down to the correct length
            # as we did not had any transfer failure above.
            flash = flash[:length]

        # TO LOCAL FILE
        # if to_file is not None:
        #     with open("/log/{}".format(to_file), "wt") as f:
        #         f.write(self._maybe_hexlify(flash, True))
        return self._maybe_hexlify(flash, hexi)

    def write_flash_block(self, flash_address: int, block_data: bytes | bytearray) -> bool:
        """Writes a defined data block (array) into the bq chip data flash at a defined flash address.

        Args:
            (int): address in flash
            (bytearray): data to write

        Returns:
            (bool): False if writing has failed or the verification readback data differ from the data to write.
        """

        _log = getLogger(__name__, DEBUG)
        block_data = self._validate_buffer(block_data, name="block_data")
        length = len(block_data)
        if (flash_address < 0x4000) or (flash_address+length > 0x6000):
            raise ValueError("Flash block area [{},{}] out of range [{},{}]".format(flash_address, flash_address+length,  0x4000, 0x6000))
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot write flash.")
        # action
        a = 0
        address = flash_address
        while address < flash_address+length:
            page = min(32, length-a)
            data = pack("<H", address) + block_data[a:a+page] # pack address in front of the data
            _log.debug(f"Write Block 0x{address:08x}:{page}")
            self.writeBlock(0x44, data) # NOT verified
            # now poll for battery is finished with flash writing
            sleep(0.3)
            self.waitForReady(timeout_ms=300, throw=True)
            _log.debug(f"Read back 0x{address:08x}:{page}")
            readback = self.read_flash_block(address, length=page, hexi=None) # we get only the data, not the address back here!
            if (readback is None) or (len(readback) < page):
                raise BatteryError("Readback length of data too less. Read {} to compare {}".format(len(readback), page))
            if readback != data[2:]: # slice the address
                raise BatteryError("Readback verification failed. Read {} to compare {}".format(hexlify(readback), hexlify(data[2:])))
            address = address + page
            a = a + page
        return True


    def write_flash_from_file(self, filename: str) -> None:
        """Programming the firmware is chipset specific.

        Args:
            filename (str): name to a data file like .srec, .hex which has to provide target addresses.

        """

        _log = getLogger(__name__, DEBUG)
        binfile = BinFile(filenames=str(filename))
        print(binfile.info())
        _info = f"From file '{filename}' loaded segments = " + ",".join([f"0x{s.address:08x}:{format_size(len(s.data), binary=True)}" for s in binfile.segments])
        _log.info(_info)
        # for segment in binfile.segments:
        #     _log.info(f"Write flash at 0x{segment.address:08x}, {len(segment.data)} bytes.")
        #     self.write_flash_block(segment.address, segment.data)


    def read_authentication_key(self) -> None:
        """Returns the programmed authentication key."""
        raise NotImplementedError("There is no direct read access to the sha1 key for this chipset.")


    def change_authentication_key(self, new_key: bytes | bytearray) -> bool:
        """Program a new authentication key.

        Using variant (2) from Manual:
          Send the AuthenticationKey() command to ManufacturerAccess(), then send the 128-bit authentication
          key to Authentication().
        Verify by variant (2) from Manual:
          Read the response from Authentication() after updating the new authentication key.

        Args:
            string | bytes: new key in hex form or bytes
        """
        new_key = self._validate_buffer(new_key, name="new_key", length=16)
        if not self.is_unsealed(check_fullaccess=True): raise BatterySecurityError("Device is not in full access mode, cannot change authentication key.")
        buf = bytes(reversed(new_key))
        self.manufacturer_access = 0x0037
        self.writeBlock(Cmd.AUTHENTICATE, buf) # cannot be verified by read !
        sleep(0.52) # for bq40z50: wait 500ms
        return self.authenticate(new_key) # verify if the new key is installed


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
            self.manufacturer_block_access = command
            res = self.manufacturer_block_access
            rcv_command = struct.unpack("<H", res[:2])[0]
            res = res[2:]  # slice the command
            # if the expected length may variy you need to pass None to length
            if (rcv_command == command) and (((length is not None) and (len(res) == length)) or (length is None)):
                return res
        raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(res)}, {len(res)}")


    #---HELPER FOR PRODUCTION----------------------------------------------------------------------


    def manufacturing_dastatus1(self, hexi: bool | str | None = None) -> tuple:
        """Read DAStatus1 and return the registers as they come.

        Raises:
            BatteryError: _description_

        Returns:
            OrderedDict: _description_
        """
        buf = self.read_manufacturer_block(command=0x0071, length=32)        
        self._manufacturing_dastatus1 = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            # data come little endian
            "cell_voltage_1": unpack_from("<H", buf, 0)[0] * 1e-3,  # mV, unsigned short, little endian
            "cell_voltage_2": unpack_from("<H", buf, 2)[0] * 1e-3,  # mV, unsigned short, little endian
            "cell_voltage_3": unpack_from("<H", buf, 4)[0] * 1e-3,  # mV, unsigned short, little endian
            "cell_voltage_4": unpack_from("<H", buf, 6)[0] * 1e-3,  # mV, unsigned short, little endian
            "bat_voltage":    unpack_from("<H", buf, 8)[0] * 1e-3,  # mV, unsigned short, little endian
            "pack_voltage":   unpack_from("<H", buf, 10)[0] * 1e-3,  # mV, unsigned short, little endian
            "cell_current_1": unpack_from("<h", buf, 12)[0] * 1e-3,  # mA, signed short, little endian
            "cell_current_2": unpack_from("<h", buf, 14)[0] * 1e-3,  # mA, signed short, little endian
            "cell_current_3": unpack_from("<h", buf, 16)[0] * 1e-3,  # mA, signed short, little endian
            "cell_current_4": unpack_from("<h", buf, 18)[0] * 1e-3,  # mA, signed short, little endian
            "cell_power_1":   unpack_from("<H", buf, 20)[0] * 1e-2,  # cW, signed short, little endian
            "cell_power_2":   unpack_from("<h", buf, 22)[0] * 1e-2,  # cW, signed short, little endian
            "cell_power_3":   unpack_from("<h", buf, 24)[0] * 1e-2,  # cW, signed short, little endian
            "cell_power_4":   unpack_from("<h", buf, 26)[0] * 1e-2,  # cW, signed short, little endian
            "power_calculated": unpack_from("<h", buf, 28)[0] * 1e-2,  # cW, signed short, little endian
            "average_power":  unpack_from("<h", buf, 30)[0] * 1e-2,  # cW, signed short, little endian
        })
        return _od2t(self._manufacturing_dastatus1)  # Teststand interface

    def manufacturing_dastatus2(self, celsius: bool = True, hexi: bool | str | None = None) -> tuple:
        buf = self.read_manufacturer_block(command=0x0072, length=16)         
        self._manufacturing_dastatus2 = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            # data come little endian
            "int_temperature": unpack_from("<H", buf, 0)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "ts1_temperature": unpack_from("<H", buf, 2)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "ts2_temperature": unpack_from("<H", buf, 4)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "ts3_temperature": unpack_from("<H", buf, 6)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "ts4_temperature": unpack_from("<H", buf, 8)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "cell_temperature":    unpack_from("<H", buf, 10)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "fet_temperature":     unpack_from("<H", buf, 12)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
            "gauging_temperature": unpack_from("<H", buf, 14)[0] * 1e-1 - (KELVIN_ZERO_DEGC if celsius else 0),  # 0.1K, unsigned short, little endian
        })
        return _od2t(self._manufacturing_dastatus2)  # Teststand interface


    def _read_ccadc_cal(self, hexi: bool | str | None = None) -> tuple:
        #self.manufacturer_access = 0xf081  # output CCADC Cal
        buf = self.manufacturer_block_access
        buf = buf[2:]  # slice command
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 24): 
            raise BatteryError(f"Readings implausible: Unexpected return value or length mismatch {type(buf)}, {len(buf)}")
        self._ccadc_cal = OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),  # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
            "counter":        unpack_from("<B", buf, 0)[0],
            "status":         unpack_from("<b", buf, 1)[0],
            "current_cc":     unpack_from("<h", buf, 2)[0]*1e-3,  # mA, signed short, little endian, current (coulomb counter)
            "cell_voltage_1": unpack_from("<h", buf, 4)[0]*1e-3,   # mV, signed short, little endian,  
            "cell_voltage_2": unpack_from("<h", buf, 6)[0]*1e-3,  # mV, signed short, little endian,
            "cell_voltage_3": unpack_from("<h", buf, 8)[0]*1e-3,  # mV, signed short, little endian,
            "cell_voltage_4": unpack_from("<h", buf, 10)[0]*1e-3,  # mV, signed short, little endian,
            "pack_voltage":   unpack_from("<h", buf, 12)[0]*1e-3,  # mV, signed short, little endian,
            "bat_voltage":    unpack_from("<h", buf, 14)[0]*1e-3,  # mV, signed short, little endian,
            "cell_current_1": unpack_from("<h", buf, 16)[0]*1e-3,  # mA, signed short, little endian,
            "cell_current_2": unpack_from("<h", buf, 18)[0]*1e-3,  # mA, signed short, little endian,
            "cell_current_3": unpack_from("<h", buf, 20)[0]*1e-3,  # mA, signed short, little endian,
            "cell_current_4": unpack_from("<h", buf, 22)[0]*1e-3,  # mA, signed short, little endian,
        })
        return _od2t(self._ccadc_cal)

    def _wait_for_adc_update(self, num_of_changes: int, timeout :int, t0_ns: int = None):
        """
        Reads "ManufacturerData" and waits the 8-bit counter changed by "num_of_changes".

        Args:
            num_of_changes (int): _description_
            timeout (int): _description_
            t0_ns (int, optional): _description_. Defaults to None.

        Raises:
            TimeoutError: _description_
        """
        # wait the 8-bit counter changed by "num_of_changes" -> overflow need to be respected!
        self._read_ccadc_cal()
        c0 = self._ccadc_cal["counter"]  # get the current counter
        #if t0_ns is None:
        t0_ns = monotonic_ns()
        pause = timeout / 10   # do 10 times access maximum
        c1 = c0
        while (abs(c1-c0) < num_of_changes):
            t1_ns = monotonic_ns()
            if (t1_ns - t0_ns) > timeout * 1e+9:
                raise TimeoutError("While wait for calibration counter")
            #self._read_ccadc_cal()  # update calibration reading
            sleep(pause)
            self._read_ccadc_cal()
            c1 = self._ccadc_cal["counter"]

    def calib_read_adc_cell_voltage(self, samples: int = 4, shorted: bool = False, timeout: float = 5.0) -> float:
        """
        Enables the calibration mode of the battery if not set already, then
        measures the voltage for Cell 1, averages "samples" readings for higher accuracy, 
        returning the mean value.

        ATTENTION: its important to use Cell 1 voltage, not the others to get needed accuracy!

        Args:
            samples (int, optional): number of samples to average. Defaults to 8.
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                    internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.
            timeout (float, optional): Overall timeout in seconds. Defaults to 5.0.

        Returns:
            float: value of averaged ADC measurements
        """

        def _get_adc_reading(i: int) -> float:
            self._read_ccadc_cal()
            return self._ccadc_cal[f"cell_voltage_{i}"]

        t0 = monotonic_ns()  # common timout over the whole function
        # make sure that calibration test is enabled
        self._ms_toggle_helper("cal_test", True, 0x002d)
        sleep(0.05)
        # enable selected raw cell voltage output on ManufacturerData()
        if shorted:
            self.manufacturer_access = 0xf082  # output shorted CCADC Cal
        else:
            self.manufacturer_access = 0xf081  # output CCADC Cal
        voltage: float = 0
        #n = 8  # take 8 measurements, including the base   
        for _ in range(0, samples):
            # wait the 8-bit counter changed by 2 -> overflow need to be respected!
            self._wait_for_adc_update(2, timeout, t0_ns=t0)
            # now get the ADCs from the last block read with corrected signs
            voltage += _get_adc_reading(1)
        # calc mean values
        if (samples != 0): voltage = voltage/samples  
        else: voltage = 0
        return float(voltage)

    def calib_write_cell_voltage_gain(self, cell_voltages: Tuple[float], shorted: bool = False) -> Tuple[np.array, int]:
        """
        Cells Voltage Calibration. 

        Args:
            cell_voltages (Tuple[float]): measured (known) cells voltage, Volts
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.

        Returns:
            tuple:
                (np.array) calibrated cell voltage measurements (V) : len = len(given cell_voltage), 
                (int) bat_gain               
            
        """
        n_cell = len(cell_voltages)
        if (n_cell > 4):
            raise IndexError("Cells voltage list index out of range.")
        for i in range(n_cell):
            cell_voltages[i] = float(cell_voltages[i]) 
        # 1. average adc cell_1 voltage
        # Raw ADC data. 3.6 V == 19.45  
        adc_cell_voltage = self.calib_read_adc_cell_voltage(shorted=shorted)
        # 2. calculate cell_gain
        # adc_cell_voltage == 0 => Exception
        cell_gain: int = int(cell_voltages[0]/adc_cell_voltage*65536)
        # 3. write cell_gain
        block = self.read_flash_block(0x4000)  # one page, no extras
        bytes_cell_gain = cell_gain.to_bytes(2, byteorder='little', signed=True)
        block[0:2] = bytes_cell_gain  # 0x4000/0x4001     
        self.write_flash_block(0x4000, block)
        # 4. Return calibrated cell_voltages
        self._ms_toggle_helper("cal_test", False, 0x002d)
        sleep(0.1)
        dasstat = self.manufacturing_dastatus1()
        res = [dasstat[1 + i] for i in range(n_cell)]
        return np.array(res), cell_gain

    def calib_read_adc_bat_voltage(self,  samples: int = 4, shorted: bool = False,  timeout: float = 5.0) -> float:
        """Enables the calibration mode of the battery if not set already, then
        measures battery voltage, averages "samples" readings for higher accuracy, 
        returning the mean value.

        Args:
            samples (int, optional): number of samples to average. Defaults to 8.
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                    internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.
            timeout (float, optional): Overall timeout in seconds. Defaults to 5.0.

        Returns:
            float: value of averaged ADC measurements
        """
        t0 = monotonic_ns()  # common timout over the whole function
        # make sure that calibration test is enabled
        self._ms_toggle_helper("cal_test", True, 0x002d)
        sleep(0.05)
        # enable selected raw cell voltage output on ManufacturerData()
        if shorted:
            self.manufacturer_access = 0xf082  # output shorted CCADC Cal
        else:
            self.manufacturer_access = 0xf081  # output CCADC Cal
        adc_bat_voltage: float = 0
        # take "samples" measurements, including the base
        for _ in range(0, samples):
            # wait the 8-bit counter changed by 2 -> overflow need to be respected!
            self._wait_for_adc_update(2, timeout, t0_ns=t0)
            # now get the ADCs from the last block read with corrected signs
            self._read_ccadc_cal()
            adc_bat_voltage += self._ccadc_cal[f"bat_voltage"] 
        if (samples != 0): adc_bat_voltage = adc_bat_voltage/samples
        else: adc_bat_voltage = 0
        return float(adc_bat_voltage)

    def calib_write_bat_voltage_gain(self, bat_voltage: float, shorted: bool = False) -> Tuple[float, int]:
        """
        Battery Voltage Calibration.

        Args:
            bat_voltage (int): measured (known) battery voltage, Volts
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.

        Returns:
            float: calibrated battery voltage.
            tuple: 
                (float) calibrated battery voltage (V),
                (int) bat_gain

        """
        bat_voltage = float(bat_voltage) 
        # 1. average adc bat voltage 
        # Raw ADC data. 10.8 V == ~14.4  
        adc_bat_voltage = self.calib_read_adc_bat_voltage(shorted=shorted)
        # 2. calculate bat_gain
        # adc_bat_voltage == 0 => Exception
        bat_gain: int = int(bat_voltage / adc_bat_voltage * 65536)
        # 3. write bat_gain
        block = self.read_flash_block(0x4000)  # one page, no extras   
        bytes_bat_gain = bat_gain.to_bytes(2, byteorder='little', signed=False)
        block[4:6] = bytes_bat_gain  # 0x4004/0x4005
        self.write_flash_block(0x4000, block)
        # 4. Return calibrated cell_voltages
        self._ms_toggle_helper("cal_test", False, 0x002d)
        sleep(0.1)
        dasstat = self.manufacturing_dastatus1()
        return float(dasstat[5]), bat_gain

    def calib_read_adc_pack_voltage(self,  samples: int = 4, shorted: bool = False,  timeout: float = 5.0) -> float:
        """Enables the calibration mode of the battery if not set already, then
        measures package voltage, averages "samples" readings for higher accuracy, 
        returning the mean value.

        Args:
            samples (int, optional): number of samples to average. Defaults to 8.
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                    internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.
            timeout (float, optional): Overall timeout in seconds. Defaults to 5.0.

        Returns:
            float: value of averaged ADC measurements
        """
        t0 = monotonic_ns()  # common timout over the whole function
        # make sure that calibration test is enabled
        self._ms_toggle_helper("cal_test", True, 0x002d)
        sleep(0.05)
        # enable selected raw cell voltage output on ManufacturerData()
        if shorted:
            self.manufacturer_access = 0xf082  # output shorted CCADC Cal
        else:
            self.manufacturer_access = 0xf081  # output CCADC Cal
        adc_pack_voltage: float = 0
        # take 8 measurements, including the base
        for _ in range(0, samples):
            # wait the 8-bit counter changed by 2 -> overflow need to be respected!
            self._wait_for_adc_update(2, timeout, t0_ns=t0)
            # now get the ADCs from the last block read with corrected signs
            self._read_ccadc_cal()
            adc_pack_voltage += self._ccadc_cal[f"pack_voltage"] 
        if (samples != 0): adc_pack_voltage = adc_pack_voltage/samples
        else: adc_pack_voltage = 0
        return float(adc_pack_voltage)

    def calib_write_pack_voltage_gain(self, pack_voltage: float, shorted: bool = False) -> Tuple[float, int]:
        """
        Package Voltage Calibration.

        Args:
            pack_voltage (float): measured (known) package voltage, Volts
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.

        Returns:
            tuple:
                (float) calibrated package voltage (V),
                (int) pack_gain
        """
        pack_voltage = float(pack_voltage) 
        # 1. average adc bat voltage 
        # Raw ADC data. 10.8 V == ~14.25  
        adc_pack_voltage = self.calib_read_adc_pack_voltage(shorted=shorted)
        # 2. calculate bat_gain
        # adc_pack_voltage == 0 => Exception
        pack_gain: int = int(pack_voltage/adc_pack_voltage*65536)
        # 3. write bat_gain
        block = self.read_flash_block(0x4000)  # one page, no extras
        #print(block)  
        bytes_pack_gain = pack_gain.to_bytes(2, byteorder='little', signed=False)
        block[2:4] = bytes_pack_gain  # 0x4002/0x4003
        self.write_flash_block(0x4000, block)
        # 4. Return calibrated cell_voltages
        self._ms_toggle_helper("cal_test", False, 0x002d)
        sleep(0.1)
        dasstat = self.manufacturing_dastatus1()
        return float(dasstat[6]), pack_gain

    def calib_read_adc_current(self,  samples: int = 4, shorted: bool = False,  timeout: float = 5.0) -> float:
        """
        Enables the calibration mode of the battery if not set already, then
        measures current_cc, averages "samples" readings for higher accuracy, 
        returning the mean value.

        Args:
            samples (int, optional): number of samples to average. Defaults to 8.
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                    internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.
            timeout (float, optional): Overall timeout in seconds. Defaults to 5.0.

        Returns:
            float: value of averaged ADC measurements
        """
        t0 = monotonic_ns()  # common timout over the whole function
        # make sure that calibration test is enabled
        self._ms_toggle_helper("cal_test", True, 0x002d)
        sleep(0.05)
        # enable selected raw cell voltage output on ManufacturerData()
        if shorted:
            self.manufacturer_access = 0xf082  # output shorted CCADC Cal
        else:
            self.manufacturer_access = 0xf081  # output CCADC Cal
        adc_curr: float = 0
        # take "samples" measurements, including the base
        for _ in range(0, samples):
            # wait the 8-bit counter changed by 2 -> overflow need to be respected!
            self._wait_for_adc_update(2, timeout, t0_ns=t0)
            # now get the ADCs from the last block read with corrected signs
            self._read_ccadc_cal()
            adc_curr += self._ccadc_cal[f"current_cc"] 
        if (samples != 0): 
            adc_curr = adc_curr / samples
        else: 
            adc_curr = 0
        return adc_curr

    def calib_write_current_gain(self, current: float, shorted: bool = False) -> Tuple[float,float,float,float,float]:
        """
        Current Calibration.

        Args:
            current (int): measured (known) current, Amps
            shorted (bool, optional): Decides if shorted CCADC mode or normal. This mode enables an
                internal short on the coulomb counter inputs (SRP, SRN). Defaults to False.

        Returns:
            tuple: 
                (float) calibrated current (A), 
                (float) bq_st_cc_gain, 
                (float) cc_gain, 
                (float) capacity_gain, 
                (float) adc_current

        """
        current = float(current)
        # 1. average adc current 
        adc_current = self.calib_read_adc_current(shorted=shorted)
        # 2. calculate current_gain, capacity_gain. 
        # adc_current == 0 => Exception
        #cc_gain = 3.58422                  # default
        if adc_current != 0:
            cc_gain = float(current / adc_current)
        else:
            cc_gain = 3.58422
        capacity_gain = float(cc_gain * 298261.6178)
        # 3. write bat_gain        
        bytes_cc_gain = bytearray(struct.pack("<f", cc_gain))         # 4 bytes
        bytes_cap_gain = bytearray(struct.pack("<f", capacity_gain))  # 4 bytes
        block = self.read_flash_block(0x4000)  # one page, no extras
        block[6:10] = bytes_cc_gain    # 0x4006/7/8/9
        block[10:14] = bytes_cap_gain  # 0x400a/b/c/d
        #block = (block[:6]                
        #        + bytes_cc_gain   # 0x4006/7/8/9
        #        + bytes_cap_gain  # 0x400a/b/c/d
        #        + block[14:])     # brackets to avoid linter failure
        #if len(block) != 32: raise Exception("Fuck the Energiesparlampe!")      
        self.write_flash_block(0x4000, block)
        # 4. Return calibrated current
        self._ms_toggle_helper("cal_test", False, 0x002d)
        sleep(0.1)
        # do a measurement to provide verification
        _current_meas = self.get_current()
        # use BQ Studio scale factor
        bq_st_cc_gain = 3.714528 / cc_gain
        # return the relevant values e.g. for logging
        return _current_meas, bq_st_cc_gain, cc_gain, capacity_gain, adc_current

    def calib_write_temp(self, temp: Tuple[float]) -> Tuple[np.array,int,int,int,int]:
        """
        Temperature calibration.

        Args:
            temp (Tuple[int]): temperature TS1 ... TS4, degrees C

        Returns:
            tuple:
              (np.array): 1 to number of given temperatures (temp) as celsius (°C),
              (int,): 4x offsets which are stored into the flash

        """
        n_ts = len(temp)
        if (n_ts > 4):
            raise IndexError("Temperature list index out of range.")
        # convert to °C x10
        t_temp = [int(temp[i] * 10) for i in range(n_ts)]
        # 1. Read TS1...TS4 offset
        block = self.read_flash_block(0x4000)  # one page (32 bytes), no extras
        # convert 4 temperature offsets to *signed* bytes
        ts_offset = [struct.unpack_from("<b", block[i:])[0] for i in range(0x15, 0x19)]
        # 2. Read appropriate temperature from the DAStatus2()
        dastatus2 = self.manufacturing_dastatus2(celsius=True)
        # convert TS1 ... TS4 from the tuple list
        int_temp = [int(t * 10) for t in dastatus2[2:6]]
        # 3. Calculate new TS1...TS4 offset
        #new_offset = bytearray(b'\x00') * 4  # 4 bytes 0's initialized
        new_offset = bytearray()
        for i in range(0, 4):
            if (i < n_ts):
                dt = t_temp[i] - int_temp[i] + ts_offset[i] 
                _b = struct.pack("b", dt)        
            else:
                _b = b'\x00'
            new_offset += _b
        # copy new temperature offset
        block[0x15:0x19] = new_offset
        # 4. Write new TS1...TS4 offset
        self.write_flash_block(0x4000, block)
        # 5. Re-check temperature TS1...TS4
        dastatus2 = self.manufacturing_dastatus2()
        res = [dastatus2[2 + i] for i in range(n_ts)]
        # return the measurements and offsets for documentation
        return np.array(res), *[struct.unpack_from("<b", new_offset[i:])[0] for i in range(4)]
        
    def _ms_toggle_helper(self, ms_key: str, enable: bool, ma_cmd: int, retries: int = 5, pause_on_retry: float = 0.1) -> bool:
        """Internal function to set a defined state using toggle and manufacturing_status() reads for control.

        Having retries = 1 results in always one control read of operation status after potential toggle.

        Args:
            ms_key (str): _description_
            enable (bool): _description_
            ma_cmd (int): _description_
            retries (int, optional): _description_. Defaults to 1.

        Returns:
            bool: _description_
        """
        _toggle_issued = False  # restrict to exactily one toggle command if needed
        while (retries >= 0):
            try:
                self.manufacturing_status()  # => update the self._manufacturing_status attribute
                if bool(self._manufacturing_status[ms_key]) != bool(enable):
                    if not _toggle_issued:
                        self.manufacturer_access = ma_cmd  # need to toggle
                        _toggle_issued = True                       
                    else:
                        # already issued the toggle command -> wait for correct state
                        pass
                    if pause_on_retry: 
                        sleep(pause_on_retry)
                else:
                    pass  # already on the target state -> do not pause  
            except OSError as ex:
                if pause_on_retry: 
                    sleep(pause_on_retry)
            finally:
                retries -= 1
        return (bool(self._manufacturing_status[ms_key]) == bool(enable))


    def _os_toggle_helper(self, os_key: str, enable: bool, ma_cmd: int, retries: int = 5, pause_on_retry: float = 0.2) -> bool:
        """Internal function to set a defined state using toggle and operation_status() reads for control.

        Having retries = 1 results in always one control read of operation status after potential toggle.

        Args:
            os_key (str): _description_
            enable (bool): _description_
            ma_cmd (int): _description_
            retries (int, optional): _description_. Defaults to 1.

        Returns:
            bool: _description_
        """
        _toggle_issued = False  # restrict to exactily one toggle command if needed
        while (retries >= 0):
            try:
                self.operation_status()  # => update the self._manufacturing_status attribute
                if bool(self._operation_status[os_key]) != bool(enable):
                    if not _toggle_issued:
                        self.manufacturer_access = ma_cmd  # need to toggle
                        _toggle_issued = True
                    else:
                        # already issued the toggle command -> wait for correct state
                        pass
                    if pause_on_retry: 
                        sleep(pause_on_retry)
                else:
                    pass  # already on the target state -> do not pause  
            except OSError as ex:
                if pause_on_retry: 
                    sleep(pause_on_retry)
            finally:
                retries -= 1
        return (bool(self._operation_status[os_key]) == bool(enable))


    def toggle_fuse(self) -> None:
        """This command manually activates/deactivates the FUSE output to ease testing during manufacturing.

        If the OperationStatus()[FUSE] = 0 indicates the FUSE output is low. Sending this command toggles the
        FUSE output to be high and the OperationStatus()[FUSE] = 1.

        Args:
            enable (None | bool, optional): toggle (enable is None) or optionally use toggle to set a defined
                state (enable is bool) if not set already. Defaults to None.

        """
        self.manufacturer_access = 0x001d

    def set_fuse(self, enable: bool) -> bool:
        #return self._ms_toggle_helper("fuse", enable, 0x001d, pause_after_toggle=0.5)
        return self._os_toggle_helper("fuse", enable, 0x001d, retries=40)


    def toggle_pchg_fet(self) -> None:
        """This command turns on/off the PCHG FET drive function to ease testing during manufacturing."""
        self.manufacturer_access = 0x001e

    def set_pchg_fet(self, enable: bool) -> bool:
        return self._ms_toggle_helper("pchg_en", enable, 0x001e)

    def toggle_chg_fet(self) -> None:
        """This command turns on/off the CHG FET drive function to ease testing during manufacturing.

        If the ManufacturingStatus()[CHG_TEST] = 0, sending this command turns on the CHG FET and the
        ManufacturingStatus()[CHG_TEST] = 1 and vice versa. This toggling command is only enabled if
        ManufacturingStatus()[FET_EN] = 0, indicating an FW FET control is not active and manual control is
        allowed. A reset clears the [CHG_TEST] flag and turns off the CHG FET.
        """
        self.manufacturer_access = 0x001f

    def set_chg_fet(self, enable: bool) -> bool:
        return self._ms_toggle_helper("chg_en", enable, 0x001f)

    def toggle_dsg_fet(self):
        """This command turns on/off DSG FET drive function to ease testing during manufacturing.

        If the ManufacturingStatus()[DSG_TEST] = 0, sending this command turns on the DSG FET and the
        ManufacturingStatus()[DSG_TEST] = 1 and vice versa. This toggling command is only enabled if
        ManufacturingStatus()[FET_EN] = 0, indicating an FW FET control is not active and manual control is
        allowed. A reset clears the [DSG_TEST] flag and turns off the DSG FET.
        """
        self.manufacturer_access = 0x0020

    def set_dsg_fet(self, enable: bool) -> bool:
        return self._ms_toggle_helper("dsg_en", enable, 0x0020)

    def toggle_gauging(self):
        """This command enables or disables the gauging function to ease testing during manufacturing.

        The initial setting is loaded from Mfg Status Init[GAUGE_EN]. If the ManufacturingStatus()[GAUGE_EN] = 0,
        sending this command will enable gauging and the ManufacturingStatus()[GAUGE_EN] = 1 and vice
        versa. In UNSEALED mode, the ManufacturingStatus()[GAUGE_EN] status is copied to Mfg Status
        Init[GAUGE_EN] when the command is received by the gauge. The bq40z50-R2 device remains on its
        latest gauging status prior to a reset.
        """
        self.manufacturer_access = 0x0021
    
    def set_gauging(self, enable: bool) -> bool:
        return self._ms_toggle_helper("gauge_en", enable, 0x0021)

    def toggle_fet_control(self):
        """This command disables/enables control of the CHG, DSG, and PCHG FET by the firmware.

        The initial setting is loaded from Mfg Status Init[FET_EN]. If the ManufacturingStatus()[FET_EN] = 0,
        sending this command allows the FW to control the PCHG, CHG, and DSG FETs and the
        ManufacturingStatus()[FET_EN] = 1 and vice versa.

        In UNSEALED mode, the ManufacturingStatus()[FET_EN] status is copied to Mfg Status Init[FET_EN]
        when the command is received by the gauge. The bq40z50-R2 device remains on its latest FET control
        status prior to a reset.
        """
        self.manufacturer_access = 0x0022

    def set_fet_control(self, enable: bool) -> bool:
        return self._ms_toggle_helper("fet_en", enable, 0x0022)

    def toggle_lifetime_data_collection(self):
        """This command disables/enables Lifetime Data Collection to help streamline production testing.

        The initial setting is loaded from Mfg Status Init[LF_EN]. If the ManufacturingStatus()[LF_EN] = 0,
        sending this command starts the Lifetime Data Collection and the ManufacturingStatus()[LF_EN] = 1 and vice versa.
        In UNSEALED mode, the ManufacturingStatus()[LF_EN] status is copied to Mfg Status Init[LF_EN] when the
        command is received by the gauge. The bq40z50-R2 device remains on its latest Lifetime Data Collection
        setting prior to a reset.
        """
        self.manufacturer_access = 0x0023

    def set_lifetime_data_collection(self, enable: bool) -> bool:
        return self._ms_toggle_helper("lf_en", enable, 0x0023)

    def toggle_permanent_failure(self):
        self.manufacturer_access = 0x0024

    def set_permanent_failure(self, enable: bool) -> bool:
        return self._ms_toggle_helper("pf_en", enable, 0x0024)

    def toggle_black_box_recorder(self):
        self.manufacturer_access = 0x0025

    def set_black_box_recorder(self, enable: bool) -> bool:
        return self._ms_toggle_helper("bbr_en", enable, 0x0025)    

    def toggle_fuse_control(self):
        self.manufacturer_access = 0x0026

    def set_fuse_control(self, enable: bool) -> bool:
        return self._ms_toggle_helper("fuse_en", enable, 0x0026)

    def toggle_led_display(self):
        self.manufacturer_access = 0x0027

    def set_led_display(self, enable: bool) -> bool:
        return self._ms_toggle_helper("led_en", enable, 0x0027)

    def toggle_led_onoff(self):
        self.manufacturer_access = 0x002b

    def set_led_onoff(self, enable: bool) -> bool:
        return self._os_toggle_helper("led", enable, 0x002b)

    def is_led_on(self) -> bool:
        self.operation_status() # => update the self._manufacturing_status attribute
        return bool(self._operation_status["led"])

    def reset_device(self):
        self.manufacturer_access = 0x0041
    
    #def reset_device_0x0012(self):  # backward compatibility command
    #    self.manufacturer_access = 0x0012

    def get_afe_register(self, hexi: bool | str | None = None) -> tuple:
        buf = self.read_manufacturer_block(command=0x0058, length=32)
        return _od2t(OrderedDict({
            "block": self._maybe_hexlify(buf, hexi),
            # data come little endian
            "interrupt_status":  unpack_from("<b", buf, 0)[0],
            "fet_status":  unpack_from("<b", buf, 0)[0],
            "rxin":  unpack_from("<b", buf, 0)[0],
            "latch_status":  unpack_from("<b", buf, 0)[0],
            "interrupt_enable":  unpack_from("<b", buf, 0)[0],
            "fet_control":  unpack_from("<b", buf, 0)[0],
            "rxien":  unpack_from("<b", buf, 0)[0],
            "rlout":  unpack_from("<b", buf, 0)[0],
            "rhout":  unpack_from("<b", buf, 0)[0],
            "rhint":  unpack_from("<b", buf, 0)[0],
            "cell_balance":  unpack_from("<b", buf, 0)[0],
            "adc_cc_control":  unpack_from("<b", buf, 0)[0],
            "adc_mux_control":  unpack_from("<b", buf, 0)[0],
            "led_control":  unpack_from("<b", buf, 0)[0],
            "control_various":  unpack_from("<b", buf, 0)[0],
            "timer_control":  unpack_from("<b", buf, 0)[0],
            "protection_delay_control":  unpack_from("<b", buf, 0)[0],
            "ocd":  unpack_from("<b", buf, 0)[0],
            "scc":  unpack_from("<b", buf, 0)[0],
            "scd1":  unpack_from("<b", buf, 0)[0],
            "scd2":  unpack_from("<b", buf, 0)[0],
        }))

    # def read_mib(self, address: int, length: int, hexi: bool | None = False) -> str|tuple:
    #     """
    #      Reads 32 bytes of Manufacturer info block, starting at address 0x4041.

    #     Args:
    #         length (int): length of manufacturer info data
    #         hexi (bool): True - returns tuple of ASCII codes, False - returns string 

    #     Returns:
    #         str | tuple:  Manufacturer info block A01 - (A01 + length)
    #     """
    #     hexi = bool(hexi)
    #     length = int(length)
    #     assert((length) > 0 and (length <= 32)), ValueError('Invalid block length. Allowed length is 1 .. 32')
    #     assert((address >= 0x4041) and (address <= 0x4060)), ValueError('Invalid address. Allowed 0x4041 .. 0x4060')
    #     assert((address-1) + length <= 0x4060), ValueError('Invalid data length or start address. Block of data out of range 0x4041 ..0x4060')
    #     if not hexi:
    #         # string
    #         mib: bytearray = self.read_flash_block(address, length=32, hexi=False)
    #         mib_str = "".join(map(chr, mib))
    #         mib_str = mib_str[0:length]
    #         return mib_str
    #     else:
    #         return self.read_flash_block(address, length=32, hexi=True)
            
    # def write_mib(self, data: str, length: int, address: int) -> bool:
    #     """
    #     Writes "length" bytes of "data" to Manufacturer info block, starting at "address"

    #     Args:
    #         data (tuple): manufacturer info data (dec or hex)
    #         length (int): length of manufacturer info data
    #         address (int): starting address

    #     Returns:
    #         bool: True - success, False - failed
    #     """
    #     data = str(data)
    #     length = int(length)
    #     address = int(address)
    #     assert((length) > 0 and (length <= 32)), ValueError('Invalid block length. Allowed length is 1 .. 32')
    #     assert((address >= 0x4041) and (address <= 0x4060)), ValueError('Invalid address. Allowed 0x4041 .. 0x4060')
    #     assert((address-1) + len(data) <= 0x4060), ValueError('Invalid data length or start address. Block of data out of range 0x4041 ..0x4060')
    #     try:
    #         start_ind = address - 0x4041
    #         stop_ind = start_ind + len(data)
    #         mib = self.read_mib(0x4041, 32, hexi=False)
    #         #udi : str = "12345678123456781234567812345678"
    #         #ss : str = ''.join(map(str,data))
    #         new_mib : str = (mib[:start_ind] + data[:length] + mib[stop_ind:])
    #         new_mib = bytearray(new_mib.encode("ascii"))
    #         #print(new_mib)
    #         res = self.write_flash_block(0x4041, new_mib)
    #     except Exception:
    #         raise
    #     return res


    def write_pcba_udi_block(self, udi_block: str) -> bool:
        """
        Writes specific RRC prefix and PCBA serial number into Manufacturer info block.
        Addresses: A01-A08 (0x4041 .. 0x4048)

        Args:
            pcba_sn (str): unique serial number for every PCBA (7 characters)
            prefix (str, optional): specific prefix provided by RRC. Defaults to "A".

        Returns:
            bool: True - success, False - failed
        """
        
        if "PCBA" in udi_block:
            # strip PCBA from udi
            clean_udi = udi_block.replace("PCBA", "")
        else:
            clean_udi = udi_block
        assert(len(clean_udi) >= 2 and len(clean_udi) <= 15), ValueError(f"Clean UDI length={len(clean_udi)} not between 2 and 15.")
        return self.write_flash_block(0x4041, bytes(clean_udi, encoding="utf-8"))

    def read_pcba_udi_block(self) -> str:
        """
        Reads specific RRC prefix and PCBA serial number from the Manufacturer info block.
        Addresses: A01-A08 (0x4041 .. 0x4048)

        Returns:
            str: pcba udi block
        """
        return self.read_flash_block(0x4041, 15).decode()



    def write_serial_number_block(self, sn: str) -> bool:
        """
        Writes serial number into Manufacturer info block.
        Addresses: A17-A30 (0x04041+17 = 0x4052 .. 0x4060)

        Args:
            sn (str): serial number (14 characters)

        Returns:
            bool: True - success, False - failed
        """
        assert(len(sn) <= 14), ValueError('Serial number length more then 14 characters.')
        buffer = bytes(sn, encoding="utf-8")
        return self.write_flash_block(0x4052, buffer)

    def read_serial_number_block(self) -> str:
        """
        Reads serial number from the Manufacturer info block.
        Addresses: A17-A30 (0x4052..0x4060)

        Returns:
            str: serial number block
        """
        return self.read_flash_block(0x4052, 14).decode()
    


    def write_internal_use_indexing(self, index_byte: str) -> bool:
        """
        Writes Internal Use Indexing Byte into Manufacturer info block.
        Addresses: A16 (0x4051)

        Args:
            index (str): index value (1 character)

        Returns:
            bool: True - success, False - failed
        """
        assert(len(index_byte) == 1), ValueError('Index my not have more then 1 character.')
        return self.write_flash_block(0x4051, bytes(index_byte, encoding="utf-8"))



    def read_index_byte(self) -> str:
        """
        Reads Internal Use Indexing Byte from the Manufacturer info block.
        Addresses: A16 (0x4051)

        Returns:
            str: Internal Use Indexing Byte
        """
        return self.read_flash_block(0x4051, 1).decode()


    def read_firmware_revision(self) -> str:
        """
        Reads firmware_revision from the Manufacturer info block.
        Addresses: A31-A32 (0x405F .. 0x4060)

        Returns:
            str: firmware_revision
        """
        return self.read_flash_block(0x405F, 2).decode()


    def set_manufacturer_date(self) -> bool:
        """
        Writes and verifies manufacturer date to the register 0x1B ManufacturerDate()

        Returns:
            bool: True - success, False - failed
        """
        try:
            now = datetime.now()
            bq_date = int(now.day + 32*now.month + (now.year - 1980)*512)
            cmd_manufacturer_date = 0x1B
            res = self.writeWordVerified(cmd= cmd_manufacturer_date, w= bq_date)
        except Exception:
            raise
        return bool(res)
    
    def set_pack_sn(self, sn: str) -> bool:
        """
        Writes and verifies pack serial number to the register 0x1C SerialNumber()

        Args:
            sn (str): serial number (hex). Examplpe "00B4"

        Returns:
            bool: True - success, False - failed
        """
        assert(len(sn) == 4), ValueError('Invalid string length. Allowed length is 4')
        try:
            sn = str(sn)
            sn_int = int(sn, 16)
            cmd_serial_number = 0x1C
            res = self.writeWordVerified(cmd= cmd_serial_number, w= sn_int)
        except Exception:
            raise
        return bool(res)

    def get_rsoc(self) -> int:
        """
        Returns the predicted remaining battery capacity as a percentage of
        FullChargeCapacity()

        Returns:
            int: RSOC, %
        """
        buf = self.soc()
        return int(buf[0])

    def get_current(self) -> float:
        """
        Returns the measured current.

        Returns:
            float: _description_
        """
        buf =  self.current()
        return float(buf[0])
    
    def get_safety_status(self) -> str:
        """
        Returns safety status register to log it.

        Returns:
            str: safety status register
        """
        self.manufacturer_access = 0x0051
        buf = self.manufacturer_data
        return str(buf)

    def get_pf_status(self) -> str:
        """
        Returns PF status register to log it.

        Returns:
            str: PF status register
        """
        self.manufacturer_access = 0x0053
        buf = self.manufacturer_data
        return str(buf)        
    
    def reset_errors(self) -> None:
        """
        Resets Black Box Recorder and Permanent Fail Data.
        """
        # Black Box Recorder reset
        self.manufacturer_access = 0x002A
        #dummy = self.read_manufacturer_block(command=0x002A, length=None)
        # Permanent Fail Data Reset
        self.manufacturer_access = 0x0029
        #dummy = self.read_manufacturer_block(command=0x0029, length=None)
    
    def check_no_errors(self) -> bool:
        """
        Checks Safety Status and Permanent Fail Status.

        Returns:
            bool: True - no errors, False - errors detected.
        """
        no_errs = True
        # Safety status
        
        self.manufacturer_access = 0x0051
        buf = self.manufacturer_data
        for i in range(len(buf)):
            if (buf[i] != 0):
                no_errs = False
        # PF status
        self.manufacturer_access = 0x0053
        buf = self.manufacturer_data
        for i in range(len(buf)):
            if (buf[i] != 0):
                no_errs = False
        return no_errs

    def ts_DeviceName(self) -> str:
        pass
    
#--------------------------------------------------------------------------------------------------
# -R2-
#--------------------------------------------------------------------------------------------------

class BQ40Z50R2(BQ40Z50R1):

    def __init__(self, smbus: BusMaster, slvAddress: int = 0x0b, pec: bool = False):
        # Note: explicitely replicate the parameters here for having
        # option in teststand to change them on call
        super().__init__(smbus, slvAddress=slvAddress, pec=pec)

    #
    # !! NO NEED to overwrite __str__() !!
    #
    
    def __repr__(self) -> str:
        return f"BQ40Z50R2({repr(self.bus)}, slvAddress={self.address}, pec={self.pec})"

    #----------------------------------------------------------------------------------------------

    @property
    def name(self):
        """Returns the battery chipset name in lower case."""
        return "bq40z50r2"

    def autodetect(self) -> bool:
        """Identifies the presence of a chipset of this type.

           We need to use some kind of SIGNATURE functions or check known responses.
           This differs from chipset to chipset.

        """
        #print(self.name)
        yesno = False
        try:
            self.operation_status() # if other chipset, this read will raise exception
            dev = self.device_type()
            self.firmware_version()
            if dev == 0x4500: # RRC2054xx, RRC21xx
                if self._firmware_version["version"] & 0xff00 == 0x0200: # RRC2130, RRC2140, ...
                    yesno=True
        except BatteryError:
            # not the right chipset
            pass
        except OSError as ex:
            if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                # -> forward this exception
                raise ex
        return yesno


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
