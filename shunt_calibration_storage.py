from typing import Tuple
import struct
from time import sleep
from i2c.eeprom_at24hc02c import AT24HC02C


class ShuntCalibrationStorageReadError(Exception):
    def __init__(self, i2c_address_7bit: int):
        self.i2c_address_7bit = i2c_address_7bit

    def __str__(self):
        return f"Error while reading shunt calibration value from EPPROM at 0x{self.i2c_address_7bit:02X}. " \
               f"Number of retries exceeded."


class ShuntCalibrationStorage:
    """A class that can access EEPROM storage via I2C (AT24HC02C) and store and load a resistance value in it.
    The resistance is stored with double-precision which can hold ca. 16 significant digits.
    The default 7-bit i2c address is 0x50.
    """
    page_list = [0, 1, 2]  # The calibration value will be stored on multiple pages for validation
    struct_format_string = ">d"  # big-endian, double with 8 bytes

    def __init__(self, i2c_port, i2c_address_7bit: int = 0x50):
        self.i2c_port = i2c_port
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.eeprom = AT24HC02C(self.i2c_port, self.i2c_address_7bit)

    def store_shunt_resistance_ohm(self, resistance_ohm: float) -> bool:
        """Store the resistance value in EEPROM and return whether it was successful.

        The value is stored with double-precision (ca. 16 significant digits).

        Args:
            resistance_ohm (float): The resistance to store in Ohm.

        Returns:
            bool: True if the readback was correct. False else.
        """
        resistance_ohm = float(resistance_ohm)
        return self.__store_calibration_value(resistance_ohm)

    def load_shunt_resistance_ohm(self, num_of_tries_left: int = 3) -> float:
        """Read the resistance value from EEPROM and return it as a float in Ohm.

        Returns:
            float: Resistance in Ohm
        """
        num_of_tries_left = int(num_of_tries_left)
        while num_of_tries_left > 0:
            result = self.__read_calibration_value()
            if result[0]:
                return result[1]
            else:
                num_of_tries_left -= 1
                sleep(0.1)
        raise ShuntCalibrationStorageReadError(self.i2c_address_7bit)

    def __store_calibration_value(self, value: float) -> bool:
        # Pack the value into a bytearray with the format specifier from the class variable
        value_bytearray = bytearray(struct.pack(ShuntCalibrationStorage.struct_format_string, value))

        # Store the packed value on multiple pages for validation
        for page in ShuntCalibrationStorage.page_list:
            self.eeprom.write_page(page, value_bytearray)
            self.eeprom.wait_after_write()

        # Perform a readback to verify the write operation
        read_back = self.__read_calibration_value()
        if read_back[0] and value == read_back[1]:
            return True
        else:
            return False

    def __read_calibration_value(self) -> Tuple[bool, int]:
        read_set = set()
        # The value has been stored on multiple pages to validate it when read out.
        # Read the content of each page, unpack it and store it in a set
        for page in ShuntCalibrationStorage.page_list:
            read_back = self.eeprom.read_page(page)
            unpacked = struct.unpack(ShuntCalibrationStorage.struct_format_string, read_back)[0]
            read_set.add(unpacked)

        # If we read the same value from each page, the set will have a length of 1 (Sets can't have duplicates)
        if len(read_set) == 1:
            return True, read_set.pop()
        else:
            return False, 0

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from i2c.ncd_eth_i2c_interface import I2CPort


# END OF FILE
