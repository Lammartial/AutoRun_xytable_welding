#import unittest
from rrc.itech import M3400, M3900

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

#--------------------------------------------------------------------------------------------------
def test_m3900_modes(m3900: M3900) -> bool:

    #========= CHARGE & DISCHARGE MODE =====================================================================

    m3900.wake_up_mode_on(voltage_limit= 12.0, curr_limit= 0.1)
    m3900.wake_up_mode_off()


    m3900.charge_mode_on(voltage_limit= 12.55, curr= 2.0)     # Volt limit 12.55 for RRC2020
    m3900.charge_mode_off()

    m3900.discharge_mode_on(voltage_limit= 11.0, curr= -2.0)
    m3900.discharge_mode_off()

    m3900.charge_mode_on(voltage_limit= 12.55, curr= 2.0)     # Volt limit 12.55 for RRC2020
    m3900.charge_mode_off()

    m3900.discharge_mode_on(voltage_limit= 11.0, curr= -2.0)
    m3900.discharge_mode_off()

    #=======================================================================================================

    #print(it_m3902.get_ADC())

    #print(it_m3902.get_VDC())

    return True

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    res : float = 0

    # # predefined resource ID
    M3902_IP_STR = "TCPIP0::172.21.101.33::inst0::INSTR"

    # 1. Create an instance of ITECH_DEV class
    # using multi-channel communication
    m3902 = M3900(M3902_IP_STR, 0)
    # 2. IMPORTANT! Set remote control mode.
    print(m3902.set_remote_control())
    # 3. Do some stuff
    test_m3900_modes(m3902)


 #=============================================================================================

    print("DONE.")