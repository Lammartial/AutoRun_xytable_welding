import argparse
from hioki import Hioki_SW1001

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