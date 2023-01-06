from typing import Tuple
import struct
from time import sleep
from eeprom_at24hc02c import AT24HC02C


class ShuntCalibrationStorageReadError(Exception):
    def __init__(self, i2c_port, i2c_address_7bit: int, what: str):
        self.i2c_port = i2c_port
        self.i2c_address_7bit = i2c_address_7bit
        self.what = what

    def __str__(self):
        return f"Error while reading the {self.what} from EPPROM at {self.i2c_port.description_string(self.i2c_address_7bit)}. " \
               f"The {self.what} could not be clearly read. You can try again, but it looks like you have to reprogram" \
               f"the {self.what}."


class ShuntCalibrationStorage:
    """A class that can access EEPROM storage via I2C (AT24HC02C) and store and load a resistance value and an
    inventory number in it.
    The resistance is stored with double-precision which can hold ca. 16 significant digits.
    The inventory number can contain up to 8 ASCII characters without a null terminator.
    The default 7-bit i2c address is 0x50.
    """
    page_list_resistance = [0, 1, 2]  # The calibration value will be stored on multiple pages for validation
    page_list_inventory_number = [3, 4, 5]
    struct_format_string_resistance = ">d"  # big-endian, double with 8 bytes
    struct_format_string_inventory_number = ">8s"  # big-endian, 8 byte string

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
        raise ShuntCalibrationStorageReadError(self.i2c_port, self.i2c_address_7bit, "shunt resistance")

    def store_inventory_number(self, inventory_number: str) -> bool:
        """Store the inventory number in EEPROM and return whether it was successful.

        The value is stored as an 8 character ASCII string without null terminator.

        Args:
            inventory_number (str): The inventory number.

        Returns:
            bool: True if the readback was correct. False else.
        """
        inventory_number = str(inventory_number).strip()
        return self.__store_inventory_number(inventory_number)

    def load_inventory_number(self, num_of_tries_left: int = 3) -> str:
        """Read the inventory number from EEPROM and return it as a string.

        Returns:
            str: Inventory number
        """
        num_of_tries_left = int(num_of_tries_left)
        while num_of_tries_left > 0:
            result = self.__read_inventory_number()
            if result[0]:
                return result[1]
            else:
                num_of_tries_left -= 1
                sleep(0.1)
        raise ShuntCalibrationStorageReadError(self.i2c_port, self.i2c_address_7bit, "inventory number")

    def __store_calibration_value(self, value: float) -> bool:
        # Pack the value into a bytearray with the format specifier from the class variable
        value_bytearray = bytearray(struct.pack(ShuntCalibrationStorage.struct_format_string_resistance, value))

        # Store the packed value on multiple pages for validation
        for page in ShuntCalibrationStorage.page_list_resistance:
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
        for page in ShuntCalibrationStorage.page_list_resistance:
            read_back = self.eeprom.read_page(page)
            unpacked = struct.unpack(ShuntCalibrationStorage.struct_format_string_resistance, read_back)[0]
            read_set.add(unpacked)

        # If we read the same value from each page, the set will have a length of 1 (Sets can't have duplicates)
        if len(read_set) == 1:
            return True, read_set.pop()
        else:
            return False, 0

    def __store_inventory_number(self, value: str) -> bool:
        if len(value) > struct.calcsize(ShuntCalibrationStorage.struct_format_string_inventory_number):
            raise ValueError(f"The inventory number for EEPROM at {self.i2c_port.description_string(self.i2c_address_7bit)} is too long. "
                             f"It can be at most 8 characters long. You used {len(value)} characters: \"{value}\"")

        value = value.encode("ascii")
        # Pack the value into a bytearray with the format specifier from the class variable
        try:
            value_bytearray = bytearray(struct.pack(ShuntCalibrationStorage.struct_format_string_inventory_number, value))
        except UnicodeEncodeError:
            raise ValueError(f"Inventory number for EEPROM at {self.i2c_port.description_string(self.i2c_address_7bit)} contains illegal characters."
                             f"It can only contain ASCII-characters. You used: \"{value}\".")

        # Store the packed value on multiple pages for validation
        for page in ShuntCalibrationStorage.page_list_inventory_number:
            self.eeprom.write_page(page, value_bytearray)
            self.eeprom.wait_after_write()

        # Perform a readback to verify the write operation
        read_back = self.__read_inventory_number()
        if read_back[0] and value == read_back[1]:
            return True
        else:
            return False

    def __read_inventory_number(self) -> Tuple[bool, str]:
        read_set = set()
        # The value has been stored on multiple pages to validate it when read out.
        # Read the content of each page, unpack it and store it in a set
        for page in ShuntCalibrationStorage.page_list_inventory_number:
            read_back = self.eeprom.read_page(page)
            read_back = read_back[:8]
            unpacked = struct.unpack(ShuntCalibrationStorage.struct_format_string_inventory_number, read_back)[0]
            read_set.add(unpacked)

        # If we read the same value from each page, the set will have a length of 1 (Sets can't have duplicates)
        if len(read_set) == 1:
            return True, read_set.pop().decode("ascii").strip("\0")  # decode and remove \0 manually
        else:
            return False, ""

# --------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    from ncd_eth_i2c_interface import I2CPort
    from smbus import BusMux_PCA9548A
    i2c_port = I2CPort("192.168.1.119")
    # print(i2c_port.i2c_bus_scan())
    mux = BusMux_PCA9548A(i2c_port)
    mux.setChannel(1)
    storage = ShuntCalibrationStorage(i2c_port)
    test_value = 3.1415
    inv = "1234567"

    storage.store_shunt_resistance_ohm(0.0)
    sleep(0.5)
    storage.store_inventory_number("0000000")
    sleep(0.5)

    readback = storage.load_shunt_resistance_ohm()
    readback_inv = storage.load_inventory_number()
    if test_value == readback:
        print("Shunt Success!")
    else:
        print(f"Shunt FAIL! test_value: {test_value}  Readback: {readback}")

    if inv == readback_inv:
        print("Inv Success!")
    else:
        print(f"Inv FAIL! test_value: {inv}  Readback: {readback_inv}")

    # storage.store_shunt_resistance_ohm(test_value)
    # sleep(0.5)
    # storage.store_inventory_number(inv)
    # sleep(0.5)


# END OF FILE
