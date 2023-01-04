"""
 Use LAN connection and "Net Module Configure" software to check CH9121 parameters:
     1. LAN parameters of CH9121: TCP SERVER mode, PORT1 (IP address, port number1), PORT2 (IP address, port number2)
     2. UART parameters of CH9121 (baudrate 57600, Data bits 8, Stop bit 1)

     Check FEASA LED ANALYSER RS232 settings. Default: baudrate 57600, Data bits 8, Stop bit 1

"""

from eth2serial.base import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION


DEBUG = 0

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

class FEASA_CH9121(Eth2SerialDevice):

    RESPONSE_OK = "OK"

    def test_int(self):
        return int(1)

    def test_float(self):
        return float(1)

    # Capture Fuctions ----------------------------------------------------------------------------

    # CAPTURE
    def capture(self) -> bool:
        """
        This Auto Range Capture instructs the LED Analyser to capture and store the data of all the
        LED's positioned under the fibers.

        Returns:
            bool: False - failed, True - success

        """
        response = self.request("capture")
        return True if self.RESPONSE_OK in response else False  # this way we ignore any line termination




# .... more




#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    HOST = "192.168.1.90"
    PORT = 2000

    # 1. Create an instance of class as device controller
    feasa = FEASA_CH9121(HOST, PORT)

    # 2. Get some data

    # "CAPTURE" command
    print(feasa.capture())

    # "CAPTURE#" command
    print(feasa.capture_range(1))

    # "CAPTUREPWM" command
    #print(feasa.capture_pwm())

    # "CAPTURE#PWM@@" command
    #print(feasa.capture_pwm_range(1, 7))

    # "getRGBI##" command
    print(feasa.get_rgbi_num(1))

    # "getINTENSITY##" command
    print(feasa.get_intensity_num(1))

    # "SetIntGain##xxx" command
    print(feasa.set_intgain_num(1, 100))

    # SetFactor## command
    print(feasa.set_factor(1))

    print("DONE.")

# END OF FILE