from typing import Tuple
from time import sleep
from modbus import log_modbus_version
from komeg import Komeg36LTemperatureChamber

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

#--------------------------------------------------------------------------------------------------

__version__ = VERSION

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import perf_counter

    log_modbus_version()
    tic = perf_counter()

    PORT = 26
    HOSTNAME = "192.168.1.90"
    # waveshare module uses 23 for TCP <-> RS232 and 26 for TCP <-> RS485; standard Modbus is 502

    chambers = [Komeg36LTemperatureChamber(f"tcp:{HOSTNAME}:{PORT}", unit_address=6),
                Komeg36LTemperatureChamber(f"tcp:{HOSTNAME}:{PORT}", unit_address=7),
                Komeg36LTemperatureChamber(f"tcp:{HOSTNAME}:{PORT}", unit_address=8),
                Komeg36LTemperatureChamber(f"tcp:{HOSTNAME}:{PORT}", unit_address=9),
                ]

    # word1 = struct.unpack(">HH", struct.pack(">f", float(-10.5)))[0]
    # print("CONV:", word1 )

    # float1 = struct.unpack(">f", struct.pack(">HH", word1, 0))[0]
    # print("CONV2:", float1 )

    # stop chamber 1, 2 and 3
    # for chamber in chambers[1:]:
    #     with chamber as k:
    #         k.stop()
    #_temp_setpoint = [55,55,-40,-40]
    #_temp_setpoint = [None, None, None, None]
    _temp_setpoint = []

    for i, chamber in enumerate(chambers):
        with chamber as k:
            print(f"CHAMBER: {i+1}")
            #k.set_datetime(datetime.now())
            # t = k.read_temperature()
            # print(f"T: {t}")
            if len(_temp_setpoint):
                if _temp_setpoint[i] is None:
                    k.stop()
                else:
                    k.set_temperature(_temp_setpoint[i])
                    #k.set_humidity(45.6)
                    k.start()
                sleep(0.5)
            # w = k.read_wet_temperature()
            # print(f"wT: {w}")
            # h = k.read_humidity()
            # print(f"H: {h}")
            dt = k.read_datetime_now()
            print(f"DATETIME_NOW: {dt}")
            #k.stop()
            #k.set_temperature(-30.0)
            #k.set_humidity(45.6)
            #k.start()
            d1 = k.read_settings()
            print(d1)
            d2 = k.read_cv()
            print(d2)

            # for a, c in [
            #     *[(0+x, 32) for x in range(0, 32, 32)],
            #     #(1, 10), (10, 10), (20, 10), (30, 10), (40, 10),
            #     *[(100+x, 32) for x in range(0, 32, 32)],
            #     (200, 32),
            #     #*[(200+x, 32) for x in range(0, 100, 32)],
            #     #*[(300+x, 32) for x in range(0, 100, 32)],
            #     #*[(400+x, 32) for x in range(0, 100, 32)],
            #     #*[(500+x, 32) for x in range(0, 100, 32)],
            #     #*[(600+x, 32) for x in range(0, 100, 32)],
            #     #*[(700+x, 32) for x in range(0, 100, 32)],
            #     (700, 32),
            #     #*[(800+x, 32) for x in range(0, 100, 32)],
            #     #*[(900+x, 32) for x in range(0, 100, 32)],
            #     (1000, 32), (2000, 32),
            # ]:
            #     k.read(a,c)

            #print("-"*80)
            #for a, c in [(x, 32) for x in range(0, 65536, 32)]:
            #     k.read(a,c)
            sleep(0.5)
            pass
    toc = perf_counter()
    _log.info(f"Send in {toc - tic:0.4f} seconds")
    _log.info("DONE.")
# END OF FILE