import socket

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

    def bt_initiate_continous(self, state):
        """ Sets continuous measurement. 
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
                raise ValueError('Error, set_output_state: invalid parameters')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex        

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
                bt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                bt_sock.settimeout(10)
                sw_sock.settimeout(10)
                bt_sock.connect((self.BT_HOST, self.BT_PORT))
                sw_sock.connect((self.SW_HOST, self.SW_PORT))
                #[SW1001] :SYST:MOD:WIRE:MODE 1,WIRE4 Set the SLOT 1 connection method to 2-wire.
                MESSAGE = ':SYST:MOD:WIRE:MODE 1,WIRE4\r\n'
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                #[SW1001] :CLOSE 101 Select SLOT 1, CH1.
                if (channel <= 11):
                    #SLOT 1
                    ch_str  = f"{channel:02d}"
                    MESSAGE = ':CLOSE 1' + ch_str + '\r\n'
                else:
                    #SLOT 2
                    channel = channel - 11
                    ch_str  = f"{channel:02d}"
                    MESSAGE = ':CLOSE 2' + ch_str + '\r\n'
                sw_sock.sendall(bytes(MESSAGE,'utf-8'))
                #[SW1001] *OPC? Check that the channel relay has been closed.
                MESSAGE = b'*OPC?\r\n'
                sw_sock.sendall(MESSAGE)           
                #[SW1001] 1 Receive a response “1” to the *OPC? query.
                resp = sw_sock.recv(1024)
                if (resp.decode('ascii') == '1\r\n'):
                    #[BT3562A] :READ? Execute single measurement using BT3562A.
                    MESSAGE = b':READ?\r\n'
                    bt_sock.sendall(MESSAGE)
                    #[BT3562A] 1.0258E-3 Receive measured values.
                    resp = bt_sock.recv(1024)
                    lst = resp.decode('ascii').split(',')
                    result = []
                    result.append(float(lst[0]))
                    result.append(float(lst[1]))                                    
                    bt_sock.close()
                    sw_sock.close()
                    return result
                else:
                    bt_sock.close()
                    sw_sock.close()
                    raise ValueError('Error, measure_channnel: invalid SW1001 response')
            else:
                raise ValueError('Error, measure_channnel: invalid channel number')
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex
    
    def all_channels_zero_adjustment(self):
        """ Measures the impedance of each of 22 channels. 

         Returns: array[0..21]: float, channel resistance, Ω mode """
        try:
            result = []
            for i in range(22):
                ch_result = self.measure_channnel(i+1)
                result.append(ch_result[0])
            return result
        except TypeError as ex:
            return ex       
        except TimeoutError as ex:
            return ex
        except ValueError as ex:
            return ex
    

    