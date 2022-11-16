import socket
from ncd_errors import *


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

I2C_BRIDGE_IP = "192.168.1.60"
I2C_BRIDGE_PORT = 2101
DEBUG = 0


class I2CPort:
    """Implements basic I2C functions of the NCD serial-to-I2C adapter"""
    def __init__(self, host: str, port: int, timeout_s: float = NCD_DEFAULT_TIMEOUT_S):
        self.socket = None
        self.host_port = (host, port)
        self.timeout_s = timeout_s
        self.ncd_interface_address = f"{host}:{port}"  # This the ip address ("192.168.1.61:2101"). Used in error messages.

        if self.__connect_socket():
            self.__data_exchange = self.__ethernet_exchange_wrapper
            if not self.self_test():
                print("Ethernet selftest failed.")

        self.last_i2c_address = -1  # Used to remember which i2c_address_7bit was last spoken to if an error occurs.

    def __connect_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout_s)
        try:
            self.socket.connect(self.host_port)
        except TimeoutError:
            raise CantFindNCDInterface(self.ncd_interface_address)
        else:
            return True

    def self_test(self):
        # Test command has the payload 0xFE 0x21. Response should be 0x55
        if self.__data_exchange(bytes([0xFE, 0x21])) == bytes([0x55]):
            return True
        else:
            raise SelfTestFailedError(self.ncd_interface_address)

    def close(self):
        try:
            self.socket.close()
        except AttributeError:
            # self.socket could be None
            pass

    def writeto(self, i2c_address_7bit: int, data: bytearray) -> int:
        """Writes a list of integers to the device on the specified I2C
        i2c_address_7bit.
        """
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise InvalidI2CAddressError(i2c_address_7bit, self.ncd_interface_address)

        self.last_i2c_address = i2c_address_7bit

        tx_payload = bytes([NCD_I2C_WRITE, i2c_address_7bit]) + data

        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        if rx_payload[0] == NCD_COMMAND_SUCCESSFULL:  # Command successful
            return len(data) + 1
        else:
            return 0

    def readfrom(self, i2c_address_7bit: int, size: int) -> bytearray:
        """Reads the specified amount (up to 25) of bytes from the device and
        checks the response for errors.
        """
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise InvalidI2CAddressError(i2c_address_7bit, self.ncd_interface_address)
        if size <= 0 or size > 100:
            raise InvalidParametersError(i2c_address_7bit, self.ncd_interface_address)

        self.last_i2c_address = i2c_address_7bit
        tx_payload = bytes([NCD_I2C_READ, i2c_address_7bit, size])
        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return bytearray(rx_payload)

    def readfrom_mem(self, i2c_address_7bit: int, data: bytearray, size: int, delay_ms: int = 0) -> bytearray:
        """Writes a list of integers (data) to the device and then reads up to
        16 bytes from the device. The response is also checked for errors.
        """
        if not self.is_valid_7bit_address(i2c_address_7bit):
            raise InvalidI2CAddressError(i2c_address_7bit, self.ncd_interface_address)

        if size < 0 or size > 16 or len(data) > 16:
            raise InvalidParametersError(i2c_address_7bit, self.ncd_interface_address)

        self.last_i2c_address = i2c_address_7bit
        tx_payload = bytes([NCD_I2C_WRITE_READ, i2c_address_7bit, size, delay_ms]) + data

        rx_payload = self.__data_exchange(tx_payload)
        self.__check_for_errors(rx_payload)
        return bytearray(rx_payload)

    def i2c_bus_scan(self):
        """Scans the bus for devices and returns a list of their addresses."""
        tx_payload = bytes(NCD_I2C_BUS_SCAN)
        rx_payload = self.__data_exchange(tx_payload)
        return list(rx_payload)

    def __check_for_errors(self, payload):
        """Checks if the response contains an error message"""
        if len(payload) == 4:  # Error messages are always 4 bytes long
            if payload[0] == NCD_ERROR_CODE_HEADER and payload[3] == NCD_ERROR_CODE_FOOTER:
                self.__handle_error_message(payload[1])
            else:
                return payload
        else:
            return payload

    def __handle_error_message(self, error_code):
        if error_code == NCD_I2C_READ_ERROR:
            raise I2CReadError(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_I2C_WRITE_ERROR:
            raise I2CWriteError1(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_I2C_WRITE_ERROR2:
            raise I2CWriteError2(self.last_i2c_address, self.ncd_interface_address)

        elif error_code == NCD_NOT_IMPLEMENTED_ERROR:
            raise I2CNotImplementedError

        elif error_code == NCD_I2C_ACK_ERROR:
            raise I2CAckError(self.last_i2c_address, self.ncd_interface_address)

        else:
            raise UnknownNCDError(self.ncd_interface_address, error_code)

    def __wrap_payload_in_packet(self, payload: bytes) -> bytes:
        """Wraps the payload in a packet, converts it to a bytearray sends it
        over the serial port.
        """
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
                retries -= 1
                self.__connect_socket()
                print(retries)
                if retries == 0:
                    raise e

    def __ethernet_exchange(self, tx_payload: bytes) -> bytes:
        # Send data
        tx_packet = self.__wrap_payload_in_packet(tx_payload)

        try:
            self.socket.sendall(tx_packet)
        except TimeoutError:  # find out which errors to add
            raise NCDTimeoutError(self.ncd_interface_address)
        except OSError:
            raise ConnectionToNCDInterfaceBroken(self.ncd_interface_address)

        # Receive data
        chunks = []
        bytes_recd = 0

        # Receive header and length info
        expected_rx_cnt = 2
        while bytes_recd < expected_rx_cnt:
            try:
                chunk = self.socket.recv(min(expected_rx_cnt - bytes_recd, 2048))
            except TimeoutError:  # find out which errors to add
                raise NCDTimeoutError(self.ncd_interface_address)
            except OSError:
                raise ConnectionToNCDInterfaceBroken(self.ncd_interface_address)
            else:
                if chunk == b'':
                    raise ConnectionToNCDInterfaceBroken(self.ncd_interface_address)

            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)

        rx_packet = b''.join(chunks)
        if rx_packet[NCD_PACKET_HEADER_INDEX] == NCD_HEADER:
            expected_rx_cnt = rx_packet[NCD_PACKET_LENGTH_INDEX] + 1  # +1 for checksum
        else:
            raise UnknownResponseError(self.ncd_interface_address, rx_packet)

        # read the rest of the packet
        chunks = []
        bytes_recd = 0
        while bytes_recd < expected_rx_cnt:
            try:
                chunk = self.socket.recv(min(expected_rx_cnt - bytes_recd, 2048))
            except TimeoutError:  # find out which errors to add
                raise NCDTimeoutError(self.ncd_interface_address)
            except OSError:
                raise ConnectionToNCDInterfaceBroken(self.ncd_interface_address)
            else:
                if chunk == b'':
                    raise ConnectionToNCDInterfaceBroken(self.ncd_interface_address)

            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)

        rx_packet += b''.join(chunks)
        payload = self.__check_and_decode_packet(rx_packet)
        return payload

    def __check_and_decode_packet(self, packet: bytes) -> bytes:
        if packet[NCD_PACKET_HEADER_INDEX] != NCD_HEADER:
            raise UnknownResponseError(self.ncd_interface_address, packet)
        if packet[NCD_PACKET_LENGTH_INDEX] != (len(packet) - NCD_PACKET_OVERHEAD):
            raise UnknownResponseError(self.ncd_interface_address, packet)
        received_checksum = packet[NCD_PACKET_CHECKSUM_INDEX]
        calculated_checksum = self.calculate_checksum(packet[:NCD_PACKET_CHECKSUM_INDEX])
        if received_checksum != calculated_checksum:
            raise ChecksumError(self.ncd_interface_address)

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


if __name__ == "__main__":
    i2c_port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
    i2c_port.writeto(0x77, bytes([0x01]))
    print(i2c_port.i2c_bus_scan())
