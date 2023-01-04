from typing import List, Tuple
import atexit
import contextlib
from time import sleep
from pyvisa import ResourceManager, constants

# NOTE: the default pyvisa import works well for Python 3.6+
# if you are working with python version lower than 3.6, use 'import visa' instead of import pyvisa as visa


# def handle_event(resource, event, user_handle):
#     resource.called = True
#     print(f"Handled event {event.event_type} on {resource}")

# #
# # Normal way to use PyVISA and callbacks is in with ... statement
# #
# rm = ResourceManager
# with rm.open_resource("TCPIP::192.168.0.2::INSTR") as instr:
#     instr.called = False
#     # Type of event we want to be notified about
#     event_type = constants.EventType.service_request
#     # Mechanism by which we want to be notified
#     event_mech = constants.EventMechanism.queue
#     wrapped = instr.wrap_handler(handle_event)

#     user_handle = instr.install_handler(event_type, wrapped, 42)
#     instr.enable_event(event_type, event_mech, None)

#     # Instrument specific code to enable service request
#     # (for example on operation complete OPC)
#     instr.write("*SRE 1")
#     instr.write("INIT")

#     while not instr.called:
#         sleep(10)

#     instr.disable_event(event_type, event_mech)
#     instr.uninstall_handler(event_type, wrapped, user_handle)

class OurVisaDevice(object):
    """Base class for our VISA devices."""

    def __init__(self, resource_string: str) -> None:
        """Initializes the variables and opens a connection to the resource. 

        Args:
            resource_string (str): VISA Resource address string
        """
        self.device = None
        self.rm = ResourceManager()
        self.resource_string = resource_string
        ## this is another way to make sure things are cleaned up
        #atexit.register(self.close)

    # # the cleanup function needs to be named close() with this way
    # def __new__(cls, *args, **kwargs):
    #     instance = super(OurVisaDevice, cls).__new__(cls)
    #     instance.__init__(*args, **kwargs)
    #     return contextlib.closing(instance)

    #
    # by defining the next two functions we can use the
    # with OurVisaDevice("xxx") as device: 
    #     device.write("xxxx")
    #     ...
    # statement, which ensures that the close() function is called in any circumstances (exception etc)
    #
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.device:
            self.device.close()
        if self.rm:
            self.rm.close()

    # convenience functions
    def list_resources(self) -> List[str,]:
        return self.rm.list_resources()

    def open(self, resource_string: str = None):
        if resource_string:
            _res_str = resource_string
        else:
            _res_str = self.resource_string
        try:
            self.device = self.rm.open_resource(_res_str)
            self.resource_string = _res_str
            self.device.read_termination = "\n"
            self.device.write_termination = "\n"
        except Exception as ex:
            # hier kann man eine Gegenmaßnahme treffen            
            raise ex

    def close(self) -> None:
        if self.device:
            self.device.close()
        if self.rm:
            self.rm.close()

    def write(self, command: str) -> None:
        # hier könnte man noch checken ob das Gerät geöffnet ist
        # if self.device.is_open() - gibts die funktion ?
        if not self.device: 
            self.open()
        self.device.write(command)
        
    def read(self) -> None:
        if not self.device: 
            self.open()
        return self.device.read()

    def query(self, request: str) -> object:
        if not self.device: 
            self.open()
        return self.device.query(request)
    
    def query_ascii_values(self, request: str) -> object:
        if not self.device: 
            self.open()
        return self.device.query_ascii_values(request)

    def assert_trigger(self):
        if not self.device: 
            self.open()
        self.device.assert_trigger()

    def wait_for_srq(self):
        if not self.device: 
            self.open()
        self.device.wait_for_srq()

    def identify(self) -> object:
        return self.query("*IDN?")

# END OF FILE