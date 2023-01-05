

class DAC53608:
    """A class to control the 8-channel 10-bit DAC DAC53608 by TI via I2C.
    The channels are numbered from 1 to 8.

    https://www.ti.com/product/DAC53608
    """
    number_of_channels = 8
    resolution_in_bits = 10
    number_of_steps = 2 ** resolution_in_bits
    device_config_register_addr = 0x01  # R/W
    dac0_data_register_addr = 0x08      # W

    def __init__(self, i2c_port, i2c_address_7bit):
        """Initialize the object with an I2CPort object and the 7-bit I2C address.

        Args:
            i2c_port: The I2CPort instance this board is connected to
            i2c_address_7bit: The board's 7-bit I2C address
        """
        self.i2c_port = i2c_port
        self.i2c_address_7bit = int(i2c_address_7bit)
        self.v_ref_V = 5.0

    def set_v_ref(self, new_v_ref_V: float):
        """Change the reference voltage for calculating the output voltage of the DAC.

        This value is only stored internally and should be the set to the voltage at the V_ref_in pin of the DAC.

        Args:
            new_v_ref_V (float): The new reference voltage in Volts.

        Raises:
            ValueError: If the new reference voltage is negative or zero.
            MagicSmoke: If the actual reference voltage is above 6.3 V
        """
        if new_v_ref_V <= 0.0:
            raise ValueError("Reference voltage for DAC53608 must be > 0 V.")
        self.v_ref_V = new_v_ref_V

    def set_channel_n_voltage(self, channel: int, voltage_V: float) -> float:
        """Set the voltage of the specified channel as close as possible to the specifed voltage and return the actual voltage.

        Since the DAC has a finite resolution, not every voltage can be set. But the voltage that is sent to the DAC will
        be as close as possible to the desired voltage.

        Notes:
            A readback of the voltage via I2C is not possible. The DAC's data registers are write-only.

        Args:
            channel (int): index of the DAC channel. Possible values [1, 8]
            voltage_V (float): desired voltage in Volts.

        Returns:
            float: The actual voltage that was sent to the DAC.

        Raises:
            ValueError: If the channel index is invalid. (< 1 or > 8)
        """
        channel = int(channel)
        self.__validate_channel_number(channel)

        steps = DAC53608.number_of_steps
        try:
            d = int(round(voltage_V * steps / self.v_ref_V, 0))
        except ZeroDivisionError:
            raise  # We can't do anything about it here. Let it propagate.

        d = min((steps-1), max(0, d))  # limit d between 0 and number_of_steps
        actual_voltage = self.v_ref_V * d / steps  # Calculate actual voltage
        self.__set_dac_data_n_register(channel, d)
        return actual_voltage

    def enable_all_channels(self):
        """Enable all channel outputs."""
        self.__set_device_config_register(0)

    def disable_all_channels(self):
        """Disable all channel outputs.

        This connects the outputs to a 10k pulldown connected to A_Gnd.
        """
        self.__set_device_config_register(0x00FF)

    def enable_channel_n(self, channel: int):
        """Enable a single channel of the DAC.

        Args:
            channel (int): index of the DAC channel. Possible values [1, 8]

        Raises:
            ValueError: If the channel index is invalid. (< 1 or > 8)
        """
        channel = int(channel)
        self.__validate_channel_number(channel)

        config_register = self.__get_device_config_register()
        channel_n_is_disabled = bool(config_register & (1 << (channel - 1)))
        if channel_n_is_disabled:
            config_register &= ~(1 << (channel - 1))
            self.__set_device_config_register(config_register)

    def disable_channel_n(self, channel: int):
        """Disable a single channel of the DAC.

        This connects the output to a 10k pulldown connected to A_Gnd.

        Args:
            channel (int): index of the DAC channel. Possible values [1, 8]

        Raises:
            ValueError: If the channel index is invalid. (< 1 or > 8)
        """
        channel = int(channel)
        self.__validate_channel_number(channel)

        config_register = self.__get_device_config_register()
        channel_n_is_disabled = bool(config_register & (1 << (channel - 1)))
        if not channel_n_is_disabled:
            config_register |= (1 << (channel - 1))
            self.__set_device_config_register(config_register)

    def __get_device_config_register(self) -> int:
        register = self.i2c_port.readfrom_mem(self.i2c_address_7bit, bytearray([DAC53608.device_config_register_addr]), 2)
        return int.from_bytes(register, "big", signed=False)

    def __set_device_config_register(self, value: int):
        msb = (value & 0xFF00) >> 8
        lsb = value & 0xFF
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([DAC53608.device_config_register_addr, msb, lsb]))

    def __set_dac_data_n_register(self, channel: int, value: int):
        register_address = DAC53608.dac0_data_register_addr + channel - 1  # -1 because numbering starts at 1
        value = value << 2  # Offset in the data register
        msb = (value & 0xFF00) >> 8
        lsb = value & 0xFF
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([register_address, msb, lsb]))

    def __validate_channel_number(self, channel: int):
        if channel < 1 or channel > DAC53608.number_of_channels:
            raise ValueError(f"Channel number {channel} is invalid for DAC53608 (ranges from 1 to {DAC53608.number_of_channels}).")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from ncd_eth_i2c_interface import I2CPort
    I2C_BRIDGE_IP = "192.168.1.60"
    I2C_BRIDGE_PORT = 2101
    port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
    port.writeto(0x77, bytearray([0x01]))
    # print(port.i2c_bus_scan())
    dac = DAC53608(port, 0x48)
    dac.enable_all_channels()
    for i in range(1, 9):
        dac.set_channel_n_voltage(i, 5)
    dac.enable_channel_n(5)

# END OF FILE