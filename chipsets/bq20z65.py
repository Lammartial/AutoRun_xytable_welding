"""Battery BMS-IC specific commands (called chipset)

   Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904
import errno
from time import sleep
from binascii import hexlify
from struct import pack, unpack_from
from rrc.battery_errors import BatteryError, BatterySecurityError
#from rrc.smartbattery import BlockData
from rrc.chipsets.bq import ChipsetTexasInstruments

###################################################################################################
#
#  BQ 20 Z 65
#
###################################################################################################

# class ExtCmd:
#     LIFETIME_DATA1 =      0x73
#     LIFETIME_DATA2 =      0x74

class BQ20Z65R1(ChipsetTexasInstruments):
    def __init__(self, smbus):
        super().__init__(smbus)
        # _bat = self
        # for c in [
        #      ExtCmd.LIFETIME_DATA1,
        #      ExtCmd.LIFETIME_DATA2,
        #      ]: self.ds[c] = BlockData(_bat, c)
        self._operation_status = None # shadow copy of operation_status() read to avoid redundant reads for seal/unseal checks

    @property
    def name(self):
        """Returns the battery chipset name in lower case."""
        return "bq20z65r1"

    def autodetect(self):
        """Identifies the presence of a chipset of this type."""
        #print(self.name)
        yesno=False
        try:
            self.manufacturer_information_data() # if other chipset, this read will raise exception
            dev = self.device_type()
            fw_rev = self.firmware_version()
            if dev == 0x0650: # RRC2020xx
                if fw_rev != 0x0106: # is rev1, not rev2
                    yesno=True
        except BatteryError as bex:
            # not the right chipset
            pass
        except OSError as ex:
            if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                # -> forward this exception
                raise ex
        return yesno

    def device_type(self):
        """Returns the BQ IC part number."""
        self.manufacturer_access = 0x0001
        value = self.manufacturer_access
        return value

    def firmware_version(self):
        """Returns the chip firmware version."""
        self.manufacturer_access = 0x0002
        value = self.manufacturer_access
        return value

    def hardware_version(self):
        """Returns the chip hardware version."""
        self.manufacturer_access = 0x0003
        value = self.manufacturer_access
        return value

    def manufacturer_status(self):
        sleep(0.001)
        self.manufacturer_access = 0x0006
        sleep(0.001)
        raw = self.manufacturer_access
        status = { "value": raw, "state": "" }
        switch = str((raw >> 14) & 0x03)
        switchMap_A = {
            str(0x00): { "charge_fet_on": True,  "discharge_fet_on": True },
            str(0x01): { "charge_fet_on": False, "discharge_fet_on": True },
            str(0x02): { "charge_fet_on": False, "discharge_fet_on": False },
            str(0x03): { "charge_fet_on": True,  "discharge_fet_on": False },
        }
        status.update(switchMap_A[switch])
        #status["state"] = "(value-" + str((raw>>12) & 0x03) + ")"
        switch = str((raw>>12) & 0x03)
        switchMap_B = {
            str(0x00): { "state": "wakeup" },
            str(0x01): { "state": "normal-discharge" },
            str(0x03): { "state": "pre-charge" },
            str(0x05): { "state": "charge" },
            str(0x07): { "state": "charge-termination" },
            str(0x08): { "state": "fault-charge-terminate" },
            str(0x09): { "state": "permanent-failure" },
            str(0x0a): { "state": "over-current" },
            str(0x0b): { "state": "over-temperature" },
            str(0x0c): { "state": "battery-failure" },
            str(0x0d): { "state": "sleep" },
            str(0x0e): { "state": "discharge-prohibited" },
            str(0x0f): { "state": "battery-removed" }
        }
        status.update(switchMap_B[switch])
        if status["state"] == "permanent-failure":
            switch = str((raw>>8) & 0x0f)
            switchMap_C = {
                str(0): { "state_add": "-fuse-blown" },
                str(1): { "state_add": "-cell-imbalance-failure" },
                str(2): { "state_add": "-safety-voltage-failure" },
                str(3): { "state_add": "-fet-failure" }
            }
            status["state"] += switchMap_C[switch]
        return status

    def chemistry_id(self):
        """Returns the OCV table chemistry ID of the battery."""
        self.manufacturer_access = 0x0008
        value = self.manufacturer_access
        return value

    def manufacturer_information_data(self):
        """
            SIGNATURE function: We can use this function to identify the chipset type,
                                by checking the Exception()

            If we have a battery with this IC type, an access to the manufacturer_data
            returns 14 bytes - in contrast to the 4 bytes of e.g. bq40Z50

        """
        self.manufacturer_access = 0x0054
        value = self.manufacturer_data
        if (not isinstance(value, bytearray) or len(value) != 14):
            raise BatteryError("Readings implausible: Unexpected battery operation status return value.", value)
        # decode the information ...
        #...
        #... TODO:

    def operation_status(self, hexi=None):
        self.manufacturer_access = 0x0054
        value = self.manufacturer_access # word (2 bytes)
        self._operation_status = {
            "value"     : self._maybe_hexlify(value.to_bytes(2,"little"), hexi),
            "pres"      : ((value>>15) & 1), # (value & (1<<15)) != 0,
            "fas"       : ((value>>14) & 1), # (value & (1<<14)) != 0,
            "ss"        : ((value>>13) & 1), # (value & (1<<13)) != 0,
            "csv"       : ((value>>12) & 1), # (value & (1<<12)) != 0,
            "ldmd"      : ((value>>10) & 1), # (value & (1<<10)) != 0,
            "wake"      : ((value>>7) & 1), # (value & (1<<7)) != 0,
            "dsg"       : ((value>>6) & 1), # (value & (1<<6)) != 0,
            "xdsg"      : ((value>>5) & 1), # (value & (1<<5)) != 0,
            "xdsgi"     : ((value>>4) & 1), # (value & (1<<4)) != 0,
            "dsgin"     : ((value>>3) & 1), # (value & (1<<3)) != 0,
            "r_dis"     : ((value>>2) & 1), # (value & (1<<2)) != 0,
            "vok"       : ((value>>1) & 1), # (value & (1<<1)) != 0,
            "qen"       : ((value>>0) & 1) # (value & (1<<0)) != 0
        }
        return self._operation_status

    def is_sealed(self, refresh=False):
        """Returns true of the device is sealed."""
        if refresh or self._operation_status is None: self.operation_status()
        # using shadow copy to avoid bus access
        print("u_SS:", self._operation_status["ss"])
        return bool(self._operation_status["ss"])

    def is_unsealed(self, check_fullaccess=False, refresh=False):
        """Checks if the battery is sealed.

           Args:
             (bool): if check_fullaccess is true, it also checks if battery is in full access mode.
           Returns
              (bool): true of the device is NOT sealed if check_fullaccess is true,
                      else only true if battery is unsealed and in full access mode.
        """
        if refresh or self._operation_status is None: self.operation_status()
        # using shadow copy to avoid bus access
        print("u_SS:", self._operation_status["ss"])
        if bool(self._operation_status["ss"]): return False # is sealed
        print("u_FAS:", self._operation_status["fas"])
        if not check_fullaccess: return True
        return (self._operation_status["fas"] == 0)

    def soh(self):
        """Returns the state of health."""
        w, _ = self.readWordVerified(0x4F)
        return {
            "percent": (w & 0xff),
            "cll":  (w>>8 + 2) & 1,
            "detf": (w>>8 + 1) & 1,
            "detw": (w>>8 + 0) & 1
        }

    def lifetime_data(self, hexi=None):
        """Returns the life time data block 1 & 2 as decoded dict.

        Can be read in sealed and unsealed mode.

        Returns:
            dict: decoded lifetime data according the datasheet
        """
        b1, _ = self.readBlockVerified(0x73)
        if len(b1) != 32: raise BatteryError("Cannot read lifetime data1 block.")
        b2, _ = self.readBlockVerified(0x74)
        if len(b2) != 8: raise BatteryError("Cannot read lifetime data2 block.")
        h = {
            "blk_1": self._maybe_hexlify(b1, hexi),
            "blk_2": self._maybe_hexlify(b2, hexi)
        }
        return {
            "values": h, # all blocks of bytes as they are - but hexlified as it looks better in JSON files later ...
            # decode block 1 (convert to SI values)
            "lt_max_temp":            unpack_from(">h", b1, 0)[0]*1e-1, # 0.1°C, signed short, little endian
            "lt_min_temp":            unpack_from(">h", b1, 2)[0]*1e-1, # 0.1°C, signed short, little endian
            "lt_max_cell_voltage":    unpack_from(">h", b1, 4)[0]*1e-3, # mV, signed short, little endian
            "lt_min_cell_voltage":    unpack_from(">h", b1, 6)[0]*1e-3, # mV, signed short, little endian
            "lt_max_pack_voltage":    unpack_from(">h", b1, 8)[0]*1e-3, # mV, signed short, little endian
            "lt_min_pack_voltage":    unpack_from(">h", b1, 10)[0]*1e-3, # mV, signed short, little endian
            "lt_max_chg_current":     unpack_from(">h", b1, 12)[0]*1e-3, # mA, signed short, little endian
            "lt_max_dsg_current":     unpack_from(">h", b1, 14)[0]*1e-3, # mA, signed short, little endian
            "lt_max_chg_power":       unpack_from(">h", b1, 16)[0]*1e-2, # 10mW, signed short, little endian
            "lt_max_dsg_power":       unpack_from(">h", b1, 18)[0]*1e-2, # 10mW, signed short, little endian
            "lt_max_avg_dsg_current": unpack_from(">h", b1, 20)[0]*1e-3, # mA, signed short, little endian
            "lt_max_avg_dsg_power":   unpack_from(">h", b1, 22)[0]*1e-2, # 10mW, signed short, little endian
            "lt_avg_temp":            unpack_from(">h", b1, 24)[0]*1e-1, # 0.1°C, signed short, little endian
            "lt_temp_samples":        unpack_from(">l", b1, 26)[0], # number, signed long, little endian
            # decode block 2
            "ot_event_count":         unpack_from(">h", b2, 0)[0], # number, signed short, little endian
            "ot_event_duration":      unpack_from(">H", b2, 2)[0], # s, unsigned short, little endian
            "ov_event_count":         unpack_from(">H", b2, 4)[0], # number, unsigned short, little endian
            "ov_event_duration":      unpack_from(">H", b2, 6)[0], # s, unsigned short, little endian
        }

    def shipping_mode(self, ship_delay=5.0):
        """Enter shipping mode which is equal to shutdown mode but repects different timing of sealed and unsealed modes.

        If sealed, waits ship_delay seconds then checks for another ship_delay seconds time if
        battry is still responsive.

        From Manual:
            If Sealed Ship Delay is set to 5 seconds, then 5 seconds after
            receiving the 2 MAC (0x0010) commands the FETs will turn off,
            and 10 seconds after receiving the 2 commands,
            the bq20z60-R1/bq20z65-R1 will enter ship mode

        Args:
            ship_delay (float, optional): [description]. Defaults to 5.0.

        Returns:
            True if battery is not responding anymore, False else
        """
        #if not self.is_sealed(): raise BatterySecurityError("Device must be sealed to enter shipping mode.")
        wassealed = self.is_sealed(refresh=True)
        self.shutdown()
        if ship_delay is not None:
            if wassealed:
                sleep(ship_delay)
            # now check until battery does not respond anymore and wait max ship_delay fro that
            return self.waitForReady(timeout_ms=(ship_delay * 1e+3), invert=True)
        else:
            # no waits requested
            if not self.isReady(): return True
        return False


    def shutdown(self):
        """Shutdown - available in seald AND unsealed but with different delay times. (See Note)

        NOTE: from Datasheet
            Instructs the bq20z60-R1/bq20z65-R1 to verify and enter shutdown mode (when the
            bq20z60-R1/bq20z65-R1 is in Unsealed or Full Access mode). This command is only available when the
            bq20z60-R1/bq20z65-R1 is in Unsealed or Full Access mode. Shutdown is not entered unless the
            PackVoltage < Charger Present and Current ≤ 0.

            In sealed mode, if the shutdown command (0x0010) is received 2 consecutive times, the
            bq20z60-R1/bq20z65-R1 enters ship mode. The 2 MAC writes cannot have any other MAC commands
            following or between them. For bq20z60-R1/bq20z65-R1 to enter ship mode, PackVoltage must be less
            than Charger Present threshold AND there are no safety conditions.
        """
        issue2nd = self.is_sealed(refresh=True)
        self.manufacturer_access = 0x0010
        if issue2nd:
            self.manufacturer_access = 0x0010

    #-------------------------------------------------
    # --- commands that work only in unsealed mode ---
    #-------------------------------------------------

    def seal(self):
        """Seals the battery."""
        if self.is_sealed(refresh=True): return True
        self.manufacturer_access = 0x0020 # this is chipset specific!
        sleep(0.1)
        if not self.is_sealed(refresh=True): return False
        # After sealing quite a few commands are not recognised by the bq.
        # Therefore we explicitly wait before proceeding with further script
        # actions.
        sleep(0.5) # was 5s !!!
        return True

    def _change_unseal_key(self, new_key):
        if not (isinstance(new_key, bytes) or isinstance(new_key, bytearray)):
            raise ValueError("new_key must be either of type bytes or type bytearray. Given was {}".format(type(new_key)))
        if not self.is_unsealed():
            raise BatterySecurityError("Device is sealed, cannot change unseal key.")
        old_key = self.readBytesVerified(0x60, 4)
        try:
            rkey = bytes(reversed(new_key)) # must be reversed (from technical reference)
            self.writeBytesVerified(0x60, rkey)
        except OSError as ex:
            self.writeBytesVerified(0x60, old_key) # try to rebuild the original key
            raise ex
        return True

    def _change_fullaccess_key(self, new_key):
        if not (isinstance(new_key, bytes) or isinstance(new_key, bytearray)):
            raise ValueError("new_key must be either of type bytes or type bytearray. Given was {}".format(type(new_key)))
        if not self.is_unsealed(check_fullaccess=True):
            raise BatterySecurityError("Device is sealed, cannot change fullaccess key.")
        old_key = self.readBytesVerified(0x60, 4)
        try:
            rkey = bytes(reversed(new_key)) # must be reversed (from technical reference)
            self.writeBytesVerified(0x61, rkey)
        except OSError as ex:
            self.writeBytesVerified(0x61, old_key) # try to rebuild the original key
            raise ex
        return True

    def change_keys(self, new_unseal_key, new_fullaccess_key):
        """Change unseal and fullaccess keys.

        To be compatible with newer chipsets like the bq40z50, we need to write both keys together.

        Args:
            new_unseal_key (bytes | bytearray): 4 bytes key
            new_fullaccess_key (bytes | bytearray): 4 bytes key
        """
        # the check for seal/unseal is done in subroutines
        self._change_unseal_key(new_unseal_key)
        self._change_fullaccess_key(new_fullaccess_key)

    def sleep(self):
        """Enter sleepmode 2 minutes after this command.

            From Datasheet:
            Instructs the bq20z60-R1/bq20z65-R1 to verify and enter sleep mode if no other command is sent after
            the Sleep command. Any SMB transition wakes up the bq20z60-R1/bq20z65-R1. It takes about 1 minute
            before the device goes to sleep. This command is only available when the bq20z60-R1/bq20z65-R1 is in
            Unsealed or Full Access mode.
        """
        if self.is_sealed(refresh=True): raise BatterySecurityError("Device is sealed, cannot set sleep mode.")
        self.manufacturer_access = 0x0011

    def dataflash_checkum(self):
        """Returns the data flash checksum of the battery.
           Only available in unsealed mode, throws error if the battery is sealed.
           The process takes 135ms.
        """
        if self.is_sealed(): raise BatteryError("Device is sealed, firmware checksum not available.")
        self.manufacturer_access = 0x0004
        sleep(0.135) # @refman: takes about 45ms, safety factor=3.
        return self.manufacturer_access

    def enable_impedance_tracking(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot activate impedance tracking.")
        self.manufacturer_access = 0x0021

    def safe_pin_activation(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot activate SAFE pin.")
        self.manufacturer_access = 0x0030

    def safe_pin_clear(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot clear SAFE pin.")
        self.manufacturer_access = 0x0031

    def leds_on(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot set LED on.")
        self.manufacturer_access = 0x0032

    def leds_off(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot set LEDs off.")
        self.manufacturer_access = 0x0033

    def display_on(self):
        """ Activates simulates DISP pin signal edge to show the charge level."""
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot set display-on.")
        self.manufacturer_access = 0x0034

    def calibration_mode(self):
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot set calibration mode.")
        self.manufacturer_access = 0x0040

    def read_flash_subclass(self, subclassid, hexi=None):
        """Reads all bytes of a subclass id from data flash.

        Args:
            subclassid (int): subclass id 0..107
            hexi (None | str): if None, data read ie returned as plain bytes. If hexi is a string e.g. "" or ","
                               the data is converted into hex chars string.

        Raises:
            ValueError: [description]
            ValueError: [description]
            BatterySecurityError: [description]
            BatteryError: [description]
            BatteryError: [description]

        Returns:
            bytearray | str: all data of flash subclass (1 .. 256) depending on the selected subclass. Type depending on hexi parameter.
        """
        # parameter check
        if (subclassid is None) or (subclassid < 0) or (subclassid > 107):
            raise ValueError("Invalid subclass ID number")
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot read flash.")
        # action
        step = "write-word"
        flash = bytearray()
        try:
            self.writeWord(0x77, subclassid) # NOT verified as 0x77 cannot be read!
            for i in range(1,9): # =[1;8]
                step = "read-block page{}".format(i)
                try:
                    block, ok = self.readBlockVerified(0x77 + i) # VERIFIED by read-back! Raises exception of failure
                    if not ok: raise BatteryError("Flash read of subclass {}, page {} failed in read verification.".format(subclassid, i))
                    flash = flash + block
                    if len(block)<32: break
                except OSError:
                    if len(flash)>0: break # last page of class is on 32 bytes boundary, so we need a failed page+1 read to identify that
                    raise
                except Exception:
                    raise
            return self._maybe_hexlify(flash, hexi)
        except OSError:
            raise BatteryError("Flash read of subclass {}, failed in step '{}'.".format(subclassid, step))
        except Exception:
            raise
        # cannot get here

    def write_flash_subclass(self, subclassid, data):
        """Write a flash page using subclass ID, and page (1..8). Data given as numeric array.

        Duration depending on number of data pages (32 bytes each page): 50ms (1) to 400ms (8).

        Args:
            subclassid (int): subclass id 0..107
            data (bytes | bytearray | string): Data to write to a complete flash subclass.
                    Either plain bytes (byets or bytearray) up to 256 bytes or
                    hex encoded string with up to 512 characters which can also have a colon (:)
                    prepending the string for compatibility reasons.

        Returns:
            True on success, else raises Exceptions
        """
        # parameter check
        if (subclassid is None) or (subclassid < 0) or (subclassid > 107):
            raise ValueError("Invalid subclass ID number")
        flash = self._validate_buffer(data, name="flash data")
        if not (len(flash)>0 and len(flash)<257):
            raise ValueError("Data length must be between 1 and 256 bytes, {} was given.".format(len(flash)))
        if self.is_sealed(): raise BatterySecurityError("Device is sealed, cannot write flash.")
        # action
        step = "write-word"
        try:
            self.writeWord(0x77, subclassid)  # NOT verified as 0x77 cannot be read!
            for i in range(1,9):
                step = "write-block page{}".format(i)
                block = flash[:min(len(flash),32)]
                #print(type(block), len(block))
                if len(block) == 0: break
                flash = flash[len(block):]
                try:
                    self.writeBlock(0x77 + i, block) # can NOT do verified read as the 2nd fread after write already starts flash programming result in not reponding on SMBus
                    # now poll for battery is finished with flash writing
                    self.waitForReady(timeout_ms=300, throw=True)
                except Exception:
                    raise
        except OSError:
            raise BatteryError("Flash write of subclass {}, failed in step '{}'.".format(subclassid, step))
        except Exception:
            raise
        # passed - now give the flash write a bit time before re-read the whole data and compare for verification
        flash = self._validate_buffer(data, name="flash data")
        rbflash = self.read_flash_subclass(subclassid, hexi=None)
        if rbflash != flash:
            raise BatteryError("Flash write of subclass {}, verififcation failed in compare.".format(subclassid))
        return True # written and verified

    def read_flash_block(self, flash_address, length=32, hexi=None):
        raise NotImplementedError("bq20z65 does not provide directly addressable data flash access, use bq20z65r1.chipset.read_flash_subclass() instead.")

    def write_flash_block(self, flash_address, block_data):
        raise NotImplementedError("bq20z65 does not provide directly addressable data flash access, use bq20z65r1.chipset.write_flash_subclass() instead.")

    def read_authentication_key(self):
        """Returns the programmed authentication key."""
        if not self.is_unsealed(check_fullaccess=True): raise BatterySecurityError("Device is not in full access mode, cannot set read keys.")
        k0, _ = self.readBytes(0x66, 4)
        k1, _ = self.readBytes(0x65, 4)
        k2, _ = self.readBytes(0x64, 4)
        k3, _ = self.readBytes(0x63, 4)
        key = k0 + k1 + k2 + k3
        return key

    def change_authentication_key(self, new_key):
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
        buf = bytes(reversed(new_key)) # swap from big to little endian byte first
        # the description in tech.ref. is wrong: the key order is 0x63 .. 0x65 least sig to biggest sig byte
        for i in range(0,4):
            _ = self.writeBlock(0x63+i, buf[(0+i*4):(4+i*4)])   # AuthenKey3 .. 0 (0x63 .. 0x66)
            sleep(0.252) # for bq20z65: wait 250ms
        return self.authenticate(new_key) # verify if the new key is installed

#--------------------------------------------------------------------------------------------------
# -R2-
class BQ20Z65R2(BQ20Z65R1):
    def __init__(self, smbus):
        super().__init__(smbus)

    @property
    def name(self):
        """Returns the battery chipset name in lower case."""
        return "bq20z65r2"

    def autodetect(self):
        """Identifies the presence of a chipset of this type."""
        #print(self.name)
        yesno=False
        try:
            self.manufacturer_information_data() # if other chipset, this read will raise exception
            dev = self.device_type()
            fw_rev = self.firmware_version()
            if dev == 0x0650: # RRCxxxx
                if fw_rev == 0x0106: # is rev2
                    yesno=True
        except BatteryError as bex:
            # not the right chipset
            pass
        except OSError as ex:
            if (ex.args[0] != errno.ENODEV) and (ex.args[0] != errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                # -> forward this exception
                raise ex
        return yesno

# END OF FILE
