"""
 Use LAN connection and "Net Module Configure" software to check CH9121 parameters:
     1. LAN parameters of CH9121: TCP SERVER mode, PORT1 (IP address, port number1), PORT2 (IP address, port number2)
     2. UART parameters of CH9121 (baudrate 57600, Data bits 8, Stop bit 1)

     Check FEASA LED ANALYSER RS232 settings. Default: baudrate 57600, Data bits 8, Stop bit 1

"""
from eth2serial.base import Eth2SerialDevice
import numpy as np

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

    def __init__(self, host: str, port: int, termination: str = "\r\n"):
        """Initialize the object with IP address and port number.

        Args:
            host (str): hostname or IPv4 address
            port (int): port to use for communication
        """
        super().__init__(host, port, termination)

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
        if (self.RESPONSE_OK in response):
            return True 
        else:
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
        response = self.request(cmd)
        if (self.RESPONSE_OK in response):
            return True 
        else:
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
        response = self.request("capturepwm", 5)
        if (self.RESPONSE_OK in response):
            return True 
        else:
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
        response = self.request(cmd, 5)
        if (self.RESPONSE_OK in response):
            return True 
        else:
            _log.error("LED analyzer error, capture_pwm_range, %s", response, exc_info=1) 
            return False 
 
    # Get Functions ----------------------------------------------------------------------------------
     
    # getRGBI##
    def get_rgbi_num(self, num: int) -> np.array:
        """
        This command instructs the LED Analyser to return RGB and Intensity data for fiber ## (01-
        20) in format rrr ggg bbb iiiii where rrr, ggg and bbb are the red, green and blue
        components of the Colour. The iiiii value indicates the intensity value.

        Args:
            num (int): fiber ## (01 - 20)
                       num=0 means measure all 4 fibers; if >0 the selected LED is measured

        Returns:
            numpy array (np.float64): [[rrr, ggg, bbb, iiiii], [], [], []]
        """

        result = np.array([])
        nplist = []
        num = int(num)
        if num > 0:
            b = num 
            e = num + 1
        else:
            b = 0
            e = 4
        for k in range(b, e):
            cmd = "getrgbi" + f"{(int(k+1)):02d}"
            try:
                response = self.request(cmd)                
                #_log.debug(response)
                lst = response.split(' ')
                nplist.append([np.float64(n) for n in lst])
            except Exception:
                _log.error("LED analyzer error, get_rgbi_num")
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
            response = int(self.request(cmd))  
        except Exception:
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
            _log.error("LED analyzer error, set_factor, %s", response, exc_info=1) 
            return False   
#-----------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    HOST = "192.168.1.120"
    PORT = 3000

    # 1. Create an instance of class as device controller
    feasa = FEASA_CH9121(HOST, PORT)

    # 2. Get some data

    # # "CAPTURE" command
    # print(feasa.capture())

    # # "CAPTURE#" command
    # print(feasa.capture_range(1))

    # "CAPTUREPWM" command
    print(feasa.capture_pwm())

    # # "CAPTURE#PWM@@" command
    # print(feasa.capture_pwm_range(1, 7))

    # "getRGBI##" command
    print(feasa.get_rgbi_num(0))
    print(feasa.get_rgbi_num(3))
    
    # # "getINTENSITY##" command
    # print(feasa.get_intensity_num(1))

    # # "SetIntGain##xxx" command
    # print(feasa.set_intgain_num(1, 100))

    # # SetFactor## command
    # print(feasa.set_factor(1))

    print("DONE.")

# END OF FILE