"""Battery BMS-IC specific commands (called chipset)

Used to access RRC proprietary features on the battery

"""

__version__ = "1.0.0"
__author__ = "Markus Ruth"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from binascii import unhexlify
from rrc.smartbattery import Battery

#--------------------------------------------------------------------------------------------------
class Chipset(Battery):
    """Abstract chipset type containing all common functions.

    Do NOT instantiate directly.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        """Returns the battery chipset name."""
        return "undefined"

    def autodetect(self):
        """Identifies the presence of a chipset of this type."""
        pass

    def authenticate(self, key) -> bool:
        """Authenticate battery by using a cryptographic feature."""
        pass

    def _validate_buffer(self, buffer: bytes | bytearray | str, name: str = "buffer", length: int = None) -> bytes | bytearray:
        """Validates a given buffer and also converts it into bytes from a hex char string if possible.

        Args:
            buffer (bytes | bytearray | str): the buffer to check and convert if it is a hex string
            name (str, optional): [description]. Defaults to "buffer".
            length (int | None, optional): Length of the buffer as bytes or bytearray.
                Note that this means if passed a key as hex string, its length is checked AFTER conversion. Defaults to None.

        Raises:
            ValueError: if length is not None and bytes buffer length is not equal the parameter.
            ValueError: data type of buffer does not match str, bytes or bytearray

        Returns:
            bytes | bytearray: converted buffer if it was hex string, else as it comes in.
        """
        if isinstance(buffer, str):
            buffer = unhexlify(buffer[1:]) if buffer[0] == ":" else unhexlify(buffer)
        if isinstance(buffer, bytes) or isinstance(buffer, bytearray):
            if length is not None:
                if len(buffer) != length:
                    raise ValueError("Data length for {} is wrong. Given length {} expected {}".format(name, len(buffer), length))
        else:
            raise ValueError("Data for {} must be either of type bytes, bytearray or hex string. Given {}".format(name,type(buffer)))
        return buffer # validated okay

#--------------------------------------------------------------------------------------------------



# END OF FILE
