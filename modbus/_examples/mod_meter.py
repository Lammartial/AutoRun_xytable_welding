"""
Modbus meter client module. Defines abstract classes for meter data
quisition by Modbus. A common (minimum) set of functions is defined
herein.
--------------------------------------------------------------------------
"""

import datetime
import pytz         # all timestamps need to have timezone awareness
from abc import ABC, abstractmethod # abstract base class

from .custom_json import JsonableObject
from ..modbus_base import ModbusClient

# for debuging support, set to >0
verbosity=0

#--------------------------------------------------------------------------------------------------
# base class
class ModbusMeter(ModbusClient):
    def __init__(self, connection_str, unit_address=None, channel=None):
        self.channel = channel
        super().__init__(connection_str, group_by_gateway=True)
        if unit_address is not None:
            self.unit_address = int(unit_address) # this OVERWRITES the unit_address stored in ModbusClient()

    def to_json(self):
        d = super().to_json()
        d.update({
            "connection": self.gateway_str + ":" + str(self.unit_address), # NOTE: we cannot name it "connection_str" as some inherited objects later use option connection=xxx
            "channel": self.channel
        })
        return d

    def filterString(self, s):
        n = ""
        for b in s:
            c = chr(b)
            if c.isprintable(): n += c
        return n

    def createTimestamp(self):
        # make sure we have timezone aware data, even tough it's just UTC
        return datetime.datetime.now(tz=pytz.utc) # => results in ISO format string in datalog
        #return datetime.datetime.now(tz=pytz.utc).timestamp() * 1e+3 # = ms UNIX timestamp - backward compatibility


    # abstract functions
    @abstractmethod
    def readConstData(self, channel=None):
        pass
    @abstractmethod
    def readAcPowerData(self, channel=None):
        pass
    @abstractmethod
    def readAcEnergyData(self, channel=None):
        pass
    @abstractmethod
    def readDcPowerData(self, channel=None):
        pass
    @abstractmethod
    def readDcEnergyData(self, channel=None):
        pass
    @abstractmethod
    def readTemperatureData(self, channel=None):
        pass

#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    print("Start test")

    # nix ...

    print("End test")
