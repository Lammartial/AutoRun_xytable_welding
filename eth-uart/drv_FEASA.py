
import socket

#--------------------------------------------------------------------------------------------------
# Fixed Configuration
#
VERSION = "0.0.1"

__version__ = VERSION

    # Use LAN connection and "Net Module Configure" software to check CH9121 parameters:
    # 1. LAN parameters of CH9121 (IP address, port number)
    # 2. UART parameters of CH9121 (baudrate 57600, Data bits 8, Stop bit 1)

    # Check FEASA LED ANALYSER RS232 settings. Default: baudrate 57600, Data bits 8, Stop bit 1
    
#--------------------------------------------------------------------------------------------------
class FEASA_DEV(object):

    def __init__(self, HOST, PORT):
        """Initialize the object with IP address and port number.

        Parameters
            ----------
            HOST: string, CH9121 IP address   
            PORT: int, CH9121 port number """
        self.HOST = HOST
        self.PORT = PORT   

# Capture Fuctions --------------------------------------------------------------------------------

    # CAPTURE 
    def capture(self):
        """ This Auto Range Capture instructs the LED Analyser to capture and store the data of all the
             LED's positioned under the fibers. """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                MESSAGE = b"capture\r\n"
                #MESSAGE = bytes([0x63,0x61,0x70,0x74,0x75,0x72,0x65,0x0A,0x0D])
                s.sendall(MESSAGE)
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    # CAPTURE#
    def capture_range(self, range):
        """ This command uses a pre-selected exposure time designated Range1, Range2 etc. For low
            light or dim LED's use Range 1 and for brighter LED's use higher ranges. 
            
            Parameters
            ----------
            range: int, 1 = Low, 2 = Medium, 3 = High, 4 = Super, 5 = Ultra """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                range_str = str(range)
                MESSAGE = "capture" + range_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex 

    # CAPTUREPWM
    def capture_pwm(self):
        """ Pulse-Width-Modulated(PWM) LED's are switched on and off rapidly to save power and to
            control Intensity. The Analyser automatically determines the correct settings required to
            execute the test. """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                range_str = str(range)
                MESSAGE = b"capturepwm\r\n"
                s.sendall(MESSAGE)
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    # CAPTURE#PWM@@
    def capture_pwm_range(self, range, factor):
        """ This command allows the User to specify the exposure range # and an averaging factor @@
            when testing PWM LED's. 
            
            Parameters 
            ----------
            range: int, represents the exposure Range 1 – 5
            factor: int, represents an averaging factor in the range 1 - 15 """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                range_str = str(range)
                factor_str  = f"{factor:02d}" 
                MESSAGE = "capture" + range_str + "PWM" + factor_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex            

# Get Functions ----------------------------------------------------------------------------------
     
    # getRGBI##
    def get_rgbi_num(self, num):
        """ This command instructs the LED Analyser to return RGB and Intensity data for fiber ## (01-
            20) in format rrr ggg bbb iiiii where rrr, ggg and bbb are the red, green and blue
            components of the Colour. The iiiii value indicates the intensity value. 
            
            Parameters 
            ----------
            num: int, fiber ## (01 - 20) """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                num_str  = f"{num:02d}" 
                MESSAGE = "getrgbi" + num_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex 

    # getINTENSITY##
    def get_intensity_num(self, num):
        """ This command is used to get the Intensity value for the LED under the Fiber number.
            This command should be preceded by a capture command to ensure valid LED data is stored
            in the memory of the LED Analyser. 
            
            Parameters 
            ----------
            num: int, represents the Fiber Number and is a number in the range 01 – 20 """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                num_str  = f"{num:02d}" 
                MESSAGE = "getintensity" + num_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex    
    
# Set Functions------------------------------------------------------------------------------------
 
    # SetIntGain##xxx
    def set_intgain_num(self, num, factor):
        """ This command allows the user to adjust the Intensity Gain Factor for each Fiber. 
            
            Parameters 
            ----------
            num: int, represents the Fiber Number and is a number in the range 01 – 20 
            factor: int, represents a 3 digit gain factor, default 100 """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                num_str  = f"{num:02d}"
                factor_str = f"{factor:03d}" 
                MESSAGE = "setintgain" + num_str + factor_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    # SetFactor##
    def set_factor(self, factor):
        """ This command allows the user to adjust the Exposure Factor for all Fibers.
            
            Parameters 
            ----------
            factor: int, represents the Factor Number and is in the range 01 – 15 (default 01). """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.HOST, self.PORT))
                factor_str = f"{factor:02d}" 
                MESSAGE = "setfactor" + factor_str + "\r\n"
                s.sendall(bytes(MESSAGE,'utf-8'))
                data = s.recv(1024)
                s.close()
                return data.decode('ascii')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex   
#--------------------------------------------------------------------------------------------------