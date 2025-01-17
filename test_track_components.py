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

    supply = DCZPlus(cfg["dc_supply"])
    print(supply.ident())

    load = DC63600(cfg["dc_supply"])
    print(load.ident())

    datalogger = DAQ970A(cfg["datalogger"], card_slot=1)
    print(datalogger.ident())

    cpu = CPU_Card(cfg["cpu_card"])
    print(cpu.ident())


# END OF FILE