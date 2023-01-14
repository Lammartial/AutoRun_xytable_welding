""" SMBus Master for RRC battery tools"""
__author__ = "Markus Ruth"
__version__ = "1.0.0"

from typing import Tuple
import errno
from struct import pack, unpack
from time import sleep
from rrc.smbus_pec import calc as pec_calc
from rrc.eth2i2c import I2CBase, I2CError, NCDError

#--------------------------------------------------------------------------------------------------
class BusmasterError(Exception):
    """Our base exception class so that all Exceptions related to our SMBus library can easiy be catched."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.message = args[0]

    def __str__(self):
        return "{}[{}]".format(type(self).__name__, self.message)


class BusmasterVerificationError(BusmasterError):
    """Raised if verified read fails."""
    pass

#--------------------------------------------------------------------------------------------------
class BusMaster:
    i2c = None

    def __init__(self, i2c: I2CBase, retry_limit=1, verify_rounds=3, pause_us=50):
        """Class providing the SMBus master protocols.

        Next to the standard functions there are "verified" versions of these
        starting with "v" letter. Each of the read functions does a repetition
        of readings and compares the result. The one with more than verified_count//2
        equal results wins and gets returned. Otherwise bytearray(),False is returned.

        Args:
            i2c (I2C instance): Created I2C bus object to share
            retry_limit (int, optional): Number of bus operation tries (do not confuse with verify_rounds!).  Applies to ALL write/read operations.
                                         Valid range is 1(no 2nd try) to 10(up to 9 retries after 1st fails). Defaults to 1.
            verify_rounds (int, optional): Number of successful bus operation repetitions with result compare. Must be an odd number whereas 1 is effectively
                                           disabling verification instead works as read once. Defaults to 3.
            pause_us (int, optional): Optional pause in Microseconds between retries and verify repeated operations, 0 disables the pause. Defaults to 50.

        Raises:
            ValueError: If there is an invalid value for retry_limit or verify_rounds
            OSError/Exception: If there are exceptions occured and no verified result, the last exception caught will be forwarded.
        """

        self.i2c = i2c
        self.pause_us = int(pause_us)  # in micro seconds
        self.retry_limit = int(retry_limit)  # number of read repetitions, must be integer in range 1 .. 10
        self.verify_rounds = int(verify_rounds)  # number of read repetitions, must be 1,3,5,7,9, etc. (odd numbers > 0)

    def __str__(self) -> str:
        return f"SMBus Master on {str(self.i2c)}"

    def __repr__(self) -> str:
        return f"BusMaster({repr(self.i2c)}, retry_limit={self.retry_limit},verify_rounds={self.verify_rounds},pause_us={self.pause_us})"

    # ----------------------------------------------------------------------------------------------
    @property
    def retry_limit(self):
        return self._retry_limit

    @retry_limit.setter
    def retry_limit(self, value):
        if not (isinstance(value, int) and (value >= 1) and (value <= 10)):
            raise ValueError("Retry count limit must be an integer 1 ... 10")
        self._retry_limit = value

    # ----------------------------------------------------------------------------------------------
    @property
    def verify_rounds(self):
        return self._verify_rounds

    @verify_rounds.setter
    def verify_rounds(self, value):
        if not (isinstance(value, int) and (value >= 1) and ((value & 1) == 1)):
            raise ValueError("Retry count limit must be an odd number > 0 like 1,3,5,7,9,...")
        self._verify_rounds = value

    # ----------------------------------------------------------------------------------------------
    def isReady(self, slvAddress):
        """Checks if the given slave address is being ACK'd on bus.

        Args:
            slvAddress (integer or byte): Slave address to check

        Returns:
            Boolean: True if address was ACK'd, else False
        """
        # return self.i2c.is_ready(slvAddress)
        isready = False
        try:
            _ = self.i2c.readfrom(slvAddress, 0, stop=True)
            isready = True
        except OSError as ex:
            if (ex.args[0] == errno.ENODEV) or (ex.args[0] == errno.ETIMEDOUT):
                # only expected execption is "device not present" or "timed out"
                pass
            else:
                # forward this exception
                raise ex
        except I2CError as ex:
            print(ex)
        except NCDError as ex:
            print(ex)
        return isready

    # ----------------------------------------------------------------------------------------------
    # core functions (all others a reusing these ones)
    def writeBytes(self, slvAddress, cmd, buffer, use_pec=False):
        """Writes a given sequence of bytes to a slave device addressed by slvAddress and command.

        Args:
            slvAddress (byte | int): 8 bit slave address (0..255)
            cmd (byte | int): command code (0..255)
            buffer (bytes | bytearray): payload bytes to be written to slave
            use_pec (bool, optional): Use a PEC checksum to verify the transfer if True. Defaults to False.

        Returns:
            bool: True if write transfer was successfully completed including PEC if given.
        """
        # print("cmd", hex(cmd)) # DEBUG
        bufc = bytearray(bytes([cmd]) + bytes(buffer))
        if use_pec:
            # calculate the PEC and attach it
            _cs = pec_calc([slvAddress << 1])
            _cs = pec_calc(bufc, _cs)
            bufc.append(_cs)
        # print("SMBUS_writebytes", hexlify(bufc).decode())  # DEBUG
        for n in range(0, self._retry_limit):
            try:
                # wlen = self.i2c.writeto_mem(slvAddress,cmd,buf)
                wlen = self.i2c.writeto(slvAddress, bufc)
                # ok = (wlen > 0)
                ok = len(bufc) == wlen
                return ok
            except OSError:
                if n == self._retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")

    def _retry_read_helper(self, slvAddress, cmd, count):
        for n in range(0, self._retry_limit):
            try:
                if count <= 16:
                    buf = self.i2c.readfrom_mem(slvAddress, cmd, count)
                else:
                    self.i2c.writeto(slvAddress, bytearray([cmd]))
                    buf = self.i2c.readfrom(slvAddress, count)
                # print("SMBUS_readbytes", hexlify(buf).decode()) # DEBUG
                return buf
            except OSError:
                if n == self._retry_limit - 1:
                    raise
            except Exception:
                raise
            sleep(self.pause_us / 1000000)
        # may never get here!
        raise Exception("Programming Error")

    def readBytes(self, slvAddress, cmd, count, use_pec=False):
        """Read bytes from a slave address with given command code written after slave address.

        Args:
            slvAddress (byte | int): 8 bit slave address (0..255)
            cmd (byte | int): command code (0..255)
            count (int): number of bytes to read
            use_pec (bool, optional): Use a PEC checksum to verify the transfer if True. Defaults to False.

        Returns:
            bytearray: bytes buffer that has been read.
            bool: True, if count bytes have been read and checksum was correct (if given), False else.
        """
        if use_pec:
            # buf = bytearray(count+1)
            # rlen = self.i2c.readfrom_mem_into(slvAddress,cmd,buf,stop=False)
            # buf = self.i2c.readfrom_mem(slvAddress,cmd,count+1)
            count = count + 1
            buf = self._retry_read_helper(slvAddress, cmd, count)
            rlen = len(buf)
            _cs = pec_calc([slvAddress << 1, cmd, slvAddress << 1 | 1])
            _cs = pec_calc(buf[:-1], _cs)
            # ok = (rlen > 0) and (_cs == buf[-1]) # last byte is checksum received
            ok = (rlen == count) and (_cs == buf[-1])  # last byte is checksum received
            return buf[:-1], ok  # remove the checksum from the data
        else:
            # buf = bytearray(count)
            # rlen = self.i2c.readfrom_mem_into(slvAddress,cmd,buf,stop=False)
            # buf = self.i2c.readfrom_mem(slvAddress,cmd,count)
            buf = self._retry_read_helper(slvAddress, cmd, count)
            rlen = len(buf)
            # ok = (rlen > 0)
            ok = (rlen == count)
            return buf, ok

    def readBytesVarLen(self, slvAddress, cmd, use_pec=False, byte_count=-1):
        """Read bytes from slave address with variable length in first byte received.

        As the i2c module does not provide this in dedicate function, we use two read
        accesses: 1) to get only the 1st byte 2) to read the given bytes+1.

        Args:
            slvAddress (byte | int): 8 bit slave address (0..255)
            cmd (byte | int): command code (0..255)
            use_pec (bool, optional): Use a PEC checksum to verify the transfer if True. Defaults to False.

        Returns:
            bytearray: bytes buffer that has been read.
            bool: True, if count bytes have been read and checksum was correct (if given), False else.
        """
        # 1. get count value
        # count = self.i2c.readfrom_mem(slvAddress,cmd,1,stop=False)
        # count = self.i2c.readfrom_mem(slvAddress,cmd,1)
        if byte_count == -1:
            count = self._retry_read_helper(slvAddress, cmd, 1)
            # 2. read the correct number of bytes
            if (len(count) > 0) and (count[0] > 0):
                buf, ok = self.readBytes(slvAddress, cmd, count[0] + 1, use_pec=use_pec)
            else:
                buf = bytearray()  # empty bytearray
                ok = False
        else:
            buf, ok = self.readBytes(slvAddress, cmd, byte_count, use_pec=use_pec)
        return buf, ok

    # ----------------------------------------------------------------------------------------------
    # "verified" functions, using multiple repetitions and compare x of y wheras y is an odd number
    def vReadBytes(self, slvAddress, cmd, count, use_pec=False):
        d = {}  # we use a dictionary to group the results (bytes read)
        ex = None
        vcnt = self._verify_rounds
        vpause = self.pause_us
        for _ in range(0, vcnt):
            try:
                buf, ok = self.readBytes(slvAddress, cmd, count, use_pec=use_pec)
                if ok:
                    k = bytes(buf)
                    if k in d:
                        d[k] += 1  # count equal results
                    else:
                        d[k] = 1  # new value
                    # Check if the new value as key into our dict has already a count of
                    # number > self._verify_rounds//2 which wins then for verified result.
                    # Note: this can be earliest after self._verify_rounds//2 + 1 iterations
                    #       and putting the comparision to this place, allows the correct use
                    #       of self._verify_rounds = 1 to effectively disable verification comparision
                    # print(k, d[k], vcnt//2, vcnt) # DEBUG
                    if d[k] > vcnt // 2:
                        return bytearray(k), True  # success!
            except OSError as e:
                ex = e  # save and ignore it for now
                pass
            if vpause > 0:
                # we need to do a pause between the tries
                sleep(vpause / 1000000)
        if ex is not None:
            # we had an exception and there is no verified result.
            # lets forward the saved exception
            raise ex
        else:
            # just too many different results on read, but no exception
            return bytearray(), False  # no or not enough verified result(s) found: fail!
            # raise BusmasterVerificationError("verification read has failed", d)

    def vReadBytesVarLen(self, slvAddress, cmd, use_pec=False):
        # Algorithm comments see above function vReadBytes()
        d = {}
        ex = None
        vcnt = self._verify_rounds
        vpause = self.pause_us
        for _ in range(0, vcnt):
            try:
                buf, ok = self.readBytesVarLen(slvAddress, cmd, use_pec=use_pec)
                if ok:
                    k = bytes(buf)
                    if k in d:
                        d[k] += 1
                    else:
                        d[k] = 1
                    # print(k, d[k], vcnt//2, vcnt) # DEBUG
                    if d[k] > vcnt // 2:
                        return bytearray(k), True
            except OSError as e:
                ex = e
                pass
            if vpause > 0:
                sleep(vpause / 1000000)
        if ex is not None:
            raise ex
        else:
            return bytearray(), False
            # raise BusmasterVerificationError("verification read has failed", d)

    def vWriteBytes(self, slvAddress, cmd, buffer, use_pec=False):
        # "verified write" is special as we do NOT do multiple write tries but do READ after WRITE
        # and compare whereas "read" means using the "verified read" strategy described above
        ok = self.writeBytes(slvAddress, cmd, buffer, use_pec=use_pec)  # write once
        if ok:
            sleep(self.pause_us / 1000000)
            rbuf, rok = self.vReadBytes(slvAddress, cmd, len(buffer), use_pec=use_pec)  # then read back verified
            # and copmpare the result with the written bytes
            if rbuf == bytearray(buffer):
                return rok
        return False

    # ---simple-versions----------------------------------------------------------------------------
    def readWord(self, slvAddress, cmd, use_pec=False):
        buf, ok = self.readBytes(slvAddress, cmd, 2, use_pec=use_pec)
        if ok:
            # generate a little endian WORD value from the two bytes
            # (PEC was already checked if required)
            # w = ((int(buf[1]) & 0xff) << 8) | (buf[0] & 0xff)
            w = unpack("<H", buf)[0]  # this is platform independent; buf is always little endian
        else:
            w = None
        return w, ok

    def readString(self, slvAddress, cmd, use_pec=False):
        buf, ok = self.readBytesVarLen(slvAddress, cmd, use_pec=use_pec)
        if ok:
            # convert to UTF8 string
            return bytes(buf[1:]).decode(), ok
        else:
            return '', False

    def readBlock(self, slvAddress, cmd, use_pec=False, byte_count=-1):
        # Note: there is no writeBlock() function implementation here on purpose.
        #       User should use the writeBytes() function with length byte in first of buffer to send.
        #       This also enables an easy read-after-write as the length of the buffer is already correct (+1)
        #       for using a readBytes() to check the complete buffer including the length byte.
        buf, ok = self.readBytesVarLen(slvAddress, cmd, use_pec=use_pec, byte_count=byte_count)
        if ok:
            # just return the bytes without length
            return bytearray(buf[1:]), ok
        else:
            return bytearray(), False

    def writeWord(self, slvAddress, cmd, w, use_pec=False):
        buffer = pack("<H", w)
        # buffer = [w & 0xff, (w >> 8) & 0xff] # this is platform independent (w could be little or big endian)
        ok = self.writeBytes(slvAddress, cmd, buffer, use_pec=use_pec)
        return ok

    # ---verified versions--------------------------------------------------------------------------

    def vReadWord(self, slvAddress, cmd, use_pec=False):
        buf, ok = self.vReadBytes(slvAddress, cmd, 2, use_pec=use_pec)
        if ok:
            # generate a little endian WORD value from the two bytes
            # (PEC was already checked if required)
            # w = ((int(buf[1]) & 0xff) << 8) | (buf[0] & 0xff)
            w = unpack("<H", buf)[0]  # this is platform independent; buf is always little endian
        else:
            w = None
        return w, ok

    def vReadString(self, slvAddress, cmd, use_pec=False):
        buf, ok = self.vReadBytesVarLen(slvAddress, cmd, use_pec=use_pec)
        if ok:
            # convert to UTF8 string
            return bytes(buf[1:]).decode(), ok
        else:
            return '', False

    def vReadBlock(self, slvAddress, cmd, use_pec=False):
        buf, ok = self.vReadBytesVarLen(slvAddress, cmd, use_pec=use_pec)
        if ok:
            # just return the bytes without length
            return bytearray(buf[1:]), ok
        else:
            return bytearray(), False

    def vWriteWord(self, slvAddress, cmd, w, use_pec=False):
        buffer = pack("<H", w)
        # buffer = [w & 0xff, (w >> 8) & 0xff] # this is platform independent (w could be little or big endian)
        ok = self.vWriteBytes(slvAddress, cmd, buffer, use_pec=use_pec)  # includes the read-back verify
        return ok


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    #ncd = I2CPort("192.168.1.149", 2101)
    #bus = BusMaster(ncd)
    #print(bus.isReady(0x77))
    #mux = BusMux(ncd, address=0x77)
    #mux.setChannel(1)
    #print(mux.getChannels())
    #print(bus.readWord(0x0b,0x09))
    pass

# END OF FILE
