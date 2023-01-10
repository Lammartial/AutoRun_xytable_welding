"""Battery BMS-IC specific commands (called chipset)

   Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904
import errno
#from battery.smartbattery import Battery
from time import sleep
from binascii import hexlify
from struct import pack, unpack, unpack_from
#from uos import urandom
#from uhashlib import sha1
from collections import OrderedDict
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from rrc.battery_errors import BatteryError, BatterySecurityError
from rrc.smbus import BusMaster
from rrc.smartbattery import Cmd
from rrc.chipsets.bq import ChipsetTexasInstruments


#--------------------------------------------------------------------------------------------------

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
    def __init__(self, smbus: BusMaster):
        super().__init__(smbus)
        self._operation_status = None # shadow copy of operation_status() read to avoid redundant reads for seal/unseal checks

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
            fw_rev = self.firmware_version()
            #print(fw_rev)
            if dev == 0x4500: # RRC2054xx, RRC21xx
                if fw_rev["version"] & 0xff00 == 0x0100: # RRC2054, RRC2054-2, ...
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
        self.manufacturer_access = 0x0002
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 11):
            raise BatteryError("Readings implausible: Unexpected return value %s,%s.", type(buf), len(buf))
        return _od2t(OrderedDict({
            "value": self._maybe_hexlify(buf, hexi),
            # data come big endian - they SUCK!
            "device_number": unpack_from(">H", buf, 0)[0],
            "version":       unpack_from(">H", buf, 2)[0],
            "build_number":  unpack_from(">H", buf, 4)[0],
            "firmware_type": unpack_from(">B", buf, 6)[0],
            "impedance_track_version": unpack_from(">H", buf, 7)[0],
            "reserved1":     unpack_from(">B", buf, 9)[0],
            "reserved2":     unpack_from(">B", buf, 10)[0],
        }))

    def hardware_version(self) -> int:
        """Returns the chip hardware version."""
        self.manufacturer_access = 0x0003
        buf = self.manufacturer_data
        value = unpack("<H", buf)[0]  # data come litte endian
        return value

    def chemistry_id(self) -> int:
        """Returns the OCV table chemistry ID of the battery."""
        self.manufacturer_access = 0x0008
        buf = self.manufacturer_data
        value = unpack("<H", buf)[0]  # data come litte endian
        return value

    def manufacturer_status(self) -> int:
        raise NotImplementedError("manufacturer_status() only available for bq20z65.")

    def operation_status(self, hexi: bool | str | None = None) -> tuple:
        """
            SIGNATURE function: We can use this function to identify the chipset type,
                                by checking the Exception()

        """
        self.manufacturer_access = 0x0054
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 4):
            BatteryError("Readings implausible: Unexpected return value %s,%s.", type(buf), len(buf))
        os = int.from_bytes(buf, "little")
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

    def manufacturing_status(self, hexi: bool | str | None = None) -> tuple:
        self.manufacturer_access = 0x0057
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 2):
            BatteryError("Readings implausible: Unexpected return value %s,%s.", type(buf), len(buf))
        os = int.from_bytes(buf, "little")
        return _od2t(OrderedDict({
            "block"     : self._maybe_hexlify(buf, hexi),
            "value"     : os,
            # bitflags
            "cal_test":  ((os>>15) & 1), # (os & (1<<15)) != 0,
            "lt_test":   ((os>>14) & 1), # (os & (1<<14)) != 0,
            # ...
        }))

    # --- more functionality for production -------------------------------------------------------

    def manufacturing_dastatus1(self, si_units: bool = True, hexi: bool | str | None = None) -> tuple:
        """Read DAStatus1 and return the registers as they come.

        Raises:
            BatteryError: _description_

        Returns:
            OrderedDict: _description_
        """
        self.manufacturer_access = 0x0071
        buf = self.manufacturer_data
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 32):
            BatteryError("Readings implausible: Unexpected return value %s,%s.", type(buf), len(buf))
        return _od2t(OrderedDict({
            "block" : self._maybe_hexlify(buf, hexi),
            # data come little endian
            "cell_voltage_1": unpack_from("<H", buf, 0)[0] * (0.001 if si_units else 1),
            "cell_voltage_2": unpack_from("<H", buf, 2)[0] * (0.001 if si_units else 1),
            "cell_voltage_3": unpack_from("<H", buf, 4)[0] * (0.001 if si_units else 1),
            "cell_voltage_4": unpack_from("<H", buf, 6)[0] * (0.001 if si_units else 1),
            "bat_voltage":    unpack_from("<H", buf, 8)[0] * (0.001 if si_units else 1),
            "pack_voltage":   unpack_from("<H", buf, 10)[0] * (0.001 if si_units else 1),
            "cell_current_1": unpack_from("<h", buf, 12)[0] * (0.001 if si_units else 1),
            "cell_current_2": unpack_from("<h", buf, 14)[0] * (0.001 if si_units else 1),
            "cell_current_3": unpack_from("<h", buf, 16)[0] * (0.001 if si_units else 1),
            "cell_current_4": unpack_from("<h", buf, 18)[0] * (0.001 if si_units else 1),
            "cell_power_1":   unpack_from("<H", buf, 20)[0] * (0.01 if si_units else 1),
            "cell_power_2":   unpack_from("<h", buf, 22)[0] * (0.01 if si_units else 1),
            "cell_power_3":   unpack_from("<H", buf, 24)[0] * (0.01 if si_units else 1),
            "cell_power_4":   unpack_from("<H", buf, 26)[0] * (0.01 if si_units else 1),
            "power_calculated": unpack_from("<H", buf, 28)[0] * (0.01 if si_units else 1),
            "average_power":  unpack_from("<H", buf, 30)[0] * (0.01 if si_units else 1),
        }))

    def manufacturing_dastatus2(self, si_units:bool = True, celsius: bool = False, hexi: bool | str | None = None) -> tuple:
        self.manufacturer_access = 0x0072
        buf = self.manufacturer_data
        #buf = b"0123456789012345"
        if (not isinstance(buf, (bytes, bytearray)) or len(buf) != 16):
            raise BatteryError("Readings implausible: Unexpected return value %s,%s.", type(buf), len(buf))
        return _od2t(OrderedDict({
            "block" : self._maybe_hexlify(buf, hexi),
            # data come little endian
            "int_temperature": unpack_from("<h", buf, 0)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "ts1_temperature": unpack_from("<h", buf, 2)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "ts2_temperature": unpack_from("<h", buf, 4)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "ts3_temperature": unpack_from("<h", buf, 6)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "ts4_temperature": unpack_from("<h", buf, 8)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "cell_temperature":    unpack_from("<h", buf, 10)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "fet_temperature":     unpack_from("<h", buf, 12)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
            "gauging_temperature": unpack_from("<h", buf, 14)[0] * (1 if si_units else 0.1) + (KELVIN_ZERO_DEGC if celsius else 0),
        }))


    # ...


    # ---------------------------------------------------------------------------------------------
    def is_sealed(self, refresh: bool = False) -> bool:
        """check if batetry is sealed

        Args:
            refresh (bool, optional): if True, the operation_status shadow will be read fresh from battery before analyze its flags. Defaults to False.

        Returns:
            bool: True, if sealed False otherwise
        """
        if refresh or self._operation_status is None: self.operation_status()
         # using shadow copy to avoid bus access
        print("s_SEC:", self._operation_status["sec"])
        return self._operation_status["sec"] == 0x03 # using shadow copy to avoid bus access


    def is_unsealed(self, check_fullaccess: bool = False, refresh: bool = False):
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
        print("u_SEC:", self._operation_status["sec"])
        if check_fullaccess:
            return (int(self._operation_status["sec"]) == 1) # full access
        return (int(self._operation_status["sec"]) in [1, 2]) # unsealed OR full access

    def lifetime_datablock(self, hexi: bool | str | None = None):
        """Compatibility function: reading just first block of lifetimedata for use e.g. in production.

        Returns:
            dict: decoded lifetime data of block 1 according the datasheet
        """
        self.manufacturer_block_access = 0x0060 # lifetime data block 1 (32 bytes)
        data = self.manufacturer_block_access
        if not isinstance(data, bytearray):
            raise BatteryError("No correct lifetime data from battery for block {}. Got {} expected bytesarray".format(1, type(data)))
        if (len(data) != 32 + 2):
            raise BatteryError("No correct lifetime data from battery for block {}. Got {} bytes expected {}".format(1, len(data), 32+2))
        # all fine, store the data
        b1 = data[2:]
        return _od2t(OrderedDict({
            "values": self._maybe_hexlify(b1, hexi), # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
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
            "values": h, # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
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

    def change_keys(self, new_unseal_key: bytes | bytearray, new_fullaccess_key: bytes | bytearray):
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
            self.writeBlock(0x44, data) # NOT verified
            # now poll for battery is finished with flash writing
            self.waitForReady(timeout_ms=300, throw=True)
            readback = self.read_flash_block(address, length=page, hexi=None) # we get only the data, not the address back here!
            if (readback is None) or (len(readback) < page):
                raise BatteryError("Readback length of data too less. Read {} to compare {}".format(len(readback), page))
            if readback != data[2:]: # slice the address
                raise BatteryError("Readback verification failed. Read {} to compare {}".format(hexlify(readback), hexlify(data[2:])))
            address = address + page
            a = a + page
        return True


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


#--------------------------------------------------------------------------------------------------
# -R2-
class BQ40Z50R2(BQ40Z50R1):
    def __init__(self, smbus):
        super().__init__(smbus)
        return

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
            fw_rev = self.firmware_version()
            #print(fw_rev)
            if dev == 0x4500: # RRC2054xx, RRC21xx
                if fw_rev["version"] & 0xff00 == 0x0200: # RRC2130, RRC2140, ...
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

# END OF FILE
