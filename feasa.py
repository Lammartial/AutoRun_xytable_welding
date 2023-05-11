"""
 Use LAN connection and "Net Module Configure" software to check CH9121 parameters:
     1. LAN parameters of CH9121: TCP SERVER mode, PORT1 (IP address, port number1), PORT2 (IP address, port number2)
     2. UART parameters of CH9121 (baudrate 57600, Data bits 8, Stop bit 1)

     Check FEASA LED ANALYSER RS232 settings. Default: baudrate 57600, Data bits 8, Stop bit 1

"""
import numpy as np
from rrc.eth2serial import Eth2SerialDevice

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


class FEASA_CH9121(Eth2SerialDevice):

    RESPONSE_OK = "OK"

    def __init__(self, resource_str: str, termination: str = "\r\n", count_fiber: int = 5):
        """_summary_

        Args:
            resource_str (str): _description_
            termination (str, optional): _description_. Defaults to "\r\n".
            count_fiber (int, optional): Number of connected fibers (1 .. 20). Defaults to 5.

        """
        super().__init__(resource_str, termination)
        self.count_fiber = int(count_fiber)

    def __str__(self) -> str:
        return f"FEASA device at {self.host}:{self.port} having {self.count_fiber} fibers connected."

    def __repr__(self) -> str:
        return f"FEASA_CH9121('{self.host}:{self.port}', termination='{self.termination}', count_fibers={self.count_fiber})"

    #----------------------------------------------------------------------------------------------
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
        response = self.request("capture", timeout=5.0)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, capture, %s", response, exc_info=1)
            return False

    # CAPTURE#
    def capture_range(self, range: int) -> bool:
        """
        This command uses a pre-selected exposure time designated Range1, Range2 etc. For low
        light or dim LED's use Range 1 and for brighter LED's use higher ranges.

        Args:
            range (int): 1 = Low, 2 = Medium, 3 = High, 4 = Super, 5 = Ultra

        Returns:
            bool: False - failed, True - success
        """
        cmd = "capture" + str(int(range))
        response = self.request(cmd, timeout=5.0)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, capture_range, %s", response, exc_info=1)
            return False

    # CAPTUREPWM
    def capture_pwm(self) -> bool:
        """
        Pulse-Width-Modulated(PWM) LED's are switched on and off rapidly to save power and to
        control Intensity. The Analyser automatically determines the correct settings required to
        execute the test.

        Returns:
            bool: False - failed, True - success
        """
        response = self.request("capturepwm", timeout=5.0)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, capture_pwm, %s", response, exc_info=1)
            return False

    # CAPTURE#PWM@@
    def capture_pwm_range(self, range: int, factor: int) -> bool:
        """
        This command allows the User to specify the exposure range # and an averaging factor @@
        when testing PWM LED's.

        Args:
            range (int): represents the exposure Range 1 – 5
            factor (int): represents an averaging factor in the range 1 - 15

        Returns:
            bool: False - failed, True - success
        """
        cmd = "capture" + str(int(range)) + "PWM" + f"{(int(factor)):02d}"
        response = self.request(cmd, timeout=5.0)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, capture_pwm_range, %s", response, exc_info=1)
            return False

    # Get Functions ----------------------------------------------------------------------------------

    # getRGBI##
    def get_rgbi_num(self, num: int) -> np.array:
        """
        This command instructs the LED Analyser to return RGB and Intensity data for fiber
        ## (01-20) in format rrr ggg bbb iiiii where rrr, ggg and bbb are the red, green and blue
        components of the Colour. The iiiii value indicates the intensity value.

        Args:
            num (int): fiber ## (01 - 20)
                       num=0 means measure all self.count_fiber fibers; if >0 the selected LED is measured
            count_fiber (int):

        Returns:
            numpy array (np.float64): [[rrr, ggg, bbb, iiiii], [], [], []]
        """

        num = int(num)
        if num < 0 or num > self.count_fiber:
            raise ValueError(f"num need to be in [0; {self.count_fibers}]. It was {num}.")

        result = np.array([])
        nplist = []
        if num > 0:
            b = num
            e = num + 1
        else:
            b = 0
            e = self.count_fiber
        for k in range(b, e):
            cmd = "getrgbi" + f"{(int(k+1)):02d}"
            try:
                response = self.request(cmd, timeout=5.0)
                #print(f"{k}: {cmd}, {response}")
                lst = response.split(' ')
                nplist.append(np.array([np.float64(n) for n in lst]))
            except Exception as ex:
                global DEBUG
                _log = getLogger(__name__, DEBUG)
                _log.error(f"LED analyzer error (get_rgbi_num) {ex}, got '{response}'")
                raise
        result = np.array(nplist)
        return result

    # getINTENSITY##
    def get_intensity_num(self, num: int) -> int:
        """
        This command is used to get the Intensity value for the LED under the Fiber number.
        This command should be preceded by a capture command to ensure valid LED data is stored
        in the memory of the LED Analyser.

        Args:
            num (int): represents the Fiber Number and is a number in the range 01 – 20

        Returns:
            int: intensity value
        """
        try:
            cmd = "getintensity" + f"{(int(num)):02d}"
            response = int(self.request(cmd, timeout=5.0))
        except Exception:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, get_intensity_num")
            raise
        return response

    # Set Functions------------------------------------------------------------------------------------

    # SetIntGain##xxx
    def set_intgain_num(self, num: int, factor: int) -> bool:
        """
        This command allows the user to adjust the Intensity Gain Factor for each Fiber.

        Args:
            num (int): represents the Fiber Number and is a number in the range 01 – 20
            factor (int): represents a 3 digit gain factor, default 100

        Returns:
            bool: False - failed, True - success
        """
        cmd = "setintgain" + f"{(int(num)):02d}" + f"{(int(factor)):03d}"
        response = self.request(cmd)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, set_intgain_num, %s", response, exc_info=1)
            return False

    # SetFactor##
    def set_factor(self, factor: int) -> bool:
        """
        This command allows the user to adjust the Exposure Factor for all Fibers.

        Args:
            factor (int): represents the Factor Number and is in the range 01 – 15 (default 01).

        Returns:
            bool: False - failed, True - success
        """
        cmd = "setfactor" + f"{(int(factor)):02d}"
        response = self.request(cmd)
        if (self.RESPONSE_OK in response):
            return True
        else:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.error("LED analyzer error, set_factor, %s", response, exc_info=1)
            return False

#-----------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------

if __name__ == "__main__":

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # TESTS have been moved out to module: test_feasa.py
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    print("DONE.")

# END OF FILE