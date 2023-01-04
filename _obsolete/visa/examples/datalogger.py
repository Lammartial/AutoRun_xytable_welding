from typing import List, Tuple
import time

from base import OurVisaDevice

# NOTE: the default pyvisa import works well for Python 3.6+
# if you are working with python version lower than 3.6, use 'import visa' instead of import pyvisa as visa


#
# Es gibt hier zwei Möglichkeiten der Strukturierung
# 1) dieses File wird wie ein Modul behandelt und verfügt über einzelne Funktionen, die von TestStand aufgerufen werden.
# 2) Hier wird eine neue Klasse DAQ970A(OurVisaDevice) mit Ableitug der Basisklasse definiert. 
#    Dann muß bei TestStand allerdings eine Instanz generiert werden
# Welche besser ist müssen wird noch sehen!
#  

# dies ist für 1)
class DAQ970A(OurVisaDevice):
    """Define a class for the device type and use TestStand to instatiate one for the whole access. 

    Args:
        OurVisaDevice (object): base type inheritance
    """
    # we need to specify the init with super init here as
    # Teststand does not handle inheritance correctly
    def __init__(self, resource_string: str) -> None:        
        super().__init__(resource_string)

    def display_on_off(self, state):
        self.write(":DISPlay {state}")

## die funktionen hier für 2)
#device = OurVisaDevice('TCPIP0::192.168.1.179::inst0::INSTR')
#
#def display_on_off(state: bool):
#    device.write(':DISPlay %d' % (state))


# END OF FILE