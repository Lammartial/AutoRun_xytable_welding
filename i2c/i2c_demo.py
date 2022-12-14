from ncd_eth_i2c_interface import I2CPort
from smbus import BusMaster, BusMux_PCA9548A
from testadapter_cell_voltage_source import CellVoltageSource
from smartbattery import Battery
from gpio_mcp23008 import MCP23008
from relayboard_i2cio4r4xdpdt import RelayBoard4Relay4GPIO
from time import sleep
from temperature_sts21 import STS21
from flash_stream_flasher import FlashStreamFlasher
from pathlib import Path
from datetime import datetime as dt
from eeprom_at24hc02c import AT24HC02C
from shunt_calibration_storage import ShuntCalibrationStorage

I2C_BRIDGE_IP = "192.168.1.83"
I2C_BRIDGE_PORT = 2101

i2c_port = I2CPort(I2C_BRIDGE_IP, I2C_BRIDGE_PORT)
busmaster = BusMaster(i2c_port)
busmux = BusMux_PCA9548A(i2c_port, address=0x77)

busmux.setChannel(1)
busmux.setChannel(2)
# print(i2c_port.i2c_bus_scan())
# bat = Battery(busmaster)

# eeprom1 = AT24HC02C(i2c_port, 80)
# eeprom1.write_bytes(0, bytearray([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]))
# print(eeprom1.read_bytes(0, 8))

shunt1 = ShuntCalibrationStorage(i2c_port, 80)
shunt1.store_shunt_resistance_ohm(-1.1)
print(shunt1.load_shunt_resistance_ohm())

# flasher = FlashStreamFlasher(bat)
# log_file_path = Path("fsf-log-file-{}.log".format(dt.now().strftime("%Y-%m-%dT%H-%M-%S")))
# flasher.setup_logger(log_file_path)
# fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3412036-02_B_Tansanit_B_RRC2040B.bq.fs")
# # fs_file = Path(r"C:\Users\mschmitt\Desktop\SCD_3410758-08_bq40z50-R4_A-draft1_Adamite_RRC2140_BMS_Files.bq.fs")
# flasher.set_firmware_file(fs_file)
# validation_result = flasher.validate_file()
# print(f"Validation result: {validation_result}")
# if validation_result:
#     pass
#     programming_result = flasher.program_fw_file()
#     print(f"Programming result: {programming_result}")

# print(bat.device_name()[0])
# print(bat.voltage())
# print(f"S: {bat.is_sealed()}")
# print(f"FA: {bat.is_full_access()}")
# bat.full_access_battery()
# print(f"S: {bat.is_sealed()}")
# print(f"FA: {bat.is_full_access()}")
# bat.seal_battery()
# print(f"S: {bat.is_sealed()}")
# print(f"FA: {bat.is_full_access()}")
# sleep(0.1)
#
# print(bat.is_sealed())


# print(i2c_port.i2c_bus_scan())

# temp = STS21(i2c_port, 0x4A)

# cvs = CellVoltageSource(i2c_port, i2c_address_7bit=0x48)
# cvs.initialize()
# cvs.set_aux_voltage(10)

# gpio = MCP23008(i2c_port, 0x20)

# rb = RelayBoard4Relay4GPIO(i2c_port, 0x20)
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
