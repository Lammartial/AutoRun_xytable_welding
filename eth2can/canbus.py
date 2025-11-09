
from typing import Tuple
from struct import unpack_from
from binascii import hexlify, unhexlify
from collections import OrderedDict
from rrc.eth2can.base import Eth2CanPort, API_OK_BYTE, API_ERROR_BYTE 


# --------------------------------------------------------------------------- #

def _od2t(d: OrderedDict) -> tuple:
    """To convert an ordered dict to a tuple of values for TestStand Container.

    Args:
        d (OrderedDict): _description_

    Returns:
        tuple: _description_
    """

    return tuple([t for t in d.values()])


# --------------------------------------------------------------------------- #


class CANBus(Eth2CanPort):


    def __init__(self, resource_str, open_connection = True, pause_on_retry = 10):  # this is for Teststand
        super().__init__(resource_str, open_connection=bool(open_connection), pause_on_retry=int(pause_on_retry))
        self._twai_status = None


    #----------------------------------------------------------------------------------------------

    def send_frame(self, identifier: int, data: bytes | bytearray, flags: int = 0, can_timeout_ms: int = 150, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
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
            can_timeout_ms.to_bytes(2, "little") + \
            bytes([len(data)]) + \
            bytearray(data)
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        return self._check_result_for_error(r)


    def receive_frame(self, identifier: int, flags: int = 0, can_timeout_ms: int = 900, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
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
            flags.to_bytes(4, "little") + \
            identifier.to_bytes(4, "little") + \
            can_timeout_ms.to_bytes(2, "little")
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        return self._check_result_for_error(r)


    def _decode_twai_status(self, buf) -> OrderedDict:
        """
            twai_state_t state;             // Current state of TWAI controller (Stopped/Running/Bus-Off/Recovery)
            uint32_t msgs_to_tx;            // Number of messages queued for transmission or awaiting transmission completion
            uint32_t msgs_to_rx;            // Number of messages in RX queue waiting to be read
            uint32_t tx_error_counter;      // Current value of Transmit Error Counter
            uint32_t rx_error_counter;      // Current value of Receive Error Counter
            uint32_t tx_failed_count;       // Number of messages that failed transmissions
            uint32_t rx_missed_count;       // Number of messages that were lost due to a full RX queue (or errata workaround if enabled)
            uint32_t rx_overrun_count;      // Number of messages that were lost due to a RX FIFO overrun
            uint32_t arb_lost_count;        // Number of instances arbitration was lost
            uint32_t bus_error_count;       // Number of instances a bus error has occurred
        
        Args:
            buf (_type_): _description_

        Returns:
            OrderedDict: _description_
        """
        state = unpack_from("<L", buf, 0)[0]
        _state_txt = (
            "STOPPED",
            "RUNNING",
            "BUF_OFF",
            "RECOVERING"
        )
        self._twai_status = OrderedDict({            
            "block": hexlify(buf),
            "state": state,
            "state_txt": _state_txt[state & 0x03],
            "msgs_to_tx": unpack_from("<L", buf, 4)[0],
            "msgs_to_rx": unpack_from("<L", buf, 12)[0],
            "tx_error_counter": unpack_from("<L", buf, 16)[0],
            "rx_error_counter": unpack_from("<L", buf, 20)[0],
            "tx_failed_count": unpack_from("<L", buf, 24)[0],
            "rx_missed_count": unpack_from("<L", buf, 28)[0],
            "rx_overrun_count": unpack_from("<L", buf, 32)[0],
            "arb_lost_count": unpack_from("<L", buf, 36)[0],
            "bus_error_count": unpack_from("<L", buf, 40)[0],
        })
        return self._twai_status


    def _check_result_for_error(self, result: bytes | bytearray) -> Tuple[bool, bytes, OrderedDict]:
        """Checks for error response and returns the payload on success.
        In case of error, a detailed info including the TWAI status is being returned.

        Args:
            result (bytes | bytearray): _description_

        Raises:
            IOError: _description_

        Returns:
            Tuple[bool, bytes, OrderedDict]: _description_
        """

        if result[0] == API_OK_BYTE:
            # ACK ok -> slice this byte off
            return True, result[1:], None
        elif result[0] == API_ERROR_BYTE:
            # is an error: decode the information
            _txt = {
                0x4711: "Wrong payload length: expected 11 or more",
                0x4712: "Write Error",
                0x4713: "Wrong payload length: expected 10 bytes payload.",
                0x4714: "Receive Error",
                0x4715: "Could not get TWAI status error",
                0x4716: "Failed to recover TAWI bus",
                0x4717: "TWAI driver not stopped error",
                0x4718: "TWAI driver de-install error",
                0x4719: "TWAI driver init error",
            }
            err_code = unpack_from("<H", result, 1)[0]            
            self._error_info = OrderedDict({
                "err_code" : err_code,
                "optional_code" : unpack_from("<L", result, 3)[0],
                "err_txt" : _txt[err_code] if err_code in _txt else '',
                "twai_status" : self._decode_twai_status(result[7:]),
            })
            return False, None, self._error_info
        else:
            # not an API error - must be in the Adapter/IFCard
            raise IOError(f"Unknown result header: {result[0]}")

    
    #----------------------------------------------------------------------------------------------

    def _err_info_to_text(self, e: dict) -> str:
        return f"CAN bus error: 0x{e['err_code']:04X}, 0x{e['optional_code']:08X}. {e['err_txt']} Status={_od2t(e['twai_status'])}"


    def teststand_send(self, identifier: int, data: str, flags: int = 0, can_timeout_ms: int = 150, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
        buf = unhexlify(data.replace("0x","").replace(",",""))
        ok, r, e = self.send_frame(int(identifier), buf, flags=int(flags), can_timeout_ms=int(can_timeout_ms), timeout=float(timeout))
        if not ok:        
            _err_txt = self._err_info_to_text(e)
        else:
            _err_txt = ""
        return ok, r, _err_txt

    def teststand_receive(self, identifier: int, flags: int = 0, can_timeout_ms: int = 900, timeout: float = 1.0) -> Tuple[bool, bytes, str]:
        ok, r, e = self.receive_frame(int(identifier), flags=int(flags), can_timeout_ms=int(can_timeout_ms), timeout=int(timeout))
        if not ok:        
            _err_txt = self._err_info_to_text(e)
        else:
            _err_txt = ""
        return ok, r, _err_txt


    def get_twai_status(self, timeout: float = 1.0) -> tuple:
        buf = b'G_'  # = get twai status
        r = self.request(buf, timeout=timeout, encoding=False)
        ok, payload, err_info = self._check_result_for_error(r)
        if ok:
            self._decode_twai_status(payload)
        return _od2t(self._twai_status)


    def reinstall_can_driver_on_remote(self, timeout: float = 1.0) -> Tuple[bool, str]:
        buf = b'X_'
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        ok, r, e = self._check_result_for_error(r)
        if not ok:        
            _err_txt = self._err_info_to_text(e)
        else:
            _err_txt = ""
        return ok, _err_txt 
    

    def recover_can_driver_on_remote(self, timeout: float = 1.0) -> Tuple[bool, str]:
        buf = b'Q_'  # = Try to recover TWAI driver, e.g. after being in RESET state
        print(hexlify(buf))  # DEBUG
        r = self.request(buf, timeout=timeout, encoding=False)
        ok, r, e = self._check_result_for_error(r)
        if not ok:        
            _err_txt = self._err_info_to_text(e)
        else:
            _err_txt = ""
        return ok, _err_txt
        


# END OF FILE