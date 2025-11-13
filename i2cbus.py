""" I²C bus mux devices which select a channel by communication."""
__author__ = "Markus Ruth"
__version__ = "1.0.0"

from typing import Tuple, List
import errno
from rrc.eth2i2c import I2CBase


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- ##


class BusMux:

    def __init__(self, i2c: I2CBase, address: int = 0x70):
        """Bus multiplexer control with one PCA9548A IC to mux 1 to 8.

        Controls the 8-channel I2C switch connected on the same I2C bus like PCA9548A.
        Multiplexes a I²C bus, e.g. 1 out of 8 depending on the selected channel.
        Handles consecutive device addresses for numbers > 8
        After start no channel is selected (=blocked).
        The channels are numbered 1 to 8
        Use .setChannel and .resetChannel to enable or disable a single channel.
        Use .getChannels to get a list of all enabled channels

        Args:
            i2c (I2C instance): Any I2C bus (Soft or Hard)
            address (Byte, optional): Device slave address on the bus. Defaults to 0x70.
        """
        self.i2c = i2c
        self.address = int(address)
        self.current_mask = 0x00  # shadow register; initial value after reset -> no channels active

    def __str__(self) -> str:
        return f"I²C bus MUX on bus {self.i2c} having slave address of 0x{(self.address & 0xff):02X}, channel mask 0x{(self.current_mask & 0xff):02X}"

    def __repr__(self) -> str:
        return f"BusMux({repr(self.i2c)}, {self.address})"

    #----------------------------------------------------------------------------------------------

    def isReady(self):
        """Checks if the MUX' slave address is being ACK'd on bus.

        Returns:
            Boolean: True if address was ACK'd, else False
        """
        # return self.i2c.is_ready(self.address)
        isready = False
        try:
            _ = self.i2c.readfrom(self.address, 0)
            isready = True
        except OSError as ex:
            if (ex.args[0] == errno.ENODEV) or (ex.args[0] == errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                pass
            else:
                # forward this exception
                raise ex
        return isready

    def setChannelMask(self, mask: int) -> bool:
        new_mask = int(mask) & 0xFF
        # try to set the new channel mask (may throw OSError exception!)
        ok = (1 == self.i2c.writeto(self.address, bytearray([new_mask])))
        if ok:
            self.current_mask = new_mask  # update shadow register
        return ok

    def getChannelMask(self) -> int:
        return int(self.current_mask)  # work with shadow only


    def reset(self) -> bool:
        """Disable ALL channels"""
        return self.setChannelMask(0x00)
   

    def getChannels(self) -> Tuple[int]:
        mask = self.current_mask  # work with shadow only
        channels = []
        for i in range(8):
            if mask & 1 << i:
                channels.append(i+1)
        return channels

    def resetChannel(self, number: int) -> bool:
        number = int(number)
        if number < 1 or number > 8:
            return False
        mask = self.current_mask & ~(1 << ((number - 1) & 0x07)) # un-select the channel
        if self.current_mask == mask:
            return True  # channel already deactivated
        return self.setChannelMask(mask)

    def setChannel(self, number: int) -> bool:
        """Switches the I²C bus to the selected channel.

        Args:
            number (int): Channel number to select 1..8 as only active channel.
                          Will be written to the bus only if is is different to the already selecetd channel.
        Raises:
            OSError: on Errors from I²C functions.

        Returns:
            Boolean: True if successfully written, False else
        """
        number = int(number)
        if number < 1 or number > 8:
            return False
        mask = 1 << ((number - 1) & 0x07)  # select the channel in the IC
        if self.current_mask == mask:
            return True  # channel already active
        return self.setChannelMask(mask)


# --------------------------------------------------------------------------- #


class MultiBusMux:

    def __init__(self, i2c: I2CBase, base_address: int = 0x70, number_of_busses: int = 1):
        """Bus multiplexer control with one up to eight PCA9548A ICs to mux one bus to many.

        Multiplexes a I²C bus, e.g. 1 out of 8 depending on the selected channel.
        Handles consecutive device addresses divided into 8 per device.
        After start no channel is selected (=blocked).

        Max number of busses is therefor 8 x 8 = 64.

        Args:
            i2c (I2C instance): Any I2C bus (Soft or Hard)
            base_address (Byte, optional): Slave address of first bus mux. Defaults to 0x70.
            busses (int, optional): Max available busses
        """

        self.muxes = [BusMux(i2c, address=base_address + n) for n in range(number_of_busses)]
        self.current_channel = -1
        self.max_channel = number_of_busses * 8

    def reset(self) -> bool:
        # disable ALL muxes
        ok = True
        for m in self.muxes:
            ok = ok and m.reset()
        return ok
    

    def get_mux(self, mux: int) -> BusMux:
        mux = int(mux)  # this is for TestStand
        if mux < 1 or mux > len(self.muxes):
            raise ValueError(f"Parameter 'number' must be in 1 and {len(self.muxes)}")
        return self.muxes[mux - 1]

    def _number_to_mux_and_channel(self, number: int) -> Tuple[int, int]:
        number = int(number)  # this is for TestStand
        if (number < 1) or (number > self.max_channel):
            raise ValueError(f"Parameter 'number' must be in 1 and {len(self.muxes)}")
        _mux = int((number - 1) / 8)  # !! channels are counted 1..8 for selection, not 0..7 !!
        _ch = number - (_mux * 8)     # !! channels are counted 1..8 for selection, not 0..7 !!
        return _mux, _ch

    def setChannel(self, number: int) -> bool:
        """Switches the I²C bus to the selected channel.

        Args:
            number (int): Channel number to select 0..n. Will be written to the bus only if is is different to the already selecetd channel.
                          A negative number will select no channel effectively block the I²C.
        Raises:
            OSError: on Errors from I²C functions.

        Returns:
            Boolean: True if successfully written, False else
        """

        number = int(number)  # this is for TestStand
        if self.current_channel == number:
            return True  # nothing changed -> save time
        _mux, _channel = self._number_to_mux_and_channel(number)  # may throw
        return self.muxes[_mux].setChannel(_channel)

    def resetChannel(self, number: int) -> bool:
        """Disconnects the I²C bus from the selected channel.

        Args:
            number (int): Channel number to select 0..n. Will be written to the bus only if is is different to the already selecetd channel.
                          A negative number will select no channel effectively block the I²C.
        Raises:
            OSError: on Errors from I²C functions.

        Returns:
            Boolean: True if successfully written, False else
        """
        number = int(number)  # this is for TestStand
        if number == 0:
            return self.reset()  # open ALL
        _mux, _channel = self._number_to_mux_and_channel(number)  # may throw
        return self.muxes[_mux].resetChannel(_channel)

# --------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------

class I2CBus(I2CBase):
    """Plain bus - either it is a built in or you should use interface specific."""
    pass


# --------------------------------------------------------------------------------------------------

class I2CMuxedBus(I2CBase):
    """
    Class that handles a bus connected I2C bus mux to select a channel
    before executing a read or write.
    You can use either a BusMux() or MultiBusMux() class as handler.
    """

    def __init__(self, i2c: I2CBase, mux: BusMux, channel: int):
        """Class that handles a bus connected I2C bus mux to select a channel
        before executing a read or write.

        Args:
            i2c (I2CBase): plain I2C bus
            mux (BusMux): BusMux device instance which has interface and slave address set.
            channel (int): the channel 1..n to select this bus
        """
        super().__init__()  # I just need the interface functions here
        self.i2c = i2c  # we use a separate i2c bus instance for real execution
        self.mux = mux
        self.channel = int(channel)

    def __str__(self) -> str:
        return f"I²C bus {self.i2c} using channel {self.channel} which translates to {self.mux}"

    def __repr__(self) -> str:
        return f"I2CMuxedBus({repr(self.i2c)}, {repr(self.mux)}), {self.channel})"

    #----------------------------------------------------------------------------------------------

    def writeto(self, i2c_address: int, data: bytearray) -> int:
        """Send a bytearray (up to 100 bytes) to the specified I2C address and return the number of sent bytes.

        Args:
            i2c_address (int): I2C address of the target device
            data (bytearray): array of bytes that should be sent. Up to 100 bytes.

        Returns:
            int: Number of sent bytes.

        """
        self.mux.setChannel(self.channel)
        return self.i2c.writeto(int(i2c_address), data)

    def readfrom(self, i2c_address: int, size: int) -> bytearray:
        """Read the specified amount of bytes (up to 100) from the device.

        Args:
            i2c_address (int): I2C address of the target device
            size (int): number of bytes to read. Up to 100

        Returns:
            bytearray: bytes read from the device
        """

        self.mux.setChannel(self.channel)
        return self.i2c.readfrom(int(i2c_address), int(size))

    def readfrom_mem(self, i2c_address: int, data: bytearray, size: int, delay_ms: int = 0) -> bytearray:
        """Send data to the device, perform a repeated start condition and read a specified amount of bytes.

        Args:
            i2c_address (int): I2C address of the target device
            data (bytearray): array of bytes that should be sent. Up to 16 bytes.
            size (int): number of bytes to read.
            delay_ms (int): Delay in ms between writing and reading data.

        Returns:
            bytearray: bytes read from the device

        """

        self.mux.setChannel(self.channel)
        return self.i2c.readfrom_mem(i2c_address, data, int(size), delay_ms=int(delay_ms))

    def i2c_bus_scan(self) -> List[int]:
        """Scan the bus for devices and return a list of their addresses."""

        self.mux.setChannel(self.channel)
        return self.i2c.i2c_bus_scan()


    def i2c_change_clock_frequency(self, frequency_hz: int, timeout_ms: int = 20) -> bool:
        """Change the I2C clock frequency of the underlying bus.

        Args:
            frequency_hz (int): New clock frequency in Hz
            timeout_ms (int, optional): Timeout in ms for the operation. Defaults to 20.

        Returns:
            bool: True if successfully changed, False else
        """

        ok1 = self.mux.reset() # disable all channels first
        ok2 = self.i2c.i2c_change_clock_frequency(frequency_hz, timeout_ms=timeout_ms)        
        return ok1 and ok2



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import I2CBus
    from rrc.smbus import BusMaster as SMBusMaster

    ## Initialize the logging
    logger_init(filename_base="local_log")  ## init root logger
    _log = getLogger(__name__, DEBUG)

    ncd = I2CPort("172.21.101.21:2101")
    #i2c = I2CBus(ncd)
    #bus = SMBusMaster(ncd)
    #_log.info(bus.isReady(0x77))
    mux = BusMux(ncd, address=0x77)

    for n in range(1,9):
        mux.setChannel(n)
        print(ncd.i2c_bus_scan())

    # mux.setChannel(1)
    # _log.info(mux.getChannels())
    # _log.info(bus.readWord(0x0b,0x09))
    # mux.reset()
    # # check if the mux-automatic works also
    # muxbus = I2CMuxedBus(ncd, bus, 1)
    # smbus = SMBusMaster(muxbus)
    # _log.info(smbus.readWord(0x0b,0x09))
    pass

# END OF FILE