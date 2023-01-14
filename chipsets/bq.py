"""Battery BMS-IC specific commands (called chipset)

Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

#import errno
from time import sleep
from binascii import unhexlify
from os import urandom
from hashlib import sha1
#from rrc.battery_errors import BatteryError
from rrc.smartbattery import Cmd
from rrc.chipsets.base import Chipset

#--------------------------------------------------------------------------------------------------
class ChipsetTexasInstruments(Chipset):
    """Abstract chipset type for TexasInstrument chipsets containing all common functions.

       Do NOT instantiate direcctly, instead use one of the capital letter BQxxx classes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"SmartBattery with TI-chipset at 0x{self.address} on {str(self.smbus)}"

    def __repr__(self) -> str:
        return f"ChipsetTexasInstruments({repr(self.smbus)}, slvAddress={self.slvAddress}, pec={self.pec})"

    #----------------------------------------------------------------------------------------------
    @property
    def name(self):
        """Returns the battery chipset name."""
        return "undefined"

    def autodetect(self):
        """Identifies the presence of a chipset of this type."""
        pass

    def cell_voltages(self) -> tuple:
        """ Returns the cell voltage registers of the chip as array.

            Independent how many cells are connected, all four registers
            are always read and returned. The array is [vcell1,vcell2,vcell3,vcell4].
        Returns:
            array: integers
        """
        return (
            self.readWordVerified(Cmd.CELL1_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL2_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL3_VOLTAGE)[0],
            self.readWordVerified(Cmd.CELL4_VOLTAGE)[0]
        )

    def is_sealed(self, refresh=True):
        """Returns true of the device is sealed.

        Args:
            refresh (bool): if True, the shadow flags will be read from battery before its flags being analyzed. Defaults to False.
        """
        pass

    def is_unsealed(self, check_fullaccess=False, refresh=False):
        """Checks if the battery is sealed.

        Args:
            (bool): if check_fullaccess is true, it also checks if battery is in full access mode.
            refresh (bool): if True, the shadow flags will be read from battery before its flags being analyzed. Defaults to False.

        Returns
            (bool): true of the device is NOT sealed if check_fullaccess is true,
                    else only true if battery is unsealed and in full access mode.
        """
        pass

    def operation_status(self):
        """Contains important status flage like sealed/unsealed status etc."""
        pass

    def authenticate(self, key: bytes | bytearray | str) -> bool:
        """Authenticate battery by using SHA1 key with a random challenge.

        Args:
            key (bytes | bytearray | hex-string): a 32 bytes key

        Raises:
            AttributeError: [description]
            AttributeError: [description]
            AttributeError: [description]

        Returns:
            [type]: [description]
        """
        key = self._validate_buffer(key, name="key", length=16)
        challenge = urandom(20) # create a random challenge
        hmac2 = sha1(key + sha1(key + challenge).digest()).digest()
        rchallenge = bytes(reversed(challenge)) # swap from big to little endian byte first
        if self.writeBlock(Cmd.AUTHENTICATE, rchallenge): # NOT verified
            sleep(0.52) # for bq20z65: wait 250ms", for bq40z50: wait 500ms
            response, ok = self.readBlock(Cmd.AUTHENTICATE)
            if ok:
                rresponse = bytes(reversed(response))
                #print(rresponse, rchallenge)
                return (hmac2 in rresponse) and (len(hmac2) == len(rresponse))
        return False

    def _write_key(self, key: int | bytes | bytearray | str) -> None:
        """Writes a given key of 32bits to the battery by manufacturer_access.

            Used to unseal the battery for TI chipsets.

            Args:
               key (int | bytes | bytearray | str): either a 32bit integer or bytes, bytearray of 4 bytes or a string of 8 hex characters,
                            optionally preceded by a colon ":"
            Exceptions:
                AttributeError - if key is neither an integer nor string
                TypeError - if key is not in correct form for unhexlify()
            Returns
                None
        """
        #hexlify(unseal_key, ':').decode()
        if isinstance(key, int):
            ikey = key # already integer
        elif isinstance(key, bytearray) or isinstance(key, bytes):
            ikey = int.from_bytes(key, "big")
        elif isinstance(key, str):
            if key[0] == ":":
                b = unhexlify(key[1:])
            else:
                b = unhexlify(key)
            ikey = int.from_bytes(b, "big")
        else:
            raise AttributeError("Invalid battery key")
        #words = [ ikey & 0xffff, ikey>>16 & 0xffff ]
        #print( [hexlify(w.to_bytes(2,"big")) for w in words] )
        self.manufacturer_access = (ikey & 0xffff)         # low word first
        self.manufacturer_access = ((ikey >> 16) & 0xffff) # high word then

    def unseal(self, unseal_key: int | bytes | bytearray | str, fullaccess_key: int | bytes | bytearray | str = None) -> bool:
        """Unseals the battery using a key given in hexadecimal format.

           Note: this function needs to have is_unsealed() implemented!

           The key can also be given in key encoded format, prepend a colon
           in this case (":abcdef...").

            Args:
                (string): unseal_key
                (string): fullaccess_key

            Returns:
                (boolean)
        """
        check_fullaccess=fullaccess_key is not None
        if self.is_unsealed(check_fullaccess=check_fullaccess, refresh=True):
            return True # already in correct mode
        # Note: After sealing, the bq will not accept unsealing for about
        #       3s to 5s, therefore we retry.
        for _ in range(0, 20):
            self._write_key(unseal_key)
            sleep(0.25) # wait a bit (250ms)
            if self.is_unsealed():
                #print("bestens")
                break

        if not self.is_unsealed(refresh=True):
            return False
        if fullaccess_key is None:
            return True # only unseal needed
        if self.is_unsealed(check_fullaccess=True, refresh=True):
            return True # already full access without dedicated key
        #print("try full access")
        # Batteries might need a time between 1s and 4s to accept full access
        # after the unseal key was written.
        for _ in range(0, 8):
            sleep(0.5)
            self._write_key(fullaccess_key)
            if self.is_unsealed(check_fullaccess=True, refresh=True):
                #print("superbestens")
                return True
        #print("grrr")
        return False

    def enable_full_access(self) -> bool:
        """Sets the battery into full-access mode by calling the unseal function with keys for the chipset."""
        pass

    def read_manufacturer_info_block(self, hexi: bool | str | None = None) -> bytes | bytearray | str:
        block, _ = self.readBlockVerified(0x70)
        return self._maybe_hexlify(block, hexi)

    # --- commands that work only in unsealed mode ---
    def seal(self):
        """Seals the battery if it is unsealed. Must be provided together with unseal() function."""
        pass

# END OF FILE
