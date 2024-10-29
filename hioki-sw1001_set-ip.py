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
parser.add_argument("-a", "--address", type=str, default="192.168.0.254", help="Optionally defines the present address of HIOKI SW1001 device to be changed.")
parser.add_argument("-p", "--port", type=int, default=23, help="Optionally sets a port address.")
parser.add_argument("-m", "--mask", type=str, default="255.255.255.0", help="Optionally sets a new netmask.")
parser.add_argument("-g", "--gateway", type=str, default=None, help="Optionally sets the default gateway. If None, the gateway is calculated by change last IP tuple to 254.")
args = parser.parse_args()

# we should always set a default gateway
if args.gateway is None:
    _gw = args.ipv4.split(".")
    _gw[3] = 254
    args.gateway = ".".join((str(i) for i in _gw))

# create a SW1001 device with either the
# factory default address and port or the
# one given by the user
SW_default_resource_string = ":".join((args.address, str(args.port)))
dev = Hioki_SW1001(SW_default_resource_string)

# now set the new IP
print(f"Changing Network address on HIOKI SW1001 device at {args.address}:")
print(f"Set Address={args.ipv4}, Port={args.port}, Mask={args.mask}, Gateway={args.gateway}")
#dev.open_socket()
dev.set_new_ip_address(args.ipv4, new_port=args.port, new_subnet_mask=args.mask, new_default_gateway=args.gateway)
#dev.close_socket()
print("DONE.")

# END OF FILE