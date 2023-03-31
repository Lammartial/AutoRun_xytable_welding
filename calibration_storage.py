from typing import Tuple
import struct
from time import sleep
from rrc.eth2i2c import I2CBase
from rrc.eeprom_at24hc02c import AT24HC02C


class CalibrationStorageReadError(Exception):

    def __init__(self, eeprom: AT24HC02C, what: str):
        self.eeprom = eeprom
        self.what = what

    def __str__(self):
        return f"Error while reading the {self.what} from {self.eeprom}. " \
               f"The {self.what} could not be clearly read. You can try again, but it looks like you have to reprogram" \
               f"the {self.what}."


#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------

class CalibrationStorage:
    """
    A class that can access EEPROM storage via I2C (AT24HC02C) and store and load adapter 
    calibration values like: 
        inventory number
        shunt resistance
        leakage current 
    in it.
    The resistance and current is stored with double-precision which can hold ca. 
    16 significant digits.
    The inventory number can contain up to 8 ASCII characters without a null terminator.
    The default 7-bit i2c address is 0x50.
    Each value is stored on multiple pages for validation purposes.
    """

    page_list_resistance = [0, 1, 2]  # The calibration value will be stored on multiple pages for validation
    page_list_inventory_number = [3, 4, 5]
    page_list_leakcurrent_offset = [6, 7, 8]
    struct_format_string_resistance = ">d"  # big-endian, double with 8 bytes
    struct_format_string_inventory_number = ">8s"  # big-endian, 8 byte string
    struct_format_string_leakcurrent_offset = ">d"  # big-endian, double with 8 bytes

    def __init__(self, i2c: I2CBase, i2c_address_7bit: int = 0x50):
        self.eeprom = AT24HC02C(i2c, int(i2c_address_7bit))

    def __str__(self) -> str:
        return f"Shunt calibration storage class, using {self.eeprom}"

    def __repr__(self) -> str:
        return f"ShuntCalibrationStorage({repr(self.eeprom.i2c)}, i2c_address_7bit={self.eeprom.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def __store_value(self, value: float, format_string: str, page_list: list, verify: bool = True) -> bool:
        # Pack the value into a bytearray with the format specifier from the class variable
           # Pack the value into a bytearray with the format specifier from the class variable
        try:
            value_bytearray = bytearray(struct.pack(format_string, value))
        except UnicodeEncodeError:
            raise ValueError(f"Value for EEPROM at {self.eeprom.__repr__()} contains illegal characters."
                             f"It can only contain ASCII-characters. You used: \"{value}\".")

        # Store the packed value on multiple pages for validation
        for page in page_list:
            self.eeprom.write_page(page, value_bytearray)
            self.eeprom.wait_after_write()

        if verify:
            # Perform a readback to verify the write operation
            read_back = self.__read_value(format_string, page_list)
            if read_back[0] and value == read_back[1]:
                return True
            else:
                return False
        else:
            return True
        
    def __read_value(self, format_string: str, page_list: list) -> Tuple[bool, int | None]:
        read_set = set()
        # The value has been stored on multiple pages to validate it when read out.
        # Read the content of each page, unpack it and store it in a set
        for page in page_list:
            read_back = self.eeprom.read_page(page)
            unpacked = struct.unpack(format_string, read_back)[0]
            read_set.add(unpacked)

        # If we read the same value from each page, the set will have a length of 1 
        # (Sets can't have duplicates)
        if len(read_set) == 1:
            return True, read_set.pop()
        else:
            return False, None

    #----------------------------------------------------------------------------------------------

    def store_inventory_number(self, inventory_number: str) -> bool:
        """
        Store the inventory number in EEPROM and return whether it was successful.
        The value is stored as an 8 character ASCII string without null terminator.

        Args:
            inventory_number (str): The inventory number.

        Returns:
            bool: True if the readback was correct. False else.
        """

        inventory_number = str(inventory_number).strip()
        if len(inventory_number) > struct.calcsize(CalibrationStorage.struct_format_string_inventory_number):
            raise ValueError(f"The inventory number for EEPROM at {self.eeprom.__repr__()} is too long. "
                             f"It can be at most 8 characters long. You used {len(inventory_number)} characters: \"{inventory_number}\"")

        return self.__store_value(inventory_number.encode("ascii"), 
                                  CalibrationStorage.struct_format_string_inventory_number,
                                  CalibrationStorage.page_list_inventory_number,
                                  verify=True)

    def load_inventory_number(self) -> str:
        """Read the inventory number from EEPROM and return it as a string.

        Returns:
            str: Inventory number
        """
        ok, v = self.__read_value(CalibrationStorage.struct_format_string_inventory_number,
                                  CalibrationStorage.page_list_inventory_number)
        if ok:
            return v.decode("ascii").strip("\x00").strip("\xff")  # decode and remove \x00, \xff manually
        raise CalibrationStorageReadError(self.eeprom, "inventory number")


    def store_shunt_resistance_ohm(self, resistance_ohm: float) -> bool:
        """
        Store the resistance value in EEPROM and return whether it was successful.
        The value is stored with double-precision (ca. 16 significant digits).

        Args:
            resistance_ohm (float): The resistance to store in Ohm.

        Returns:
            bool: True if the readback was correct. False else.
        """

        return self.__store_value(float(resistance_ohm), 
                                  CalibrationStorage.struct_format_string_resistance,
                                  CalibrationStorage.page_list_resistance,
                                  verify=True)

    def load_shunt_resistance_ohm(self) -> float:
        """Read the resistance value from EEPROM and return it as a float in Ohm.

        Returns:
            float: Resistance in Ohm
        """

        ok, v = self.__read_value(CalibrationStorage.struct_format_string_resistance,
                                  CalibrationStorage.page_list_resistance)
        if ok:
            return v
        raise CalibrationStorageReadError(self.eeprom, "shunt resistance")


    def store_leakcurrent_amps(self, current_amps: float) -> bool:
        """
        Store the leakage current measurement in EEPROM and return whether it was successful.
        The value is stored with double-precision (ca. 16 significant digits).

        Args:
            resistance_ohm (float): The current to store in amps.

        Returns:
            bool: True if the readback was correct. False else.
        """
    
        return self.__store_value(float(current_amps), 
                                  CalibrationStorage.struct_format_string_leakcurrent_offset, 
                                  CalibrationStorage.page_list_leakcurrent_offset,
                                  verify=True)

    def load_leakcurrent_amps(self) -> float:
        """Read the resistance value from EEPROM and return it as a float in Ohm.

        Returns:
            float: Resistance in Ohm
        """

        ok, v = self.__read_value(CalibrationStorage.struct_format_string_leakcurrent_offset,
                                  CalibrationStorage.page_list_leakcurrent_offset)
        if ok:
            return v
        
        raise CalibrationStorageReadError(self.eeprom, "leakage current")


