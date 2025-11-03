
from typing import Tuple
from binascii import hexlify
from rrc.eth2can.base import Eth2CanPort

class CANBus(Eth2CanPort):


    def send(self, identifier: int, data: bytes | bytearray, flags: int = 0, can_timeout: int = 150, timeout: float = 1.0) -> Tuple[bytes, str]:
        """
        Send raw CAN frame data.

        Args:
            identifier (int): _description_
            data (bytes): _description_
            flags (int, optional): _description_. Defaults to 0.
            can_timeout (int, optional): CAN bustransfer timeout in ms. Defaults to 150.
            timeout (float, optional): Timeout of Ethernet request process in seconds. Defaults to 1.0.
        """

        s = b'W' + flags.to_bytes(4, "little") +\
            identifier.to_bytes(4, "little") +\
            can_timeout.to_bytes(2, "little") +\
            bytes([len(data)]) + bytearray(data)
        print(hexlify(s))

        r = self.request(b'W' +
                        flags.to_bytes(4, "little") +
                        identifier.to_bytes(4, "little") +
                        can_timeout.to_bytes(2, "little") +
                        bytes([len(data)]) + bytearray(data),
                        timeout=timeout,
                        encoding=False)
        return r, hexlify(r).decode()


    def receive(self, identifier: int, flags: int = 0, can_timeout: int = 900, timeout: float = 1.0) -> Tuple[bytes, str]:
        """Receive raw CAN frame data.

        Args:
            identifier (int): _description_
            flags (int, optional): _description_. Defaults to 0.
            can_timeout (int, optional): CAN bustransfer timeout in ms. Defaults to 900.
            timeout (float, optional): Timeout of Ethernet request process in seconds. Defaults to 1.0.

        Raises:
            TimeoutError: _description_
            ValueError: _description_

        Returns:
            Tuple[bytes, str]: _description_
        """

        r = self.request(b'R' +
                        identifier.to_bytes(4, "little") +
                        flags.to_bytes(4, "little") +
                        can_timeout.to_bytes(2, "little"),
                        timeout=timeout,
                        encoding=False)
        length = r[0]
        data = r[1:length]
        return data, hexlify(r).decode()


# END OF FILE