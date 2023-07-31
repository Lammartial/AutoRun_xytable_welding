import socket
from time import sleep
from struct import pack
from rrc.eth2i2c.base import I2CBase
from rrc.eth2i2c.ncd_errors import *


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

# From internet:
# 100KHz: AA 06 BC 32 01 01 00 00 A0
# 38KHz:  AA 06 BC 32 01 01 00 01 A1
# 200KHz: AA 06 BC 32 01 01 00 02 A2
# 300KHz: AA 06 BC 32 01 01 00 03 A3
# 400KHz: AA 06 BC 32 01 01 00 04 A4
#         [AA bytecount][c1, c2, u1, u2, u3, u4][checksum]
#              API       payload

NCD_DEFAULT_TIMEOUT_S = 5

NCD_HEADER = 0xAA
NCD_I2C_WRITE = 0xBE
NCD_I2C_READ = 0xBF
NCD_I2C_WRITE_READ = 0xC0
NCD_I2C_BUS_SCAN = [0xC1, 0x00]
NCD_COMMAND_SUCCESSFULL = 0x55
NCD_ERROR_CODE_HEADER = 0xBC
NCD_ERROR_CODE_FOOTER = 0x43

NCD_I2C_READ_ERROR = 0x5B
NCD_I2C_WRITE_ERROR1 = 0x5A
NCD_I2C_WRITE_ERROR2 = 0x5C
NCD_I2C_NOT_IMPLEMENTED_ERROR = 0x5D
NCD_I2C_ACK_ERROR = 0x5E

NCD_PACKET_HEADER_INDEX = 0
NCD_PACKET_LENGTH_INDEX = 1
NCD_PACKET_DATA0_INDEX = 2
NCD_PACKET_CHECKSUM_INDEX = -1
NCD_PACKET_OVERHEAD = 3



