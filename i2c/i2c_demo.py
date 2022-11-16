from ncd_eth_i2c_interface import I2CPort
from smbus import BusMaster, BusMux_PCA9548A
from testadapter_cell_voltage_source import CellVoltageSource
from gpio_mcp23008 import MCP23008

I2C_BRIDGE_IP = "192.168.1.60"
I2C_BRIDGE_PORT = 2101

i2c_port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
busmaster = BusMaster(i2c_port)
busmux = BusMux_PCA9548A(i2c_port, address=0x77)

busmux.setChannel(1)
print(i2c_port.i2c_bus_scan())

# cvs = CellVoltageSource(i2c_port, i2c_address_7bit=0x48)
# cvs.initialize()
# cvs.set_cell_n_voltage(2, 3.7)

gpio = MCP23008(i2c_port, 0x20)
