from time import sleep
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC


class STS21:
    """A class to control the STS21 temperature sensor by Sensirion.

    https://sensirion.com/products/catalog/STS21/
    """
    cmd_user_register_read = 0xE7
    cmd_user_register_write = 0xE6
    cmd_soft_reset = 0xFE
    cmd_trigger_meas_hold = 0xE3
    cmd_trigger_meas_no_hold = 0xF3
    measurement_resolution = {11: 0x81, 12: 0x01, 13: 0x80, 14: 0x00}

    def __init__(self, i2c_port, i2c_address_7bit: int = 0x4A):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c_port: The I2CPort instance this sensor is connected to
            i2c_address_7bit: The sensor's 7-bit I2C address
        """
        self.i2c_port = i2c_port
        self.i2c_address_7bit = int(i2c_address_7bit)

    def start_measurement_hold(self, retries: int = 3) -> float:
        """Start a temperature measurement in "hold master mode" and return the temperature in °C as a float.

        In hold master mode the sensor will hold the SCL line low until it has completed the measurement (clock
        stretching). For the NCD I2C converters the maximum allowed clock stretching seems to be around 50 ms.
        I.e. if the measurement takes longer than 50 ms it will result in a "Chip does not respond" error from the
        I2C converter. For the measurement resolutions of 11, 12 and 13 bit this should be fine, but a measurement with
        14 bit will definetly take longer and therefore result in an error. 14 bit measurements (which is the sensor's
        power-on default) should therefore only be started with the start_measurement_no_hold function.

        Args:
            retries: Number of retries if the CRC of the sensors response is incorrect.

        Returns:
            float: Temperature in °C

        Raises:
            ValueError: if the CRC is still wrong after all retries are used up.
        """
        retries = int(retries)
        while retries > 0:
            result = self.i2c_port.readfrom_mem(self.i2c_address_7bit, bytearray([STS21.cmd_trigger_meas_hold]), 3)
            if self.check_crc(result):
                return self.__convert_sensor_response_to_temperature(result)
            retries -= 1
        raise ValueError(f"CRC from temperature sensor at 0x{self.i2c_address_7bit:02X} still wrong after multiple retries.")

    def start_measurement_no_hold(self, retries: int = 3) -> float:
        """Start a temperature measurement in "no hold master mode" and return the temperature in °C as a float.

        In no hold mode the I2C transfer is over after the measurement has been started. Then the function waits for
        85 ms before it reads the measurement result from the sensor.

        Args:
            retries: Number of retries if the CRC of the sensors response is incorrect.

        Returns:
            float: Temperature in °C

        Raises:
            ValueError: if the CRC is still wrong after all retries are used up.
        """
        retries = int(retries)
        while retries > 0:
            self.i2c_port.writeto(self.i2c_address_7bit, bytearray([STS21.cmd_trigger_meas_no_hold]))
            sleep(0.085)  # This is the worst case waiting time for the measurement to be finished
            result = self.i2c_port.readfrom(self.i2c_address_7bit, 3)
            if self.check_crc(result):
                return self.__convert_sensor_response_to_temperature(result)
            retries -= 1
        raise ValueError(f"CRC from temperature sensor at 0x{self.i2c_address_7bit:02X} still wrong after multiple retries.")

    def __convert_sensor_response_to_temperature(self, sensor_response: bytearray) -> float:
        """Convert the response from the sensor to a temperature in °C according to the datasheet."""
        temperature_signal_output = int.from_bytes(sensor_response[0:2], "big", signed=False)
        temperature_signal_output &= 0xFFFC  # The last two bits are status bits and must be set to 0 before the conversion.
        t_celsius = -46.85 + 175.72 * temperature_signal_output / 2 ** 16
        return t_celsius

    def set_measurement_resolution(self, resolution_bits: int):
        """Set the resolution of the temperature measurements.

        Possible resolutions for this sensor are 11, 12, 13 and 14 bit.

        Args:
            resolution_bits (int): The desired resolution. Can be either 11, 12, 13 or 14

        Raises:
            ValueError: If the resolution is not 11, 12, 13 or 14
        """
        resolution_bits = int(resolution_bits)
        if resolution_bits not in STS21.measurement_resolution.keys():
            raise ValueError(f"Wrong measurement resolution for STS21. Must be one of "
                             f"{list(STS21.measurement_resolution.keys())}. You selected {resolution_bits}")

        user_register = self.__get_user_register()
        new_user_register = (user_register & 0x7E) | STS21.measurement_resolution[resolution_bits]
        self.__set_user_register(new_user_register)

    def check_crc(self, response) -> bool:
        crc_calc = calc_crc8(response[:-1])
        crc_read = response[-1]
        return crc_read == crc_calc

    def __get_user_register(self) -> int:
        response = self.i2c_port.readfrom_mem(self.i2c_address_7bit, bytearray([STS21.cmd_user_register_read]), 1)
        return int.from_bytes(response, "big", signed=False)

    def __set_user_register(self, value: int):
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([STS21.cmd_user_register_write, value]))


def calc_crc8(databytes):
    """Calculates the cyclic redundancy check (crc) over the input bytes using polynominal 0x1070 for SmartBusPEC

    Args:
        databytes (bytes or bytearray): buffer to calculate CRC over. Expects being a buffer of bytes, type check is ommitted for sake of performance.

    Returns:
        byte: calculated crc value.
    """
    _sum = 0
    if databytes is not None:
        global lutable_poly_0x31
        for b in databytes:
            _sum = lutable_poly_0x31[_sum ^ b]
    return _sum


# CRC-8 lookup table for polynom 0x31. From http://www.sunshine2k.de/coding/javascript/crc/crc_js.html
lutable_poly_0x31 = [0x00, 0x31, 0x62, 0x53, 0xC4, 0xF5, 0xA6, 0x97, 0xB9, 0x88, 0xDB, 0xEA, 0x7D, 0x4C, 0x1F, 0x2E,
                     0x43, 0x72, 0x21, 0x10, 0x87, 0xB6, 0xE5, 0xD4, 0xFA, 0xCB, 0x98, 0xA9, 0x3E, 0x0F, 0x5C, 0x6D,
                     0x86, 0xB7, 0xE4, 0xD5, 0x42, 0x73, 0x20, 0x11, 0x3F, 0x0E, 0x5D, 0x6C, 0xFB, 0xCA, 0x99, 0xA8,
                     0xC5, 0xF4, 0xA7, 0x96, 0x01, 0x30, 0x63, 0x52, 0x7C, 0x4D, 0x1E, 0x2F, 0xB8, 0x89, 0xDA, 0xEB,
                     0x3D, 0x0C, 0x5F, 0x6E, 0xF9, 0xC8, 0x9B, 0xAA, 0x84, 0xB5, 0xE6, 0xD7, 0x40, 0x71, 0x22, 0x13,
                     0x7E, 0x4F, 0x1C, 0x2D, 0xBA, 0x8B, 0xD8, 0xE9, 0xC7, 0xF6, 0xA5, 0x94, 0x03, 0x32, 0x61, 0x50,
                     0xBB, 0x8A, 0xD9, 0xE8, 0x7F, 0x4E, 0x1D, 0x2C, 0x02, 0x33, 0x60, 0x51, 0xC6, 0xF7, 0xA4, 0x95,
                     0xF8, 0xC9, 0x9A, 0xAB, 0x3C, 0x0D, 0x5E, 0x6F, 0x41, 0x70, 0x23, 0x12, 0x85, 0xB4, 0xE7, 0xD6,
                     0x7A, 0x4B, 0x18, 0x29, 0xBE, 0x8F, 0xDC, 0xED, 0xC3, 0xF2, 0xA1, 0x90, 0x07, 0x36, 0x65, 0x54,
                     0x39, 0x08, 0x5B, 0x6A, 0xFD, 0xCC, 0x9F, 0xAE, 0x80, 0xB1, 0xE2, 0xD3, 0x44, 0x75, 0x26, 0x17,
                     0xFC, 0xCD, 0x9E, 0xAF, 0x38, 0x09, 0x5A, 0x6B, 0x45, 0x74, 0x27, 0x16, 0x81, 0xB0, 0xE3, 0xD2,
                     0xBF, 0x8E, 0xDD, 0xEC, 0x7B, 0x4A, 0x19, 0x28, 0x06, 0x37, 0x64, 0x55, 0xC2, 0xF3, 0xA0, 0x91,
                     0x47, 0x76, 0x25, 0x14, 0x83, 0xB2, 0xE1, 0xD0, 0xFE, 0xCF, 0x9C, 0xAD, 0x3A, 0x0B, 0x58, 0x69,
                     0x04, 0x35, 0x66, 0x57, 0xC0, 0xF1, 0xA2, 0x93, 0xBD, 0x8C, 0xDF, 0xEE, 0x79, 0x48, 0x1B, 0x2A,
                     0xC1, 0xF0, 0xA3, 0x92, 0x05, 0x34, 0x67, 0x56, 0x78, 0x49, 0x1A, 0x2B, 0xBC, 0x8D, 0xDE, 0xEF,
                     0x82, 0xB3, 0xE0, 0xD1, 0x46, 0x77, 0x24, 0x15, 0x3B, 0x0A, 0x59, 0x68, 0xFF, 0xCE, 0x9D, 0xAC]


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    pass

# END OF FILE