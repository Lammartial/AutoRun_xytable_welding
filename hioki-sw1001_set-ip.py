import argparse
from rrc.hioki import Hioki_SW1001

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

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("ipv4", type=str, help="The new device address")
parser.add_argument("-p", "--port", type=int, default=23, help="Optionally sets a port address.")
parser.add_argument("-m", "--mask", type=str, default="255.255.255.0", help="Optionally sets a new netmask.")
parser.add_argument("-g", "--gateway", type=str, default="0.0.0.0", help="Optionally sets the default gateway.")

args = parser.parse_args()

# create a SW1001 device with factory default address
SW_default_resource_string = "192.168.0.254:23"
dev = Hioki_SW1001(SW_default_resource_string)

# now set the new IP
dev.set_new_ip_address(args.ipv4, new_port=args.port, new_default_gateway=args.gateway)

print("DONE.")

# END OF FILE