# This script is used to set up LAN configuration on HIOKI SW1001
#
# How to use:
#
# 1. Connect the LAN cable to the SW1001.
# 2. Set communication setting mode switch (DFLT/USER) on the back of the SW1001 to DFLT. 
#    Default: IP 192.168.0.254, Port 23.
# 3. Set the IP of the PC to the same subnetwork. For example 192.168.0.10.
# 4. Define the IP address of the SW1001 below.
# 5. Run script.
# 6. Switch off the SW1001. Set communication setting mode switch (DFLT/USER) to USER. Switch on the device.
# 7. New IP has been applied.

import socket
from time import sleep

VERSION = "0.0.1"
__version__ = VERSION

# DEFAULT ID
DEFAULT_IP_STR = "192.168.0.254"
DEFAULT_PORT_INT = 23

# USER ID
SW1001_IP_STR = "192.168.1.101" 
SW1001_PORT_INT = 23

if __name__ == "__main__":
    try:
       with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((DEFAULT_IP_STR, DEFAULT_PORT_INT))
            IP_STR = SW1001_IP_STR.replace('.' , ',')
            # Set the IP address for the device.
            # :SYSTem:COMMunicate:LAN:IPADdress <Value 1>,<Value 2>,<Value 3>,<Value 4>
            MESSAGE = ':SYST:COMM:LAN:IPAD ' + IP_STR + '\r\n'
            s.sendall(bytes(MESSAGE,'utf-8'))
            # Set the LAN subnet mask.            
            # :SYSTem:COMMunicate:LAN:SMASK <Value 1>,<Value 2>,<Value 3>,<Value 4>
            MESSAGE = ':SYST:COMM:LAN:SMASK 255,255,255,0\r\n'
            s.sendall(bytes(MESSAGE,'utf-8'))
            # Set the address for the default gateway.
            # :SYSTem:COMMunicate:LAN:GATeway <Value 1>,<Value 2>,<Value 3>,<Value 4>
            MESSAGE = ':SYST:COMM:LAN:GAT 0,0,0,0\r\n'
            s.sendall(bytes(MESSAGE,'utf-8'))
            # Specify the communication command port No.
            # :SYSTem:COMMunicate:LAN:CONTrol <1 - 9999>
            MESSAGE = ':SYST:COMM:LAN:CONT 23\r\n'
            s.sendall(bytes(MESSAGE,'utf-8'))
            #:SYSTem:COMMunicate:LAN:UPDate
            MESSAGE = ':SYST:COMM:LAN:UPD\r\n'
            s.sendall(bytes(MESSAGE,'utf-8'))

            sleep(2)

            MESSAGE = "SYST:COMM:LAN:IPAD?\r\n"
            s.sendall(bytes(MESSAGE,'utf-8'))
            data = s.recv(1024)
            result = data.decode('ascii').replace(',','.')
            print('IP address has been set: ' , result)

            s.close()
    except NameError as ex:
        print(ex)
    except ConnectionRefusedError as ex:
        print(ex)
    
    print("DONE.")

    sleep(2)
    
# END OF FILE

