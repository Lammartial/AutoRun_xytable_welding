from dac_dac53608 import DAC53608
from ncd_eth_i2c_interface import I2CPort


class CellVoltageSource:
    cell1_dac_channel = 1
    cell2_dac_channel = 2
    cell3_dac_channel = 3
    cell4_dac_channel = 4
    cell5_dac_channel = 5
    cell6_dac_channel = 6
    cell7_dac_channel = 7
    # cell_dict maps cell numbers to DAC-channels
    cell_dict = {1: cell1_dac_channel, 2: cell2_dac_channel, 3: cell3_dac_channel, 4: cell4_dac_channel,
                 5: cell5_dac_channel, 6: cell6_dac_channel, 7: cell7_dac_channel}
    aux_dac_channel = 8

    def __init__(self, i2c: I2CPort, i2c_address_7bit: int):
        self.i2c_address_7bit = i2c_address_7bit
        self.dac = DAC53608(i2c, i2c_address_7bit)
        self.aux_dac_channel_gain = 2.0

    def initialize(self):
        """
        Sets all voltages to 0 V and enables the voltage outputs.
        Brings the device into a defined state.
        :return:
        """
        for i in range(1, DAC53608.number_of_channels+1):
            self.dac.set_channel_n_voltage(i, 0.0)
        self.dac.enable_all_channels()

    def set_aux_voltage(self, aux_pin_voltage_V) -> float:
        """
        Sets the voltage on the auxillary pin
        :param aux_pin_voltage_V: desired output voltage in Volts
        :return: actual output voltage in Volts after adjusting to resolution of the DAC.
        """
        dac_voltage_V = aux_pin_voltage_V / self.aux_dac_channel_gain
        return self.dac.set_channel_n_voltage(CellVoltageSource.aux_dac_channel, dac_voltage_V)

    def enable_aux_dac_channel(self):
        """
        Enables the DAC-channel for the aux pin.
        :return:
        """
        self.dac.enable_channel_n(CellVoltageSource.aux_dac_channel)

    def power_down_aux_dac_channel(self):
        """
        Disables the DAC-channel for the aux pin.
        :return:
        """
        self.dac.disable_channel_n(CellVoltageSource.aux_dac_channel)

    def set_all_cell_voltages(self, cell_voltage_V) -> float:
        """
        Sets the voltage of all cells to the same voltage.
        :param cell_voltage_V: desired output voltage in Volts
        :return: actual output voltage in Volts after adjusting to resolution of the DAC.
        """
        set_voltage_V = 0.0
        for cell in CellVoltageSource.cell_dict:
            set_voltage_V = self.dac.set_channel_n_voltage(cell, cell_voltage_V)
        return set_voltage_V

    def enable_all_cell_channels(self):
        """
        Enables all DAC-channels for the cell pins.
        :return:
        """
        for cell in CellVoltageSource.cell_dict:
            self.dac.enable_channel_n(cell)

    def power_down_all_cell_channels(self):
        """
        Disables all DAC-channels for the cell pins.
        :return:
        """
        for cell in CellVoltageSource.cell_dict:
            self.dac.disable_channel_n(cell)

    def set_cell_n_voltage(self, cell_n, cell_voltage_V) -> float:
        """
        Sets the voltage of the specified cell
        :param cell_n: Number of the cell. Numbering starts at 1. Maximum is 7.
        :param cell_voltage_V: desired output voltage in Volts
        :return: actual output voltage in Volts after adjusting to resolution of the DAC.
        """
        self.__validate_cell_number(cell_n)
        return self.dac.set_channel_n_voltage(cell_n, cell_voltage_V)

    def enable_cell_n_channel(self, cell_n: int):
        """
        Enables the DAC-channel for the specified cell pins.
        :param cell_n:
        :return:
        """
        self.__validate_cell_number(cell_n)
        self.dac.enable_channel_n(CellVoltageSource.cell_dict[cell_n])

    def power_down_cell_n_channel(self, cell_n: int):
        """
        Disables the DAC-channel for the specified cell pin.
        :param cell_n:
        :return:
        """
        self.__validate_cell_number(cell_n)
        self.dac.disable_channel_n(CellVoltageSource.cell_dict[cell_n])

    def __validate_cell_number(self, cell_n: int):
        """
        Checks if the cell number is valid. I.e. It checks if the Cell voltage source has that cell
        :param cell_n:
        :return:
        """
        if cell_n not in CellVoltageSource.cell_dict.keys():
            raise ValueError(f"Cell number for the Cell Voltage Source (0x{self.i2c_address_7bit:02X}) must be "
                             f"between 1 to {max(CellVoltageSource.cell_dict.keys())}. You selected {cell_n}.")


if __name__ == '__main__':
    from ncd_eth_i2c_interface import I2CPort
    I2C_BRIDGE_IP = "192.168.1.60"
    I2C_BRIDGE_PORT = 2101
    i2c_port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
    # print(i2c_port.i2c_bus_scan())
    i2c_port.writeto(0x77, bytes([0x01]))
    cvs = CellVoltageSource(i2c_port, 0x48)
    cvs.initialize()
    cvs.set_aux_voltage(3.141)
    # cvs.set_cell_n_voltage(1, 3.7)
    # cvs.set_cell_n_voltage(2, 3.7)
    # cvs.set_cell_n_voltage(3, 3.7)
    # cvs.set_cell_n_voltage(4, 2.5)
    cvs.set_all_cell_voltages(3.7)
    cvs.power_down_cell_n_channel(2)
