from eeprom_at24hc02c import AT24HC02C
import struct
from time import sleep


class ShuntCalibrationStorageReadError(Exception):
    def __init__(self, i2c_address_7bit: int):
        self.i2c_address_7bit = i2c_address_7bit

    def __str__(self):
        return f"Error while reading shunt calibration value from EPPROM at 0x{self.i2c_address_7bit:02X}. " \
               f"Number of retries exceeded."


class ShuntCalibrationStorage:
    """A class that can access EEPROM storage via I2C and store and load a resistance value in it."""
    page_list = [0, 1, 2]  # The calibration value will be stored on multiple pages for validation
    struct_format_string = ">Q"  # big-endian, unsigned long long with 8 bytes
    storage_factor = 1000000  # Resistance is stored in µOhm.

    def __init__(self, i2c_port, i2c_address_7bit: int):
        self.i2c_port = i2c_port
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.eeprom = AT24HC02C(self.i2c_port, self.i2c_address_7bit)

    def store_shunt_resistance(self, resistance_ohm: float) -> bool:
        """Store the resistance value in EEPROM and return whether it was successful.

        Args:
            resistance_ohm (float): The resistance to store in Ohm.

        Returns:
            bool: True if the readback was correct. False else.
        """
        resistance_uohm_int = int(round((resistance_ohm * ShuntCalibrationStorage.storage_factor), 0))

        return self.__store_calibration_value(resistance_uohm_int)

    def load_shunt_resistance_ohm(self, retries: int = 3) -> float:
        """Read the resistance value from EEPROM and return as a float in Ohm.

        Returns:
            float: Resistance in Ohm
        """
        retries = int(retries)
        while retries > 0:
            result = self.__read_calibration_value()
            if result[0]:
                return result[1] / ShuntCalibrationStorage.storage_factor  # Normal division will always return a float in Python 3
            else:
                retries -= 1
                sleep(0.1)
        raise ShuntCalibrationStorageReadError(self.i2c_address_7bit)

    def __store_calibration_value(self, value: int) -> bool:
        value = int(value)
        value_bytearray = bytearray(struct.pack(ShuntCalibrationStorage.struct_format_string, value))

        for page in ShuntCalibrationStorage.page_list:
            self.eeprom.write_page(page, value_bytearray)
            self.eeprom.wait_after_write()

        read_back = self.__read_calibration_value()
        if read_back[0] and value == read_back[1]:
            return True
        else:
            return False

    def __read_calibration_value(self) -> (bool, int):
        read_set = set()
        for page in ShuntCalibrationStorage.page_list:
            read_back = self.eeprom.read_page(page)
            read_set.add(struct.unpack(ShuntCalibrationStorage.struct_format_string, read_back))

        if len(read_set) == 1:  # Check if all items in read_set are the same. (Sets can't have duplicates)
            return True, read_set.pop()
        else:
            return False, 0
