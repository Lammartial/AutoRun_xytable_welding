from typing import List

class I2CBase:
    """An abstract I²C Interface class.

    Do NOT instantiate directly.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def open(self):
        pass

    def close(self):
        pass

    def writeto(self, i2c_address: int, data: bytearray) -> int:
        """Send a bytearray (up to 100 bytes) to the specified I2C address and return the number of sent bytes.

        Args:
            i2c_address (int): I2C address of the target device
            data (bytearray): array of bytes that should be sent. Up to 100 bytes.

        Returns:
            int: Number of sent bytes.

        """
        pass

    def readfrom(self, i2c_address: int, size: int) -> bytearray:
        """Read the specified amount of bytes (up to 100) from the device.

        Args:
            i2c_address (int): I2C address of the target device
            size (int): number of bytes to read. Up to 100

        Returns:
            bytearray: bytes read from the device
        """
        pass

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
        pass

    def i2c_bus_scan(self) -> List[int]:
        """Scan the bus for devices and return a list of their addresses."""
        pass



# END OF FILE