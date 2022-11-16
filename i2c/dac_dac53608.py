

DAC53608_DEVICE_CONFIG_REGISTER_ADDR = 0x01
DAC53608_STATUS_TRIGGER_REGISTER_ADDR = 0x02
DAC53608_BROADCAST_REGISTER_ADDR = 0x03
DAC53608_DAC0_DATA_REGISTER_ADDR = 0x08


class DAC53608:
    number_of_channels = 8
    resolution_in_bits = 10
    number_of_steps = 2 ** resolution_in_bits

    def __init__(self, i2c_port, i2c_address_7bit):
        self.i2c_port = i2c_port
        self.i2c_address_7bit = i2c_address_7bit
        self.v_ref_V = 5.0

    def set_v_ref(self, new_v_ref_V: float):
        if new_v_ref_V <= 0.0:
            raise ValueError("Reference voltage for DAC53608 must be > 0 V.")
        self.v_ref_V = new_v_ref_V

    def set_channel_n_voltage(self, channel: int, voltage_V: float) -> float:
        self.__validate_channel_number(channel)

        steps = DAC53608.number_of_steps
        d = int(round(voltage_V * steps / self.v_ref_V, 0))
        d = min((steps-1), max(0, d))  # constrain d to 0 to number_of_steps
        actual_voltage = self.v_ref_V * d / steps  # Calculate actual voltage
        self.__set_dac_n_data_register(channel, d)
        return actual_voltage

    def enable_all_channels(self):
        self.__set_device_config_register(0)

    def disable_all_channels(self):
        self.__set_device_config_register(0x00FF)

    def enable_channel_n(self, channel: int):
        self.__validate_channel_number(channel)

        config_register = self.__get_device_config_register()
        channel_n_is_disabled = bool(config_register & (1 << (channel - 1)))
        if channel_n_is_disabled:
            config_register &= ~(1 << (channel - 1))
            self.__set_device_config_register(config_register)

    def disable_channel_n(self, channel: int):
        self.__validate_channel_number(channel)

        config_register = self.__get_device_config_register()
        channel_n_is_disabled = bool(config_register & (1 << (channel - 1)))
        if not channel_n_is_disabled:
            config_register |= (1 << (channel - 1))
            self.__set_device_config_register(config_register)

    def __get_device_config_register(self) -> int:
        register = self.i2c_port.readfrom_mem(self.i2c_address_7bit, bytearray([DAC53608_DEVICE_CONFIG_REGISTER_ADDR]), 2)
        return int.from_bytes(register, "big", signed=False)

    def __set_device_config_register(self, value: int):
        msb = (value & 0xFF00) >> 8
        lsb = value & 0xFF
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([DAC53608_DEVICE_CONFIG_REGISTER_ADDR, msb, lsb]))

    def __set_dac_n_data_register(self, channel: int, value: int):
        register_address = DAC53608_DAC0_DATA_REGISTER_ADDR + channel - 1
        value = value << 2  # Offset in the data register
        msb = (value & 0xFF00) >> 8
        lsb = value & 0xFF
        self.i2c_port.writeto(self.i2c_address_7bit, bytearray([register_address, msb, lsb]))

    def __validate_channel_number(self, channel: int):
        if channel < 1 or channel > DAC53608.number_of_channels:
            raise ValueError(f"Channel number {channel} is invalid for DAC53608 (ranges from 1 to {DAC53608.number_of_channels}).")


if __name__ == "__main__":
    from ncd_eth_i2c_interface import I2CPort
    I2C_BRIDGE_IP = "192.168.1.60"
    I2C_BRIDGE_PORT = 2101
    port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
    port.writeto(0x77, bytes([0x01]))
    # print(port.i2c_bus_scan())
    dac = DAC53608(port, 0x48)
    dac.enable_all_channels()
    for i in range(1, 9):
        dac.set_channel_n_voltage(i, 5)
    dac.enable_channel_n(5)
