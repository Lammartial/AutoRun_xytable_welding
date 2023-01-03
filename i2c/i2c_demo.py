from ncd_eth_i2c_interface import I2CPort
from smbus import BusMaster, BusMux_PCA9548A
from testadapter_cell_voltage_source import CellVoltageSource
from gpio_mcp23008 import MCP23008
from relayboard_i2cio4r4xdpdt import RelayBoard4Relay4GPIO
from time import sleep
from temperature_sts21 import STS21

I2C_BRIDGE_IP = "192.168.1.60"
I2C_BRIDGE_PORT = 2101

i2c_port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
busmaster = BusMaster(i2c_port)
busmux = BusMux_PCA9548A(i2c_port, address=0x77)

busmux.setChannel(1)

rb = RelayBoard4Relay4GPIO(i2c_port, 0x20)
rb.enable_relay_n(1)

#print(i2c_port.i2c_bus_scan())

# temp = STS21(i2c_port, 0x4A)

# cvs = CellVoltageSource(i2c_port, i2c_address_7bit=0x48)
# cvs.initialize()
# cvs.set_aux_voltage(10)

#gpio = MCP23008(i2c_port, 0x20)


#
# for i in range(4, 8):
#     rb.set_gpio_n_as_input(i)
#     rb.enable_pullup_for_gpio_n(i)
#
# while True:
#     if rb.read_gpio_n(4):
#         rb.enable_relay_n(1)
#     else:
#         rb.disable_relay_n(1)
#
#     if rb.read_gpio_n(5):
#         rb.enable_relay_n(2)
#     else:
#         rb.disable_relay_n(2)
#
#     if rb.read_gpio_n(6):
#         rb.enable_relay_n(3)
#     else:
#         rb.disable_relay_n(3)
#
#     if rb.read_gpio_n(7):
#         rb.enable_relay_n(4)
#     else:
#         rb.disable_relay_n(4)
#
#     sleep(0.1)
