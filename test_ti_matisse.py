
import math
from struct import pack, unpack, unpack_from, pack_into
from binascii import hexlify




def float2flash(value: float) -> int:
    if value == 0:
        value += 0.0000001    # avoid log of zero
    if value < 0:
        bNegative = 1
        value *= -1
    else:
        bNegative = 0
    exponent = int((math.log(value)/math.log(2)))
    MSB = exponent + 127        # exponent bits
    mantissa = value / (2**exponent)
    mantissa = (mantissa - 1) / (2**-23)
    if (bNegative == 0):
        mantissa = int(mantissa) & 0x7fffff   # remove sign bit if number is positive
    result = int(round(mantissa + MSB * 2**23))
    print(hex(mantissa))  # DEBUG
    print(hex(MSB))  # DEBUG
    print(hex(result))  # DEBUG
    return result


def flash2float(value: int) -> float:
    # nearly IEEE754 format - but not correct!!
    exponent = 0xFF & int(value / (2**23))  # exponent is most significant byte after sign bit
    mantissa = value % (2**23)
    if (0x80000000 & value == 0):  # check if number is positive
        isPositive = 1
    else:
        isPositive = 0
    mantissa_f = 1.0
    mask = 0x400000
    for i in range(0,23):
        if ((mask >> i) & mantissa):
            mantissa_f += 2**(-1*(i+1))
    result = mantissa_f * 2**(exponent-127)
    if not(isPositive):
        result *= -1
    return float(result)



def ti_f4_to_float(z: int) -> float:
    exponent = (z >> 24) - 128 - 24  # both numbers are from ??? TI
    print(hex(exponent))
    mantissa = z & 0xFFFFFF
    sign = -1 if (z & 0x800000) != 0 else 1
    mantissa = mantissa | 0x800000  # set back the hidden 1 of mantissa
    result = sign * mantissa * 2**exponent
    return result


def flash_f4_to_float(z: int) -> float:
    # TI stores the EXP in a different way:
    # b31..b24 = EXP + 2
    # b24 = sign bit
    # b23..b0 = mantissa
    # To convert to IEEE754 we need to subtract 2 from EXP and move the sign bit to b31
    n = (z & 0x7FFFFF) | (((((z >> 24) & 0xFF) - 2) & 0xFF) << 23) | ((z & 0x00800000) << 8)
    b = pack("<L", n)
    f = unpack("<f", b)
    print(hexlify(b))
    print(f)
    return f[0]


def float_to_flash_f4(value: float) -> int:
    b = pack("<f", value)
    n = unpack("<L", b)[0]
    z = (n & 0x7FFFFF) | ((((n >> 23) & 0xFF) + 2) << 24) | ((n & 0x80000000) >> 8)
    return z


#print(ti_f4_to_float(0x7F71205C))

z = 0x7F71205C

print(ti_f4_to_float(z))
print(hex(float_to_flash_f4(0.47095000743865967)))
print(flash2float(z))
print(flash_f4_to_float(z))

z = 0x940898c0
print(ti_f4_to_float(z))
print(hex(float_to_flash_f4(559500)))

print(hex(n))
b = pack("<L", n)
print(hexlify(b))
f = unpack("<f", b)
print(f)
f0 = unpack("<f", bytearray([0x5c,0x20, 0xf1,0x3e]))
print(f0)

f1 = 0.47095000743865967
b1 = pack("<f", f1)
print(hexlify(b1))
print(unpack("f", b1))

f1 = 559500
b1 = pack("<f", f1)
print(hexlify(b1))
print(unpack("f", b1))

