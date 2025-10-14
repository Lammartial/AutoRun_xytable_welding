
import yaml
import json
import socket
from pathlib import Path
from pprint import pprint
from collections import OrderedDict


CONF_FILENAME_DEV = Path(__file__).parent / "station_config_development.yaml"  # development
CONF_FILENAME_PROD = Path("C:/") / "Production" / "station_config.yaml"        # production


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
            #
            # do some mods after reading which makes debugging much easier
            #
            if "line_id" in self._CONFIG and int(self._CONFIG["line_id"]) < 1:
                # included 0 and -1 to trigger calculation by own IP address
                # -> calculate from IP octet #3
                if int(self._own_network[2]) > 100:
                    self._line_id = abs(self._own_network[2] - 100)
                else:
                    self._line_id = 0  # UNKNOWN
            else:
                # use line ID as given in YAML -> used in DEBUG with TSDEV to assign a Production Line
                self._line_id = int(self._CONFIG["line_id"])

            if "TSDEV" in self._hostname:
                # TS development PC -> calculate target network line
                _nw =[
                    self._own_network[0],
                    self._own_network[1],
                    (100 + self._line_id) if self._line_id < 10 else self._line_id,
                    0
                ]
                _net_replace = ".".join((str(c) for c in _nw[:3])) + "."
            else:
                _net_replace = ".".join((str(c) for c in self._own_network[:3])) + "."

            match self._own_network[1]:
                case 71 | 168:
                    # RRC Germany
                    pass
                case 75:
                    # RRC VN
                    pass

            # if line_network is defined it is used to replace the first three octets
            # by the own IPs first three octets. This allows decoupling YAML from line
            if "line_network" in self._CONFIG:
                # do a text replacement loop
                _sub = self._CONFIG["line_network"]
                _txt = json.dumps(self._CONFIG).replace(_sub, _net_replace)
                self._CONFIG = OrderedDict(json.loads(_txt))




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
            # new: add offset of 10 to the port for each production line > 1
            _ar = _api_base_url.split(":")
            try:
                _new_port = int(_ar[-1]) + (self._line_id-1) * 10
                _ar[-1] = str(_new_port)  # set port with offset based on line no
                _api_base_url = ":".join(_ar)
                # do NOT modify the base content!
            except ValueError:
                pass  # do not change the api base url

        if "station_id" not in d:
            _station_id = self._hostname  # we are using the hostname
        else:
            _station_id = d["station_id"]
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
    print("Primary IP :", cfg._primary_ip)
    print("Hostname   :", cfg._hostname)
    print("Own Network:", cfg._own_network)
    print("Line-ID    :", cfg._line_id)
# END OF FILE