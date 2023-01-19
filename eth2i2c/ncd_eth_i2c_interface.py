import socket
from time import sleep
from rrc.eth2i2c.base import I2CBase
from rrc.eth2i2c.ncd_errors import *


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

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
NCD_I2C_WRITE_ERROR = 0x5A
NCD_I2C_WRITE_ERROR2 = 0x5C
NCD_NOT_IMPLEMENTED_ERROR = 0x5D
NCD_I2C_ACK_ERROR = 0x5E

NCD_PACKET_HEADER_INDEX = 0
NCD_PACKET_LENGTH_INDEX = 1
NCD_PACKET_DATA0_INDEX = 2
NCD_PACKET_CHECKSUM_INDEX = -1
NCD_PACKET_OVERHEAD = 3



class I2CPort(I2CBase):
    """A class to control the NCD Ethernet to I2C converter"""

    def __init__(self, host: str, port: int = 2101, timeout_s: float = NCD_DEFAULT_TIMEOUT_S, open_connection: bool = True):
        """Initialize the object, establish the network connection and perform the selftest of the converter.

        Args:
            host (str): hostname IP address of the converter
            port (int): port used for the communication. Default setting is 2101.
            timeout_s (float): Timeout for network communication in seconds

        Raises:
            NCDSelfTestFailedError: Raised if the selftest of the converter fails.
        """
        self.socket = None
        self._host = str(host)
        self._port = int(port)
        self._open_connection = open_connection
        self.timeout_s = timeout_s
        self.ncd_interface_address = f"{self._host}:{self._port}"  # This the ip address ("192.168.1.61:2101"). Used in error messages.
        self.last_i2c_address = -1  # Used to remember which i2c_address_7bit was last spoken to if an error occurs.
        if open_connection:
            self.open()

    def __str__(self) -> str:
        """Create a string that contains IP address, port and I2C address. Used for error messages.

        The string has the format "<ip address>:<port>:<i2c address>"
        Example: "192.168.1.56:2101:0x40"
        """
        return f"NCD ETH-to-I2C bridge at {self._host}:{self._port}:0x{self.last_i2c_address:02X}"

    def __repr__(self) -> str:
        return f"I2CPort({self._host}, {self._port}, timeout_s={self.timeout_s}, open_connection={self._open_connection})"

    #----------------------------------------------------------------------------------------------

    def open(self) -> None:
        self.__connect_socket()
        self.__data_exchange = self.__ethernet_exchange_wrapper
        self.self_test()  # raises if anything wrong

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

    def self_test(self) -> None:
        """Perform the self test of the converter.

        Raises:
            NCDSelfTestFailedError: Raised if the selftest of the converter fails.
        """
        # Test command has the payload 0xFE 0x21. Response should be 0x55
        if self.__data_exchange(bytes([0xFE, 0x21])) != bytes([0x55]):
            raise NCDSelfTestFailedError(self)


    def writeto(self, i2c_address_7bit: int, data: bytearray) -> int:
        """Send a bytearray (up to 100 bytes) to the specified I2C address and return the number of sent bytes.

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

        if len(data) > 100:
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
        if size <= 0 or size > 100:
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
            size (int): number of bytes to read. Up to 16.
            delay_ms (int): Delay in ms between writing and reading data.

        Returns:
            bytearray: bytes read from the device

        Raises:
            InvalidI2CAddressError: If the I2C address is invalid.
            InvalidParametersError: If size is invalid. (<= 0 or > 100)
        """
        i2c_address_7bit = int(i2c_address_7bit)
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise NCD_I2CInvalidAddressError(i2c_address_7bit, self)

        if isinstance(data, int):
            data = bytearray([data])

        if size < 0 or size > 16 or len(data) > 16:
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
        return list(rx_payload)


    def i2c_change_speed(self):
        # From internet:
        # 100KHz: AA 06 BC 32 01 01 00 00 A0
        # 38KHz:  AA 06 BC 32 01 01 00 01 A1
        # 200KHz: AA 06 BC 32 01 01 00 02 A2
        # 300KHz: AA 06 BC 32 01 01 00 03 A3
        # 400KHz: AA 06 BC 32 01 01 00 04 A4
        #         [AA bytecount][c1, c2, u1, u2, u3, u4][checksum]
        #              API       payload
        tx_payload = bytes([0xBC,0x32,0x01,0x01,0x00,0x02])
        rx_payload = self.__data_exchange(tx_payload)
        _log = getLogger(__name__, DEBUG)
        _log.info(rx_payload)
        return list(rx_payload)


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
        if error_code == NCD_I2C_READ_ERROR:
            raise OSError(NCD_I2C_READ_ERROR, f"I2C Read Error on {self}")
            #raise NCD_I2CReadError(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_I2C_WRITE_ERROR:
            raise OSError(NCD_I2C_READ_ERROR, f"I2C Write Error1 on {self}")
            #raise NCD_I2CWriteError1(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_I2C_WRITE_ERROR2:
            raise OSError(NCD_I2C_READ_ERROR, f"I2C Write Error2 on {self}")
            #raise NCD_I2CWriteError2(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_NOT_IMPLEMENTED_ERROR:
            raise Exception("Not implemented NCD function used")

        elif error_code == NCD_I2C_ACK_ERROR:
            raise OSError(NCD_I2C_READ_ERROR, f"I2C ACK Error on {self}")
            #raise NCD_I2CAckError(self.last_i2c_address, self.ncd_interface_address)

        else:
            raise NCDUnknownErrorCodeError(self, error_code)

    def __wrap_payload_in_packet(self, payload: bytes) -> bytes:
        """Wraps the payload in an NCD packet."""
        byte_count = len(payload)
        packet = bytes([NCD_HEADER, byte_count]) + payload

        checksum = self.calculate_checksum(packet)
        packet += checksum.to_bytes(1, 'little')
        return packet

    def __ethernet_exchange_wrapper(self, tx_payload: bytes, retries: int = 3) -> bytes:
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
                return self.__ethernet_exchange(tx_payload)
            except Exception as e:                
                #_log = getLogger(__name__, 2)
                #_log.debug(f"NCD Retries {retries}")                
                #sleep(0.05)
                self.__connect_socket()
                retries -= 1
                if retries == 0:
                    raise e
                
    def __ethernet_exchange(self, tx_payload: bytes) -> bytes:
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

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    I2C_BRIDGE_RESOURCE_STR = "192.168.1.56"
    dev = I2CPort(I2C_BRIDGE_RESOURCE_STR)
    dev.writeto(0x77, bytearray([0x02]))
    _log.info(str(dev.i2c_bus_scan()))
    #_log.info(str(dev.i2c_change_speed()))

# END OF FILE
