import pyvisa as visa
import time
from typing import List, Tuple

# NOTE: the default pyvisa import works well for Python 3.6+
# if you are working with python version lower than 3.6, use 'import visa' instead of import pyvisa as visa

# start of Untitled
def daq970A_display_on_off(state: bool):
    rm = visa.ResourceManager()
    DAQ970A = rm.open_resource('TCPIP0::192.168.1.179::inst0::INSTR')
    DAQ970A.write(':DISPlay %d' % (state))
    DAQ970A.close()
    rm.close()
# end of Untitled

# start of Untitled
def daq970A_display_on():
   rm = visa.ResourceManager()
   DAQ970A = rm.open_resource('TCPIP0::192.168.1.179::inst0::INSTR')
   DAQ970A.write(':DISPlay %d' % (1))
   DAQ970A.close()
   rm.close()
# end of Untitled