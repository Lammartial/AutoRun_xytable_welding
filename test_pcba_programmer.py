
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets.bq import ChipsetTexasInstruments
from rrc.chipsets.bq40z50 import BQ40Z50R1, BQ40Z50R2

from rrc.pcba_programmer import PROGRAMMERS, PRODUCT_LIST

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

#--------------------------------------------------------------------------------------------------

# UNPROGRAMMED PCBA as it arrives from supplier:
# ----------------------------------------------
# Device Name: bq40z50-R1
# FW Version: ('4500010600240003850200', 17664, 262, 36, 0, 901, 2, 0)
# Checksums as int/hex: (54677, '0xD595', 57997, '0xE28D', 27800, '0x6C98')
# Checksums as hexlifyed bytes: '95D5,8DE2,986C'
# Checksums as hex comma separated: '95,D5,8D,E2,98,6C'
#
# PROGRAMMED RRC2040-2:
# ---------------------
# Device Name: RRC2040-2
# FW Version: ('4500021100340004750200', 17664, 529, 52, 0, 1141, 2, 0)
# Checksums as int/hex: (38388, '0x95F4', 54113, '0xD361', 26195, '0x6653')
# Checksums as hexlifyed bytes: 'F495,61D3,5366'
# Checksums as hex comma separated: 'F4,95,61,D3,53,66'
#

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    i2cbus = I2CPort(PROGRAMMERS[0])
    smbus = BusMaster(i2cbus, retry_limit=1, verify_rounds=3, pause_us=50)
    bat = BQ40Z50R1(smbus)

    print("PIN 35", i2cbus.gpio_read_input(35))
    print("PIN 39", i2cbus.gpio_read_input(39))
    i2cbus.gpio_write_output(12, 0)  # LED
    print("PIN 35", i2cbus.gpio_read_input(35))
    print("PIN 39", i2cbus.gpio_read_input(39))
    i2cbus.gpio_write_output(12, 1)
    print("PIN 35", i2cbus.gpio_read_input(35))
    print("PIN 39", i2cbus.gpio_read_input(39))
    i2cbus.gpio_write_output(32, 0)  # Power Enable
    print("PIN 35", i2cbus.gpio_read_input(35))
    i2cbus.gpio_write_output(32, 1)

    print("Device Name:", bat.device_name()[0])
    print("FW Version:", bat.firmware_version(hexi=True))
    print("Checksums as int/hex:", bat.read_firmware_checksum())
    print("Checksums as hexlifyed bytes:", bat.read_firmware_checksum(hexi=True))
    print("Checksums as hex comma separated:", bat.read_firmware_checksum(hexi=","))
    
    i2cbus.gpio_write_output(32, 1)

# END OF FILE
