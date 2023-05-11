#import unittest
from typing import Tuple
from time import sleep

from rrc.feasa import FEASA_CH9121


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #





#-----------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger without filelogging
    _log = getLogger(__name__, DEBUG)

    RESOURCE_STRING = "172.25.101.43:3000"

    # 1. Create an instance of class as device controller
    feasa = FEASA_CH9121(RESOURCE_STRING)

    # 2. Get some data

    # # "CAPTURE" command
    # print(feasa.capture())

    # # "CAPTURE#" command
    # print(feasa.capture_range(1))

    # "CAPTUREPWM" command
    print("Issue capture command...")
    print(feasa.capture_pwm())

    # # "CAPTURE#PWM@@" command
    # print(feasa.capture_pwm_range(1, 7))

    # "getRGBI##" command
    print("getRGBI##0")
    print(feasa.get_rgbi_num(0))
    print("getRGBI##3")
    print(feasa.get_rgbi_num(3))

    # # "getINTENSITY##" command
    # print(feasa.get_intensity_num(1))

    # # "SetIntGain##xxx" command
    # print(feasa.set_intgain_num(1, 100))

    # # SetFactor## command
    # print(feasa.set_factor(1))

    print("DONE.")

# END OF FILE