class I2CPort(I2CBase):
    """A class to control the NCD Ethernet to I2C converter"""

    def __init__(self, resource_str: str, timeout_s: float = NCD_DEFAULT_TIMEOUT_S, open_connection: bool = True):
        """Initialize the object, establish the network connection and perform the selftest of the converter.

        Args:
            host (str): hostname IP address of the converter
            port (int): port used for the communication. Default setting is 2101.
            timeout_s (float, optional): Timeout for network communication in seconds. Defaults to 5s.
            open_connectuion (bool, optional): If True, the socket connection is opened on init(). Defaults to True.

        Raises:
            NCDSelfTestFailedError: Raised if the selftest of the converter fails.
        """
        self.socket = None
        _res = resource_str.split(":")
        self._host = _res[0]
        self._port = int(_res[1]) if len(_res) > 1 else int(2101)  # use default port
        self._open_connection = open_connection
        self.timeout_s = timeout_s
        self.ncd_interface_address = f"{self._host}:{self._port}"  # This the ip address ("192.168.1.61:2101"). Used in error messages.
        self.last_i2c_address = -1  # Used to remember which i2c_address_7bit was last spoken to if an error occurs.
        self.interface_is_rrc = False  # assume NCD original per default, changed by open() function
        if open_connection:
            self.open()

    def __str__(self) -> str:
        """Create a string that contains IP address, port and I2C address. Used for error messages.

        The string has the format "<ip address>:<port>:<i2c address>"
        Example: "192.168.1.56:2101:0x40"
        """
        return f"NCD ETH-to-I2C bridge at {self._host}:{self._port}:0x{(self.last_i2c_address & 0xff):02X}"

    def __repr__(self) -> str:
        return f"I2CPort({self.ncd_interface_address}, timeout_s={self.timeout_s}, open_connection={self._open_connection})"

    #----------------------------------------------------------------------------------------------

    def open(self) -> None:
        self.__connect_socket()
        #self.soft_reset()  # add to prevent any side effects from failed tests
        self.self_test()   # raises if anything wrong


    def close(self) -> None:
        try:
            self.socket.close()
        except AttributeError:
            # self.socket could be None
            pass


    def __enter__(self) -> object:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __connect_socket(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout_s)
        try:
            self.socket.connect((self._host, self._port))
        except TimeoutError:
            raise NCDCantFindInterface(self.ncd_interface_address)


    def soft_reset(self) -> None:
        # from AlphaStation sources
        if self.__data_exchange(bytes([0xFE, 0x21, 0xBC])) != bytes([0x55]):
            raise NCDError(self)


    def hard_reset(self) -> None:
        # from AlphaStation sources
        if self.__data_exchange(bytes([0xFE, 0x21, 0xBD])) != bytes([0x55]):
            raise NCDError(self)


    def self_test(self) -> None:
        """Perform the 2-way self test of the converter and checks for API.

        Raises:
            NCDSelfTestFailedError: Raised if the selftest of the converter fails.
        """

        # Test command has the payload 0xFE 0x21.
        #   Response from NCD.io should be 0x55
        #   Response from RRC OLIMEX should be 0x55,0x42
        _response = self.__data_exchange(bytes([0xFE, 0x21]))
        if _response == bytes([0x55, 0x42]):
            self.interface_is_rrc = True  # RRC OLIMEX board
        elif _response == bytes([0x55]):
            self.interface_is_rrc = False  # NCD.io board
        else:
            # no valid result
            raise NCDSelfTestFailedError(self)


    def writeto(self, i2c_address_7bit: int, data: bytearray) -> int:
        """Send a bytearray (up to 100/255 bytes NCD/RRC) to the specified I2C address and return the number of sent bytes.

        Args:
            i2c_address_7bit (int): 7-bit I2C address of the target device
            data (bytearray): array of bytes that should be sent. Up to 100 bytes.

        Returns:
            int: Number of sent bytes.

        Raises:
            InvalidI2CAddressError: If the I2C address is invalid.
            InvalidParametersError: If the length of data is invalid. (> 100)
        """
        i2c_address_7bit = int(i2c_address_7bit)
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise NCD_I2CInvalidAddressError(i2c_address_7bit, self)
        if (not self.interface_is_rrc and (len(data) > 100)) or (self.interface_is_rrc and (len(data) > 255)):
            raise NCD_I2CInvalidParametersError(i2c_address_7bit, self)

        self.last_i2c_address = i2c_address_7bit
        tx_payload = bytes([NCD_I2C_WRITE, i2c_address_7bit]) + data
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        if rx_payload[0] == NCD_COMMAND_SUCCESSFULL:  # Command successful
            return len(data)
        else:
            return 0


    def readfrom(self, i2c_address_7bit: int, size: int) -> bytearray:
        """Read the specified amount of bytes (up to 100) from the device.

        Args:
            i2c_address_7bit (int): 7-bit I2C address of the target device
            size (int): number of bytes to read. Up to 100

        Returns:
            bytearray: bytes read from the device

        Raises:
            InvalidI2CAddressError: If the I2C address is invalid.
            InvalidParametersError: If size is invalid. (<= 0 or > 100)
        """
        i2c_address_7bit = int(i2c_address_7bit)
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise NCD_I2CInvalidAddressError(i2c_address_7bit, self)
        if (size <= 0) or ((not self.interface_is_rrc and (size > 100)) or (self.interface_is_rrc and (size > 255))):
            raise NCD_I2CInvalidParametersError(i2c_address_7bit, self)

        self.last_i2c_address = i2c_address_7bit
        tx_payload = bytes([NCD_I2C_READ, i2c_address_7bit, size])
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return bytearray(rx_payload)


    def readfrom_mem(self, i2c_address_7bit: int, data: bytearray, size: int, delay_ms: int = 0) -> bytearray:
        """Send data to the device, perform a repeated start condition and read a specified amount of bytes.

        Args:
            i2c_address_7bit (int): 7-bit I2C address of the target device
            data (bytearray): array of bytes that should be sent. Up to 16 bytes.
            size (int): number of bytes to read. Up to 255.
            delay_ms (int): Delay in ms between writing and reading data.

        Returns:
            bytearray: bytes read from the device

        Raises:
            InvalidI2CAddressError: If the I2C address is invalid.
            InvalidParametersError: If size is invalid. (<= 0 or >100 on NCD or >255 on RRC)
        """
        i2c_address_7bit = int(i2c_address_7bit)
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise NCD_I2CInvalidAddressError(i2c_address_7bit, self)

        if isinstance(data, int):
            data = bytearray([data])

        if len(data) <= 0 or len(data) > 16:
            raise NCD_I2CInvalidParametersError(i2c_address_7bit, self)

        if (not self.interface_is_rrc) and (size > 16):
            # the NCD ETH-I2C converter can only read up to 16 bytes in a
            # write-read operation, but can read up to 100 bytes in a read-only operation.
            # Size checks are done in these functions, so no need to check sizes here.
            # -> so transform into single write then read
            self.writeto(i2c_address_7bit, data)
            return self.readfrom(i2c_address_7bit, size)

        # RRC implmentation
        if (size < 0) or (size > 255):
            raise NCD_I2CInvalidParametersError(i2c_address_7bit, self)

        self.last_i2c_address = i2c_address_7bit
        tx_payload = bytes([NCD_I2C_WRITE_READ, i2c_address_7bit, size, delay_ms]) + data
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return bytearray(rx_payload)


    def i2c_bus_scan(self):
        """Scan the bus for devices and return a list of their addresses."""
        tx_payload = bytes(NCD_I2C_BUS_SCAN)
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return list(rx_payload)


    def i2c_change_clock_frequency_ncd(self, frequency: int) -> list:
        # From internet:
        # 100KHz: AA 06 BC 32 01 01 00 00 A0
        # 38KHz:  AA 06 BC 32 01 01 00 01 A1
        # 200KHz: AA 06 BC 32 01 01 00 02 A2
        # 300KHz: AA 06 BC 32 01 01 00 03 A3
        # 400KHz: AA 06 BC 32 01 01 00 04 A4
        #         [AA bytecount][c1, c2, u1, u2, u3, u4][checksum]
        #              API       payload
        # AA=170, BC=188
        tx_payload = bytes([0xBC,0x32,0x01,0x01,0x00])
        if   frequency ==  38000: tx_payload += bytes([0x01])
        elif frequency == 200000: tx_payload += bytes([0x02])
        elif frequency == 300000: tx_payload += bytes([0x03])
        elif frequency == 400000: tx_payload += bytes([0x04])
        else: tx_payload += bytes([0x00])
        rx_payload = self.__data_exchange(tx_payload)
        #_log = getLogger(__name__, DEBUG)
        #_log.info(rx_payload)
        self.__check_for_errors(rx_payload)
        return list(rx_payload)


    def i2c_change_clock_frequency(self, frequency: int, timeout_ms: int = None) -> list:
        # RRC specific function !
        tx_payload = bytes([0xCF]) \
                        + pack(">L", frequency) \
                        + (pack(">L", timeout_ms) if timeout_ms else bytes())  # to 32 bit unsigned each
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return list(rx_payload)


    # -------------------------------------------------------------------------
    # internal functions
    # -------------------------------------------------------------------------

    def __check_for_errors(self, payload):
        """Check if the response contains an error message"""
        if len(payload) == 4:  # Error messages are always 4 bytes long
            if payload[0] == NCD_ERROR_CODE_HEADER and payload[3] == NCD_ERROR_CODE_FOOTER:
                self.__handle_error_message(payload[1])
            else:
                return payload
        else:
            return payload

    def __handle_error_message(self, error_code):
        #
        # This function should convert to I2C error exceptions.
        #
        # But using OSError instead is to be SMBUS compliant!
        #
        # NOTE:
        #   error messages taken from AlphaStation source code write/read I2C functions
        #
        if error_code == NCD_I2C_READ_ERROR:
            raise OSError(error_code, f"I2C timeout error while read on {self}, slave-IC did Not Respond, check I2C address.")
        elif error_code in [NCD_I2C_WRITE_ERROR1, NCD_I2C_WRITE_ERROR2]:
            raise OSError(error_code, f"I2C timeout error while write on {self}, slave-IC did Not Respond, check I2C address.")
        elif error_code == NCD_I2C_ACK_ERROR:
            raise OSError(error_code, f"I2C ACK Error on {self}")
        elif error_code == NCD_I2C_NOT_IMPLEMENTED_ERROR:
            raise Exception("Not implemented I2C function used")
        else:
            raise NCDUnknownErrorCodeError(self, error_code)


    def __wrap_payload_in_packet(self, payload: bytes) -> bytes:
        """Wraps the payload in an NCD packet."""
        byte_count = len(payload)
        packet = bytes([NCD_HEADER, byte_count]) + payload

        checksum = self.calculate_checksum(packet)
        packet += checksum.to_bytes(1, 'little')
        return packet

    def __data_exchange(self, tx_payload: bytes, retries: int = 3) -> bytes:
        """
        Performs the ethernet exchange and tries to reconnect the socket if the exchange failed.
        Number of retries can be specified
        Args:
            tx_payload:
            retries:

        Returns:

        """
        while retries > 0:
            try:
                return self.__socket_exchange(tx_payload)
            except Exception as e:
                #_log = getLogger(__name__, 2)
                #_log.debug(f"NCD Retries {retries}")
                #sleep(0.05)
                self.__connect_socket()
                retries -= 1
                if retries == 0:
                    raise e

    def __socket_exchange(self, tx_payload: bytes) -> bytes:
        # Send data
        tx_packet = self.__wrap_payload_in_packet(tx_payload)

        try:
            self.socket.sendall(tx_packet)
        except TimeoutError:  # find out which errors to add
            raise NCDTimeoutError(self)
        except OSError:
            raise NCDConnectionToInterfaceBroken(self)

        # Receive data
        chunks = []
        bytes_recd = 0

        # Receive header and length info
        expected_rx_cnt = 2
        while bytes_recd < expected_rx_cnt:
            try:
                chunk = self.socket.recv(min(expected_rx_cnt - bytes_recd, 2048))
            except TimeoutError:  # find out which errors to add
                raise NCDTimeoutError(self)
            except OSError:
                raise NCDConnectionToInterfaceBroken(self)
            else:
                if chunk == b'':
                    raise NCDConnectionToInterfaceBroken(self)

            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)

        rx_packet = b''.join(chunks)
        if rx_packet[NCD_PACKET_HEADER_INDEX] == NCD_HEADER:
            expected_rx_cnt = rx_packet[NCD_PACKET_LENGTH_INDEX] + 1  # +1 for checksum
        else:
            raise NCDUnknownResponseError(self, rx_packet)

        # read the rest of the packet
        chunks = []
        bytes_recd = 0
        while bytes_recd < expected_rx_cnt:
            try:
                chunk = self.socket.recv(min(expected_rx_cnt - bytes_recd, 2048))
            except TimeoutError:  # find out which errors to add
                raise NCDTimeoutError(self)
            except OSError:
                raise NCDConnectionToInterfaceBroken(self)
            else:
                if chunk == b'':
                    raise NCDConnectionToInterfaceBroken(self.ncd_interface_address)

            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)

        rx_packet += b''.join(chunks)
        payload = self.__check_and_decode_packet(rx_packet)
        return payload

    def __check_and_decode_packet(self, packet: bytes) -> bytes:
        if packet[NCD_PACKET_HEADER_INDEX] != NCD_HEADER:
            raise NCDUnknownResponseError(self, packet)
        if packet[NCD_PACKET_LENGTH_INDEX] != (len(packet) - NCD_PACKET_OVERHEAD):
            raise NCDUnknownResponseError(self, packet)
        received_checksum = packet[NCD_PACKET_CHECKSUM_INDEX]
        calculated_checksum = self.calculate_checksum(packet[:NCD_PACKET_CHECKSUM_INDEX])
        if received_checksum != calculated_checksum:
            raise NCDChecksumError(self)

        return packet[NCD_PACKET_DATA0_INDEX:NCD_PACKET_CHECKSUM_INDEX]

    @staticmethod
    def calculate_checksum(data: bytes):
        """Calculates the checksum for transmissions to the NCD serial-to-I2C
        adapter. (https://ncd.io/serial-to-i2c-conversion/)
        Checksum = Sum of all the bytes inside "data" and then limit to lower 8 bits.
        """
        return sum(data) & 0xFF

    @staticmethod
    def is_valid_7bit_address(i2c_address_7bit: int) -> bool:
        """Checks if i2c_address_7bit is a valid I2C address."""
        if isinstance(i2c_address_7bit, int):
            return 0 <= i2c_address_7bit < 128
        else:
            return False


