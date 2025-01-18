"""
Test patterns to check MiniTRack components communication including CPU Card either by USB/SERIAL or Ethernet later on.

"""

from time import sleep
from rrc.track import CPU_Card, DC63600, DCZPlus
from rrc.keysight import DAQ970A


PRODUCTION_LINES_SETUP = {
    "toptek": {
        "cpu_card":   "COM8,115200,8N1",
        "datalogger": "172.23.130.31:5025",
        "dc_load":    "172.23.130.32:2101",
        "dc_supply":  "172.23.130.33:8003",
    }
}



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = PRODUCTION_LINES_SETUP["toptek"]

    supply = DCZPlus(cfg["dc_supply"], channel=1)
    sleep(0.10)  # wait until all network modules are load, otherwise the first connect throws from time to time

    print(supply.ident())
    print(supply.channel, supply.select_channel())
    supply.initialize_device()
    supply.clear_protection()
    supply.set_voltage(5.5)
    print(supply.get_foldback())
    print(supply.get_condition_register(2))

    supply2 = DCZPlus(cfg["dc_supply"], channel=2)
    print(supply2.ident())
    print(supply2.channel, supply2.select_channel())
    supply2.initialize_device()
    supply2.clear_protection()

    load = DC63600(cfg["dc_load"], channel=1)
    print(load.ident())
    print(load.select_channel())
    load.initialize_device()
    print(load.get_load_mode())
    load.set_load_mode("CVL")

    load2 = DC63600(cfg["dc_load"], channel=2)
    print(load2.ident())
    print(load2.select_channel())
    load2.initialize_device()
    print(load2.get_load_mode())

    datalogger = DAQ970A(cfg["datalogger"], card_slot=1)
    print(datalogger.ident())

    cpu = CPU_Card(cfg["cpu_card"])
    print(cpu.ident())
    #print(cpu.ident_boot())
    #print(cpu.help().replace("\r","\n\r"))

# END OF FILE