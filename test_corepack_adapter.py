#import unittest
from typing import Tuple
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    i2cbus = I2CPort("172.25.101.42:2101") 
    #print(i2cbus.i2c_bus_scan())
    #exit(1) 
    mux = BusMux(i2cbus, address=0x77)
    #smbus = BusMaster(I2CMuxedBus(i2cbus, mux, 1), retry_limit=7, verify_rounds=3, pause_us=50)    
    #bus = BusMaster(i2cbus)
    #print(bus.isReady(0x77))
    #mux = BusMux(i2cbus, address=0x77)
    mux.setChannelMask(0xff)
    #mux.setChannel(1)
    print(i2cbus.i2c_bus_scan())
    #print(mux.getChannels())
    #print(bus.readWord(0x0b,0x09))
    pass

# END OF FILE