# --------------------------------------------------------------------------------------------------

def test_write_read(storage: CalibrationStorage):
    ohm = 3.1415
    inv = "1234567"
    amps = 0.000025

    storage.store_shunt_resistance_ohm(ohm)
    sleep(0.5)
    storage.store_inventory_number(inv)
    sleep(0.5)
    storage.store_leakcurrent_amps(amps)
    sleep(0.5)

    readback = storage.load_shunt_resistance_ohm()
    if ohm == readback:
        print("Shunt Success!")
    else:
        print(f"Shunt FAIL!")
    print(f"Test value: {ohm}  Readback: {readback}")

    readback = storage.load_inventory_number()    
    if inv == readback:
        print("Inv Success!")
    else:
        print(f"Inv FAIL!")
    print(f"Test value: {inv}  Readback: {readback}")

    readback = storage.load_leakcurrent_amps()    
    if amps == readback:
        print("Leakage offset Success!")
    else:
        print(f"Leakage offset FAIL!")
    print(f"Test value: {amps}  Readback: {readback}")

    # clear
    storage.store_shunt_resistance_ohm(0.0)
    storage.store_inventory_number("00000000")
    storage.store_leakcurrent_amps(0.0)

def test_print_stored_values(storage: CalibrationStorage):
    ohm = storage.load_shunt_resistance_ohm()
    inv = storage.load_inventory_number()
    amps = storage.load_leakcurrent_amps()
    print("Stored EEPROM Values:")
    print(ohm)
    print(inv)
    print(amps)


    
# --------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from rrc.eth2i2c import I2CPort
    from rrc.i2cbus import BusMux, I2CMuxedBus

    i2c = I2CPort("172.25.101.30:2101")  # 30 / 32 / 34
    # print(i2c_port.i2c_bus_scan())
    mux = BusMux(i2c, 0x77)
    bus = I2CMuxedBus(i2c, mux, 1)
    storage = CalibrationStorage(bus)

    #test_write_read(storage)
    
    test_print_stored_values(storage)

# END OF FILE
