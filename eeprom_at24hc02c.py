from time import sleep
from rrc.i2cbus import I2CBase


class AT24HC02C:
    """A class to control the AT24HC02C 256 byte I2C EEPROM by Microchip.

    https://www.microchip.com/en-us/product/AT24HC02C
    The memory size is 256 bytes. It is organized into 32 pages of 8 bytes each.
    A single write operation must stay within one page. I.e. At most 8 bytes can
    be written per write operation.
    Reading can be performed without page limitations.
    The default 7-bit i2c address is 0x50.
    """
    max_write_time_s = 0.005
    memory_size = 256
    number_of_pages = 32
    bytes_per_page = 8

    def __init__(self, i2c: I2CBase, i2c_address_7_bit: int = 0x50):
        self.i2c = i2c
        self.i2c_address_7bit = int(i2c_address_7_bit)

    def __str__(self) -> str:
        return f"AT24HC02C EEPROM device with address {self.i2c_address_7bit:02x} on {self.i2c}"

    def __repr__(self) -> str:
        return f"AT24HC02C({repr(self.i2c)}, i2c_address_7bit={self.i2c_address_7bit})"

    #----------------------------------------------------------------------------------------------

    def read_bytes(self, word_address: int, number_of_bytes: int) -> bytearray:
        """Read number_of_bytes starting at word_address and return them.

        Args:
            word_address (int): Starting address for the read operation. Must be between 0 and 255.
            number_of_bytes (int): Number of bytes that should be read. Must be between 0 and 255.

        Raises:
            ValueError: If word_address or number_of_bytes is invalid.

        Returns:
            bytearray: Bytes returned from the EEPROM memory.
        """
        word_address = int(word_address)
        number_of_bytes = int(number_of_bytes)
        if number_of_bytes < 0 or number_of_bytes > (AT24HC02C.memory_size - 1):
            raise ValueError(f"Number of bytes to read for I2C EEPROM at address 0x{self.i2c_address_7bit:02X} is "
                             f"invalid. Must be between 0 and {AT24HC02C.memory_size - 1}. You selected {number_of_bytes}.")
        self.__validate_word_address(word_address)

        # We are splitting up write and read because the NCD ETH-I2C converter can only read up to 16 bytes in a
        # write-read operation, but can read up to 100 bytes in a read-only operation.
        self.i2c.writeto(self.i2c_address_7bit, bytearray([word_address]))
        return self.i2c.readfrom(self.i2c_address_7bit, number_of_bytes)

    def read_page(self, page) -> bytearray:
        """Read 8 bytes from the specified page and return them.

        Args:
            page (int): Index of the page to read. Must be between 0 and 31.

        Returns:
            bytearray: 8 bytes from the specified page.
        """
        page = int(page)
        self.__validate_page_number(page)
        word_address = self.__get_address_for_page(page)
        self.__validate_word_address(word_address)

        return self.read_bytes(word_address, AT24HC02C.bytes_per_page)

    def write_bytes(self, word_address: int, data: bytearray) -> bool:
        """Write the bytes in data to word_address. Then return whether the readback was correct.

        The data can be at most 8 bytes long and must all be on the same memory page.
        This function also performs a sleep of 5 ms between write and readback to allow the EEPROM to write the data.

        Args:
            word_address (int): Starting address for the read operation. Must be between 0 and 255.:
            data (bytearray): Data that should be sent. At most 8 bytes (size of one page).

        Returns:
            bool: True if the readback was correct. False else.
        """
        word_address = int(word_address)
        self.__validate_word_address(word_address)

        if not self.__data_fits_in_page_boundaries(word_address, len(data)):
            raise ValueError(f"Data does not fit into page for I2C EEPROM at address 0x{self.i2c_address_7bit:02X}. "
                             f"Data start address: {word_address}, data length: {len(data)}.")

        self.i2c.writeto(self.i2c_address_7bit, (bytearray([word_address]) + data))
        self.wait_after_write()

        read_back = self.read_bytes(word_address, len(data))
        if read_back == data:
            return True
        else:
            return False

    def write_page(self, page: int, data: bytearray) -> bool:
        """Write up to 8 bytes to the specified page. Then return whether the readback was correct.

        Args:
            page (int): Index of the page to read. Must be between 0 and 31.
            data (bytearray): Data that should be written to the page. At most 8 bytes long.

        Raises:
            ValueError: If data is too long.

        Returns:
            bool: True if the readback was correct. False else.
        """
        page = int(page)
        self.__validate_page_number(page)
        word_address = self.__get_address_for_page(page)
        self.__validate_word_address(word_address)
        if len(data) > AT24HC02C.bytes_per_page:
            raise ValueError(f"Data is too long for page write on I2C EEPROM at address 0x{self.i2c_address_7bit:02X}. "
                             f"Can be at most {AT24HC02C.bytes_per_page} bytes. Your data is {len(data)} bytes long.")

        return self.write_bytes(word_address, data)

    def wait_after_write(self):
        sleep(AT24HC02C.max_write_time_s)

    def __get_address_for_page(self, page: int) -> int:
        """Page address = page index * bytes per page"""
        return page * AT24HC02C.bytes_per_page

    def __data_fits_in_page_boundaries(self, start_address: int, data_length: int) -> bool:
        """Return true if a number of bytes written to start_address will fit on the same page.

        All address where Bits 3 to 7 are the same lie on the same memory page. This is checked
        using the bit mask 0xF8 = 0b1111_1000.
        """
        end_address = start_address + data_length - 1
        if (start_address & 0xF8) == (end_address & 0xF8) and data_length <= AT24HC02C.bytes_per_page:
            return True
        else:
            return False

    def __validate_page_number(self, page: int):
        if page < 0 or page > (AT24HC02C.number_of_pages - 1):
            raise ValueError(f"Page number for I2C EEPROM at address 0x{self.i2c_address_7bit:02X} is invalid. "
                             f"Must be between 0 and 31. You selected {page}.")

    def __validate_word_address(self, word_address: int):
        if word_address < 0 or word_address > (AT24HC02C.memory_size - 1):
            raise ValueError(f"Word address for I2C EEPROM at address 0x{self.i2c_address_7bit:02X} is invalid. "
                             f"Must be between 0 and {AT24HC02C.memory_size - 1}. You selected {word_address}.")


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    pass

# END OF FILE