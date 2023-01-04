from eth2serial.base import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

DEBUG = 0

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------

class HiokiBaseDevice(Eth2SerialDevice):

    def get_idn(self) -> str:
        """
        Queries the device ID

        Returns:
            str: <Manufacturer's name>,<Model name>,0,<Software version>

        """
        return self.request("*IDN?")

class Hioki_BT3561A(HiokiBaseDevice):

    def set_resistance_range(self, range: float) -> bool:
        """Set the Resistance Measurement Range.

        Args:
            range (float): resistance 0...3100 Ohm

        Returns:
            bool: _description_
        """

        assert (range >= 0) and (range <= 3100), ValueError('invalid parameter for resistance: 0 < R <= 3100')
        return self.send(f':RES:RANG {range}')

# add more ...


class Hioki_SW1001(HiokiBaseDevice):

    def set_wire_mode(self, slot: int, mode: int) -> str:
        """
        Sets the connection method for a given slot.

        Args:
            slot (int): slot number 1 .. 3
            mode (int): wire mode 2 or 4

        Returns:
            str: _description_
        """

        assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
        assert ((mode == 2) or (mode == 4)), ValueError('Invalid mode. Only 2 or 4 allowed.')

        self.send(f":SYST:MOD:WIRE:MODE {slot},WIRE{mode}")
        return self.request("*OPC?")

    def get_wire_mode(self, slot: int) -> int:
        assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')

        response = self.request(f":SYST:MOD:WIRE:MODE? {slot}")
        return int(response)  # this is NOT safe!

# add more ...


class Hioki_BT3561A_20Channels(object):

    def __init__(self, BT_HOST, BT_PORT, SW_HOST, SW_PORT):
        self.bt = Hioki_BT3561A(BT_HOST, BT_PORT)
        self.sw = Hioki_SW1001(SW_HOST, SW_PORT)

    def measure_channel(self, chan):
        pass







# END OF FILE