#--------------------------------------------------------------------------------------------------

def test_interface(resource_str: str) -> None:
    from rrc.i2cbus import BusMux
    from rrc.smbus import BusMaster
    from rrc.chipsets.bq40z50 import BQ40Z50R1

    print("Test NCD API compatibility")
    dev = I2CPort(resource_str)
    print("API is RRC:", dev.interface_is_rrc)
    mux = BusMux(dev, 0x77)
    bus = BusMaster(dev)
    bat = BQ40Z50R1(bus)
    _= [print(f"DEVICE: {item}") for item in [dev,mux,bus,bat]]
    if dev.interface_is_rrc:
        print("Change clock frequency - RRC: ", str(dev.i2c_change_clock_frequency(77000)))
        print("Change clock frequency and timeout - RRC: ", str(dev.i2c_change_clock_frequency(55000, timeout_ms = 33)))
        #print("Change clock frequency - NCD: ", str(dev.i2c_change_clock_frequency_ncd(38000)))
        #dev.writeto(0x77, bytearray([0x02]))
        for c in range(1, 9):
            mux.setChannel(c)
            print(f"Channel {c}:", str(dev.i2c_bus_scan()))
        mux.setChannel(1)
    else:
        print(str(dev.i2c_bus_scan()))
    if bat.isReady():
        print("Found SmartBattery:")
        print(bat.device_name())
        print(bat.design_capacity())
        print(bat.design_voltage())
    else:
        print("No SmartBattery found")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    I2C_BRIDGE_RESOURCE_STR = "172.21.101.30:2101"  # HOM
    #I2C_BRIDGE_RESOURCE_STR = "172.25.102.20:2101"  # VN
    #I2C_BRIDGE_RESOURCE_STR = "192.168.69.77:2101"

    test_interface(I2C_BRIDGE_RESOURCE_STR)

    toc = perf_counter()
    print(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE
