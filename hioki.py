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

class HiokiBaseDevice(Eth2SerialDevice):

    def get_idn(self) -> str:
        """
        Queries the device ID

        Returns:
            str: <Manufacturer's name>,<Model name>,0,<Software version>

        """
        return self.request("*IDN?")

# ... add more ...


class Hioki_BT3561A(HiokiBaseDevice):

    def set_resistance_range(self, range: float) -> bool:
        """Set the Resistance Measurement Range.

        Args:
            range (float): resistance 0...3100 Ohm

        Returns:
            bool: _description_
        """

        assert (range >= 0) and (range <= 3100), ValueError('invalid parameter for resistance: 0 < R <= 3100')
        return self.send(f':RES:RANG {range}')

# add more ...


class Hioki_SW1001(HiokiBaseDevice):

    def set_wire_mode(self, slot: int, mode: int) -> str:
        """
        Sets the connection method for a given slot.

        Args:
            slot (int): slot number 1 .. 3
            mode (int): wire mode 2 or 4

        Returns:
            str: _description_
        """

        assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')
        assert ((mode == 2) or (mode == 4)), ValueError('Invalid mode. Only 2 or 4 allowed.')

        self.send(f":SYST:MOD:WIRE:MODE {slot},WIRE{mode}")
        return self.request("*OPC?")

    def get_wire_mode(self, slot: int) -> int:
        assert ((slot >= 1) and (slot <= 3)), ValueError('Invalid slot number. Allowed range is 1 .. 3')

        response = self.request(f":SYST:MOD:WIRE:MODE? {slot}")
        return int(response)  # this is NOT safe!


    def set_new_ip_address(self, new_ip: str, new_port: int = 23,
                           new_subnet_mask: str = "255.255.255.0", new_default_gateway: str = "0.0.0.0",
                           pause_reboot: float = 5.0):
        """_summary_

        Args:
            new_ip (str): _description_
            new_port (int, optional): _description_. Defaults to 23.
            new_subnet_mask (str, optional): _description_. Defaults to "255.255.255.0".
            new_default_gateway (str, optional): _description_. Defaults to "0.0.0.0".
            pause_reboot (float, optional): _description_. Defaults to 5.0.
        """
        # remove the dots from the strings
        _ip_str = new_ip.replace('.' , ',')
        _subnet_mask = new_subnet_mask.replace('.' , ',')
        _default_gateway = new_default_gateway.replace('.' , ',')
        _port = int(new_port)
        # Set the IP address for the device.
        # :SYSTem:COMMunicate:LAN:IPADdress <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:IPAD {_ip_str}')
        # Set the LAN subnet mask.
        # :SYSTem:COMMunicate:LAN:SMASK <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:SMASK {_subnet_mask}')
        # Set the address for the default gateway.
        # :SYSTem:COMMunicate:LAN:GATeway <Value 1>,<Value 2>,<Value 3>,<Value 4>
        self.send(f':SYST:COMM:LAN:GAT {_default_gateway}')
        # Specify the communication command port No.
        # :SYSTem:COMMunicate:LAN:CONTrol <1 - 9999>
        self.send(f':SYST:COMM:LAN:CONT {_port}')
        #:SYSTem:COMMunicate:LAN:UPDate
        self.send(f':SYST:COMM:LAN:UPD')
        # now we need to update our communication host and port internally...
        self.host = new_ip
        self.port = new_port
        # ...and wait for reboot of the device.
        #
        # !!! USER has to toggle a switch also !!!
        #
        sleep(pause_reboot)
        try:
            # check if the new address is available
            result = self.request(f"SYST:COMM:LAN:IPAD?").replace(',','.')
            _log.info('IP address has been set: %s' , result)
        except NameError as ex:
            _log.error(ex)
        except ConnectionRefusedError as ex:
            _log.error(ex)

# add more ...


#--------------------------------------------------------------------------------------------------
class Hioki_BT3561A_20Channels(object):
    """This is a class that holds a BT3561A and a SW1001 device providing convenience functions."""

    def __init__(self, BT_HOST, BT_PORT, SW_HOST, SW_PORT):
        self.bt = Hioki_BT3561A(BT_HOST, BT_PORT)
        self.sw = Hioki_SW1001(SW_HOST, SW_PORT)

    def measure_channel(self, chan):
        pass

# ... add more ...


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from time import sleep

    res : float = 0

    # predefined resource ID
    BT_IP_STR = "192.168.1.202"     # BT3561A IP addr
    BT_PORT = 23                    # BT3561A port
    SW_IP_STR = "192.168.1.201"     # SW1001 IP addr
    SW_PORT = 23                    # SW1001 port

    # 1. Create an instance of 20 channel MUXER with HIOKI ACIR measurement device class
    hioki = Hioki_BT3561A_20Channels(BT_IP_STR, BT_PORT, SW_IP_STR, SW_PORT)

    # 2. ==== BT3561A functions ==========================================================================
    # *IDN?
    print('BT3561A ID: ', hioki.bt.get_idn())

    # *RST
    #hioki.bt.set_reset()

    # *TST?
    print('BT3561A TEST: ', hioki.bt.self_test())

    # Set function 'RV'
    hioki.bt.set_function('RV')

    # Get function
    print('BT3561A Func: ', hioki.bt.get_function())

    # Set resistance range 0.1 Ohm
    hioki.bt.set_resistance_range(0.1)

    # Get resistance range
    print('BT3561A Resistance Range: ', hioki.bt.get_resistance_range())

    # Set voltage range 6 V
    hioki.bt.set_voltage_range(6)

    # Get voltage range
    print('BT3561A Voltage Range: ', hioki.bt.get_voltage_range())

    # Set auto range ON
    hioki.bt.set_autorange(1)

    # Get auto range
    print('BT3561A Auto Range : ', hioki.bt.get_autorange())

    # Adjust zero, 0 - success
    #print('BT3561A Zero Adjustment: ', hioki.bt.set_adjustment())

    # Adjust clear
    hioki.bt.set_adjustment_clear()

    # System calibration
    hioki.bt.set_syst_calibration()

    # System calibration auto 1 - ON, 0 - OFF
    hioki.bt.set_syst_calibration_auto(0)

    # Get system key lock
    print('BT3561A Key Lock: ', hioki.bt.get_syst_klock())

    # Set system key lock OFF
    hioki.bt.set_syst_klock(0)

    # System Local
    hioki.bt.set_local_control()

    # Set trigger source
    hioki.bt.set_trigger_source('IMM')

    # Get trigger source
    print('BT3561A trig source: ', hioki.bt.get_trigger_source())

    # =============== READ? ============================

    # IMPORTANT! Set continuous measurement OFF.
    hioki.bt.set_continous_measurement('OFF')

    sleep(0.1)

    print('BT3561A measurement ', hioki.bt.read())

    hioki.bt.set_continous_measurement('ON')

    # 3. ==== SW1001 functions ===========================================================================

    # *IDN?
    print('SW1001 ID: ', hioki.sw.get_idn())

    # *RST
    #hioki.sw.set_reset()

    # *TST?
    #print('SW1001 Self Test: ', hioki.sw.self_test())

    # Raw query command
    #print('SW1001 Get Scan List: ', hioki.sw.set_raw_query(':SCAN?'))

    # Raw command
    #hioki.sw.set_raw_command(':SYST:MOD:SHI 1,GND')

    # IMPORTANAT! Switching the channel:
    # 1. Set wire mode
    #hioki.sw.set_wire_mode(1, 4)
    # 2. Set shield mode (if needed)
    #hioki.sw.set_shield_mode(1, 'TERM2')
    # 3. CLOSE channel
    #hioki.sw.close(1, 1)

    #print('SW1001 Slot1 Wire Mode: ', hioki.sw.get_wire_mode(1))
    #print('SW1001 Slot1 Shield Mode: ', hioki.sw.get_shield_mode(1))

    # Get module count
    #print('SW1001 Slot1 Count: ', hioki.sw.get_module_count(1))
    #print('SW1001 Slot2 Count: ', hioki.sw.get_module_count(2))

    # CLOSE channel
    #hioki.sw.close(1, 1)

    # OPEN
    #hioki.sw.open()

    # 4. ==== Cells tester (BT3561A + SW1001) functions ================================================

    # IMPORTANT! Set continuous measurement OFF.
    hioki.bt.set_continous_measurement('OFF')

    sleep(0.1)

    # measure single channel (1 ... 22)
    #print(hioki.measure_channnel(15))

    # measure all 22 4-wire channels (Could be useful for Zero-adjustment procedure)
    print(hioki.measure_all_channels())

    hioki.sw.open()

    hioki.bt.set_continous_measurement('ON')

    print("DONE.")


# END OF FILE
