
from typing import Tuple
from struct import unpack_from
from binascii import hexlify
from rrc.eth2can.base import Eth2CanPort




class CANBus(Eth2CanPort):


    def send(self, identifier: int, data: bytes | bytearray, flags: int = 0, can_timeout: int = 150, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
        """
        Send raw CAN frame data.

        Args:
            identifier (int): _description_
            data (bytes): _description_
            flags (int, optional): _description_. Defaults to 0.
            can_timeout (int, optional): CAN bustransfer timeout in ms. Defaults to 150.
            timeout (float, optional): Timeout of Ethernet request process in seconds. Defaults to 1.0.
        """

        buf = b'W' + \
            flags.to_bytes(4, "little") + \
            identifier.to_bytes(4, "little") + \
            can_timeout.to_bytes(2, "little") + \
            bytes([len(data)]) + \
            bytearray(data)
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        ok, err = self._check_result_for_error(r)
        if ok:        
            return ok, r, hexlify(r).decode()
        else:
            return ok, None, err
        
        
    def receive(self, identifier: int, flags: int = 0, can_timeout: int = 900, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
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

        buf = b'R' + \
            identifier.to_bytes(4, "little") + \
            flags.to_bytes(4, "little") + \
            can_timeout.to_bytes(2, "little")
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        ok, err = self._check_result_for_error(r)
        if ok:        
            return ok, r, hexlify(r).decode()
        else:
            return ok, None, err


    def _check_result_for_error(self, result: bytes | bytearray) -> Tuple[bool, str]:
        if result[0] == 0x55:
            # ACK ok
            return True, None
        elif result[0] == 0xEE:
            # is an error
            err_code = unpack_from("<H", result, 1)[0]
            optional_code = unpack_from("<L", result, 3)[0]
            _txt = {
                0x4711: "Wrong payload length: expected 11 or more",
                0x4712: "Write Error",
                0x4713: "Wrong payload length: expected 10 bytes payload.",
                0x4714: "Receive Error",            
            }
            _err = f"CAN bus error: 0x{err_code:04X}, 0x{optional_code:08X}. {_txt[err_code] if err_code in _txt else ''}"
            #raise IOError(f"CAN bus error: 0x{err_code:04X}, 0x{optional_code:08X}. {_txt[err_code] if err_code in _txt else ''}")
            return False, _err
        else:
            # not an API error - must be in the Adapter/IFCard
            raise IOError(f"Unknown result header: {result[0]}")



# END OF FILE