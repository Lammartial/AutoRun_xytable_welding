from typing import Tuple, List
from icmplib import ping


def host_up(hostname: str) -> bool:
    """Check single hostname or IP address by pinging it up to twice with short timeout.

    Args:
        hostname (str): _description_

    Returns:
        bool: True = host responded, False = host down or unreachable
    
    """

    host = ping(hostname, count=2, interval=0.2, timeout=0.5)
    return host.packets_sent == host.packets_received


def check_list_of_hosts(hostlist: List[str]) -> List[Tuple[str, bool]]:
    return [(h, host_up(h)) for h in hostlist]


def find_hosts_down(hostlist: List[str]) -> List[Tuple[str, bool]]:
    return [h for h, p in [(h, host_up(h)) for h in hostlist] if p == False]


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    NETWORK_STR = "172.25.101"
    hosts = [
        f"{NETWORK_STR}.102",
        f"{NETWORK_STR}.50",
        f"{NETWORK_STR}.41",
        f"{NETWORK_STR}.182",
    ]

    print(check_list_of_hosts(hosts))
    print(find_hosts_down(hosts))

# END OF FILE