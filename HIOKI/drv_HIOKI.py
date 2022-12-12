import socket
from time import sleep

VERSION = "0.0.1"
__version__ = VERSION


class HIOKI_DEV(object):

    def __init__(self, BT_HOST, BT_PORT, SW_HOST, SW_PORT):
        """Initialize the object with IP address and port number.

        Parameters
            ----------
            BT_HOST: string, BT3561A IP address   
            BT_PORT: int, BT3561A port number
            SW_HOST: string, SW1001 IP address   
            SW_PORT: int, SW1001 port number """

        self.BT_HOST = str(BT_HOST)
        self.BT_PORT = int(BT_PORT)
        self.SW_HOST = str(SW_HOST)
        self.SW_PORT = int(SW_PORT)

#================ HIOKI BT3561A FUNCTIONS ============================================================
    def BT_get_idn(self):
        """ Queries the device ID
            Returns: <Manufacturer's name>, 
                     <Model name>,0,
                     <Software version> """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = '*IDN?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_reset(self):
        """ Initializes the device. """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = '*RST\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            bt_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_self_test(self):
        """ Initiates a self-test and queries the result.
            Returns: int,   0 - No Errors
                            1 - RAM Error
                            2 - EEPROM Error
                            3 - RAM and EEPROM Errors """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = '*TST?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            return int(result.decode('ascii'))
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_function(self, mode):
        """ Select the Measurement Mode Setting.

            Parameters
            ----------
            mode: string, 'RV', 'RES', 'VOLT' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (mode == 'RV') or (mode == 'RES') or (mode == 'VOLT'):
                MESSAGE = (f':FUNC {mode}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_function: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_function(self):
        """ Query the Measurement Mode Setting.

            Returns: string, 'RV', 'RES', 'VOLT' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':FUNC?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_resistance_range(self, range):
        """ Set the Resistance Measurement Range.

            Parameters
            ----------
            range: float, resistance 0...3100 Ohm """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (range >= 0) and (range <= 3100):
                MESSAGE = (f':RES:RANG {range}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_resistance_range: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_resistance_range(self):
        """ Query the Resistance Measurement Range.

            Returns: float, 3.0000E-3/ 30.000E-3/ 300.00E-3/
                     3.0000E+0/ 30.000E+0/ 300.00E+0/ 3.0000E+3 """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':RES:RANG?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            return float(result.decode('ascii'))
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_voltage_range(self, range):
        """ Set the Voltage Measurement Range.

            Parameters
            ----------
            range: float, voltage -300...300 V """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (range >= -300) and (range <= 300):
                MESSAGE = (f':VOLT:RANG {range}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_voltage_range: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_voltage_range(self):
        """ Query the Voltage Measurement Range.

            Returns: float, 6.00000E+0/ 60.0000E+0/100.000E+0/
                            300.000E+0 """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':VOLT:RANG?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            return float(result.decode('ascii'))
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex    

    def BT_set_autorange(self, state):
        """ Set the Auto-Ranging Setting.

            Parameters
            ----------
            state: int 1|0 or string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (state == 0) or (state == 1) or (state == 'ON') or (state == 'OFF'):
                MESSAGE = (f':AUT {state}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_autorange: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_autorange(self):
        """ Query the Auto-Ranging Setting.

            Returns: string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':VOLT:RANG?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_adjustment_clear(self):
        """ Cancel Zero-Adjustment. """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':ADJ:CLEA\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            bt_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_adjustment(self):
        """ Execute Zero Adjustment and Query the Result.

            Returns: int, 0 - Zero adjustment succeeded
                          1 - Zero adjustment failed """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':ADJ?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            return int(result.decode('ascii'))
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_syst_calibration(self):
        """ Execute Self-Calibration. """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':SYST:CAL\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            bt_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_syst_calibration_auto(self, state):
        """ Self-Calibration State and Setting.

            Parameters
            ----------
            state: int 1|0 or string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (state == 0) or (state == 1) or (state == 'ON') or (state == 'OFF'):
                MESSAGE = (f':SYST:CAL:AUTO {state}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_autorange: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_syst_calibration_auto(self):
        """ Query the Self-Calibration State.

            Returns: string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':SYST:CAL:AUTO?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex     

    def BT_set_syst_klock(self, state):
        """ Set the Key-Lock State.

            Parameters
            ----------
            state: int 1|0 or string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (state == 0) or (state == 1) or (state == 'ON') or (state == 'OFF'):
                MESSAGE = (f':SYST:KLOC {state}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_syst_klock: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_syst_klock(self):
        """ Query the Key-Lock State. 

            Returns: string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':SYST:KLOC?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_local_control(self):
        """ Set Local Control. """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = (f':SYST:LOC\r\n')
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            bt_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_trigger_source(self, state):
        """ Set the Trigger Source.

            Parameters
            ----------
            state: string 'IMM'|'EXT' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (state == 'IMM') or (state == 'EXT'):
                MESSAGE = (f':TRIG:SOUR {state}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_trigger_source: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_get_trigger_source(self):
        """ Query the Trigger Source.

            Returns: string 'IMMEDIATE'|'EXTERNAL' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':TRIG:SOUR?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = bt_sock.recv(1024)
            bt_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def BT_set_continous_measurement(self, state):
        """ Sets continuous measurement ON|OFF. 
        Parameter
        ---------
        state: int 1|0 or string 'ON'|'OFF' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            if (state == 0) or (state == 1) or (state == 'ON') or (state == 'OFF'):
                MESSAGE = (f':INIT:CONT {state}\r\n')
                bt_sock.sendall(bytes(MESSAGE,'utf-8'))
                bt_sock.close()
                return
            else:
                bt_sock.close()
                raise ValueError('Error, BT_set_continous_measurement: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def BT_read(self):
        """ Execute a Measurement and Read the Measured Values.

            Returns: string 'IMMEDIATE'|'EXTERNAL' """
        try:
            bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bt_sock.settimeout(10)
            bt_sock.connect((self.BT_HOST, self.BT_PORT))
            MESSAGE = ':READ?\r\n'
            bt_sock.sendall(bytes(MESSAGE,'utf-8'))
            resp = bt_sock.recv(1024)
            bt_sock.close()
            if (self.BT_get_function() == 'RV'):
                lst = resp.decode('ascii').split(',')
                result = []
                result.append(float(lst[0]))
                result.append(float(lst[1]))                                    
            else:
                result = resp.decode('ascii').rstrip()        
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        
#================ HIOKI SW1001 FUNCTIONS =============================================================
    def SW_get_idn(self):
        """ Queries the device ID (ID code).
            Returns: <Manufacturername>,
                     <Modelname>,
                     <Serial No.>,
                     <Software version> """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = '*IDN?\r\n'
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = sw_sock.recv(1024)
            sw_sock.close()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def SW_set_reset(self):
        """ Initializes the device. """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = '*RST\r\n'
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            sw_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def SW_self_test(self):
        """ Initiates a self-test and queries the result.
            Returns: string, 'PASS'|'FAIL' """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = '*TST?\r\n'
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = sw_sock.recv(1024)
            sw_sock.close()
            result = result.decode('ascii').rstrip()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def SW_set_wire_mode(self, slot, mode):
        """ Sets the connection method for a given slot.

        Parameters
        ---------
        slot: int, slot number 
        mode: int, wire mode (2 or 4) """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if ((slot >= 1) and (slot <= 3)) and ((mode == 2) or (mode == 4)):
                MESSAGE = (f':SYST:MOD:WIRE:MODE {slot},WIRE{mode}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                MESSAGE = '*OPC?\r\n'
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                res = sw_sock.recv(1024)
                sw_sock.close()
                return
            else:
                sw_sock.close()
                raise ValueError('Error, SW_set_wire_mode: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_get_wire_mode(self, slot):
        """ Queries the connection method for a given slot.

        Parameter
        ---------
        slot: int, slot number 
        
        Returns: string 'WIRE2' or 'WIRE4' """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if (slot >= 1) and (slot <= 3):
                MESSAGE = (f':SYST:MOD:WIRE:MODE? {slot}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                result = sw_sock.recv(1024)
                sw_sock.close()
                result = result.decode('ascii').rstrip()
                return result
            else:
                sw_sock.close()
                raise ValueError('Error, SW_get_wire_mode: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_set_shield_mode(self, slot, mode):
        """ Sets the shield wire connection destination for a given slot.

        Parameters
        ---------
        slot: int, slot number 
        mode: string, OFF/GND/TERM1/TERM2/TERM3/T1T3/SNS2L """
        try:
            arr_mode = ['OFF','GND','TERM1','TERM2','TERM3','T1T3','SNS2L']
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if ((slot >= 1) and (slot <= 3)) and (mode in arr_mode):
                MESSAGE = (f':SYST:MOD:SHI {slot},{mode}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                MESSAGE = '*OPC?\r\n'
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                res = sw_sock.recv(1024)
                sw_sock.close()
                return
            else:
                sw_sock.close()
                raise ValueError('Error, SW_set_shield_mode: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_get_shield_mode(self, slot):
        """ Queries the shield wire connection destination for a given slot.

        Parameter
        ---------
        slot: int, slot number 
        
        Returns: string, OFF/GND/TERM1/TERM2/TERM3/T1T3/SNS2L """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if (slot >= 1) and (slot <= 3):
                MESSAGE = (f':SYST:MOD:SHI? {slot}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                result = sw_sock.recv(1024)
                sw_sock.close()
                result = result.decode('ascii').rstrip()
                return result
            else:
                sw_sock.close()
                raise ValueError('Error, SW_get_shield_mode: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_get_module_count(self, slot):
        """ Returns to the specified relay opening/closing frequency.

        Parameter
        ---------
        slot: int, slot number 
        
        Returns: int, <Opening/closing frequency> = 0 to 1000000000 """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if (slot >= 1) and (slot <= 3):
                MESSAGE = (f':SYST:MOD:COUN? {slot}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                result = sw_sock.recv(1024)
                sw_sock.close()
                return int(result.decode('ascii'))
            else:
                sw_sock.close()
                raise ValueError('Error, SW_get_module_count: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_close(self, slot, channel):
        """ Closes the specified slot and channel. 
            The channel that was closed previously is automatically opened.

        Parameter
        ---------
        slot: int, slot number 
        channel; int, channel number """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            if ((slot >= 1) and (slot <= 3)) and ((channel >= 1) and (channel <= 22)):
                MESSAGE = (f':CLOS {slot}{channel:02d}\r\n')
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                MESSAGE = '*OPC?\r\n'
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                res = sw_sock.recv(1024)
                sw_sock.close()
            else:
                sw_sock.close()
                raise ValueError('Error, SW_close: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex

    def SW_open(self):
        """ Opens all channels. """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = (f':OPEN\r\n')
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            sw_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
    
    def SW_set_raw_command(self, cmd):
        """ Sets raw command and returns error.

            Parameters
            ----------
            cmd : str, command """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = cmd + '\r\n'
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            sw_sock.close()
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex

    def SW_set_raw_query(self, cmd):
        """ Sets raw command and returns error.

            Parameters
            ----------
            cmd : str, command 
            
            Returns
            result : string """
        try:
            sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sw_sock.settimeout(10)
            sw_sock.connect((self.SW_HOST, self.SW_PORT))
            MESSAGE = cmd + '\r\n'
            sw_sock.sendall(bytes(MESSAGE,'utf-8'))
            result = sw_sock.recv(1024)
            sw_sock.close()
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
    
#================ BATTERY TEST SYSTEM =================================================================
    def measure_channnel(self, channel):
        """ Measures the voltage and impedance of the a given channel. 
         
         Parameters
         ----------
         channel: int, channel number 1 ... 22 

         Returns: array[0]: float, resistance, Ω mode 
                  array[1]: float, voltage, V mode """
        try:
            channel = int(channel)
            if ((channel >= 1) and (channel <= 22)):

                # SW1001 operations ==================
                if (channel <= 11):
                    #SLOT 1
                    self.SW_set_shield_mode(1, 'GND')
                    self.SW_set_wire_mode(1, 4)
                    self.SW_close(1, channel)
                else:
                    #SLOT 2
                    channel = channel - 11
                    self.SW_set_shield_mode(2, 'GND')
                    self.SW_set_wire_mode(2, 4)
                    self.SW_close(2, channel)  
                # BT3561A operations =================
                bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                bt_sock.settimeout(10)
                bt_sock.connect((self.BT_HOST, self.BT_PORT))
                #[BT3561A] :READ? Execute single measurement using BT3561A.
                MESSAGE = b':READ?\r\n'
                bt_sock.sendall(MESSAGE)
                #[BT3561A] 1.0258E-3 Receive measured values.
                resp = bt_sock.recv(1024)
                bt_sock.close()

                # bt_sock should be closed before invoking BT_get_function!
                bt_function_type = self.BT_get_function()

                if (bt_function_type == 'RV'):
                    lst = resp.decode('ascii').split(',')
                    result = []
                    result.append(float(lst[0]))
                    result.append(float(lst[1]))                                    
                else:
                    result = float(resp.decode('ascii'))
                return result
            else:
                raise ValueError('Error, measure_channnel: invalid channel number')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex
    
    def measure_all_channels(self):
        """ Measures the impedance of each of 22 channels. 

            Returns: array[0..43]: float, Ch1.Impedance, Ch1.Voltage, Ch2.Impedance, Ch2.Voltage, ... """
        try:
            result = []
            # bt_sock should be closed before invoking BT_get_function!
            bt_function_type = self.BT_get_function()
            for i in range(22):
                # Channel 1/Slot1 or Channel 1/Slot 2. Needs to switch shield mode and wire mode
                if (i == 0):
                    self.SW_set_shield_mode(1, 'GND')
                    self.SW_set_shield_mode(1, 'GND')
                    self.SW_set_wire_mode(1, 4)
                    self.SW_set_wire_mode(1, 4)
                if (i == 11):
                    self.SW_set_shield_mode(2, 'GND')
                    self.SW_set_shield_mode(2, 'GND')
                    self.SW_set_wire_mode(2, 4)
                    self.SW_set_wire_mode(2, 4)
                if (i < 11):
                    #SLOT 1
                    self.SW_close(1, i+1)
                else:
                    #SLOT 2
                    self.SW_close(2, (i-11)+1)  
                bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                bt_sock.settimeout(10)
                bt_sock.connect((self.BT_HOST, self.BT_PORT))
                #[BT3561A] :READ? Execute single measurement using BT3561A.
                MESSAGE = b':READ?\r\n'
                bt_sock.sendall(MESSAGE)
                #[BT3561A] 1.0258E-3 Receive measured values.
                resp = bt_sock.recv(1024)
                bt_sock.close()

                if (bt_function_type == 'RV'):
                    lst = resp.decode('ascii').split(',')
                    result.append(float(lst[0]))
                    result.append(float(lst[1]))                                    
                else:
                    result.append(float(resp.decode('ascii')))
                    result.append(float(0))
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
    

    