import yaml
import socket
from pathlib import Path
from pprint import pprint
from collections import OrderedDict


CONF_FILENAME_DEV = Path(".") / "station_config_example.yaml"  # development
CONF_FILENAME_PROD = Path("C:/") / "Production" / "station_config.yaml"  # production


#--------------------------------------------------------------------------------------------------
def get_ipv4():
    """
    Helper function that determines the own IPv4 address on the primary interface.
    Falls back to localhost if no IP available.

    Returns:
        str: IPv4 address
    """
    _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _s.settimeout(0)
    try:
        # doesn't even have to be reachable
        _s.connect(('10.254.254.254', 1))
        _ip = _s.getsockname()[0]
    except Exception:
        _ip = "127.0.0.1"
    finally:
        _s.close()
    return _ip

#--------------------------------------------------------------------------------------------------

class StationConfiguration:

    def __init__(self, test_type: str, filename: str | Path = CONF_FILENAME_PROD) -> None:
        # get the own, main IP address
        self._hostname = socket.gethostname()
        self._primary_ip = socket.gethostbyname(socket.gethostname())
        # analyze the IP a bit:
        self._own_network = [int(s) for s in self._primary_ip.split(".")]
        match self._own_network[1]:
            case 71 | 168:
                # RRC Germany
                pass
            case 75:
                # RRC VN
                pass
        if int(self._own_network[2]) > 100:
            self._line_id = abs(self._own_network[2] - 100)
        else:
            self._line_id = self._own_network[2]  # line 1
        self._CONFIG = None
        self.test_type = test_type
        self._filename = Path(filename)
        self._read_yaml_file(self._filename)

    def __str__(self) -> str:
        return f"Test station configuration by YAML file {self._filename}"

    def __repr__(self) -> str:
        return f"StationConfiguration({self.test_type},filename={self._filename})"

    #----------------------------------------------------------------------------------------------

    def _read_yaml_file(self, filepath: str | Path) -> OrderedDict:
        with open(Path(filepath), "rt") as file:
            self._CONFIG = OrderedDict(yaml.safe_load(file))
            # here we could check the YAML file setting of test_type
            self._CONFIG["test_type"] = self.test_type


    #---- Interface for SPS -----------------------------------------------------------------------

    def get_resources_for_test_type(self) -> dict:
        d = self._CONFIG
        return d[self.test_type]

    # --- TestStand Interfaces --------------------------------------------------------------------


    def get_resource_strings_for_socket(self, socket: int | str) -> tuple:
        # return the selected socket configuration in a convenient way for teststand
        socket = int(socket)
        if socket == -1: socket = 0  # -1 is the SingleSequential setting
        d = self._CONFIG
        _test_type = d["test_type"]
        _ns = len(d[_test_type]["test_sockets"])
        assert (socket >= 0 and socket < _ns), ValueError(f"Socket must be in [0..{_ns}].")
        r = OrderedDict(self._CONFIG[_test_type]["test_sockets"][str(socket)]["resource_strings"])
        # here we could change the network tuples
        # of the YAML resources by replacement
        #nw_correction = ".".join(d["line_network"].split(".")[:3])  # only the first three IP numbers
        # need a regex here ... todo
        #return tuple([v.replace(xyz, nw_correction) for k,v in r.items()])
        return tuple([v for k,v in r.items()])


    def get_i2c_mux_configuration(self) -> tuple:
        # return the i2c mux configuration, if any
        d = self._CONFIG
        _test_type = d["test_type"]
        print(d[_test_type], hasattr(d[_test_type], "i2c_mux"))
        if "i2c_mux" not in d[_test_type]:
            raise AttributeError(f"Station for {_test_type } has no I2C mux configuration set.")
        mux = d[_test_type]["i2c_mux"]
        if "num_bus" not in mux:
            raise AttributeError(f"Missing 'i2c_mux.num_bus' attribute.")
        if "device_to_bus_map" not in mux:
            raise AttributeError(f"Missing 'i2c_mux.device_to_bus_map' attribute.")
        result = mux["num_bus"], tuple([v for k,v in mux["device_to_bus_map"].items()])
        return result


    def get_station_configuration(self) -> tuple:
        # return the station's configuration in a convenient way for teststand
        d = self._CONFIG
        _test_type = d["test_type"]
        _ns = len(d[_test_type]["test_sockets"])
        if "dsp_api_base_url" in d:
            _api_base_url = d["dsp_api_base_url"]  # one global base url
        else:
            _api_base_url = d[_test_type]["dsp_api_base_url"]  # allows for test specific base urls
        if "station_id" not in d:
            _station_id = self._hostname  # we are using the hostname
        else:
            _station_id = d["station_id"]
        _api_base_url
        result = (
            _test_type,             # str
            _station_id,            # str
            _api_base_url,          # str
            self._line_id,          # int, replace by auto-detection
            _ns                     # int
        )
        return result

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = StationConfiguration("PCBA_TEST", filename=CONF_FILENAME_DEV)
    #pprint(cfg._CONFIG)
    pprint(cfg.get_station_configuration())
    pprint(cfg.get_resource_strings_for_socket(0))
    pprint(cfg.get_i2c_mux_configuration())
    print(cfg._primary_ip, cfg._hostname, cfg._own_network, cfg._line_id)
# END OF FILE