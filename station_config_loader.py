import yaml
from pathlib import Path
from pprint import pprint
from collections import OrderedDict


CONF_FILENAME_DEV = Path(".") / "station_config_example.yaml"  # development
CONF_FILENAME_PROD = Path("C:/") / "Production" / "station_config.yaml"  # production


#--------------------------------------------------------------------------------------------------

class StationConfiguration:

    def __init__(self, test_type: str, filename: str | Path = CONF_FILENAME_PROD) -> None:
        self._CONFIG = None
        self.test_type = test_type
        self._filename = Path(filename)
        self._read_yaml_file(self._filename)

    def __str__(self) -> str:
        return f"Test station configuration by YAML file {self._filename}"

    def __repr__(self) -> str:
        return f"StationConfiguration(filename={self._filename})"

    #----------------------------------------------------------------------------------------------

    def _read_yaml_file(self, filepath: str | Path) -> OrderedDict:
        with open(Path(filepath), "rt") as file:
            self._CONFIG = OrderedDict(yaml.safe_load(file))
            # here we could check the YAML file setting of test_type
            self._CONFIG["test_type"] = self.test_type

    # --- TestStand Interfaces --------------------------------------------------------------------


    def get_resource_strings_for_socket(self, socket: int | str) -> tuple:
        # return the selected socket configuration in a convenient way for teststand
        socket = int(socket)
        if socket == -1: socket = 1  # -1 is the SingleSequential setting
        d = self._CONFIG
        _test_type = d["test_type"]
        _ns = len(d[_test_type]["test_sockets"])
        assert (socket > 0 and socket <= _ns), ValueError(f"Socket must be in [1..{_ns}].")
        r = OrderedDict(self._CONFIG[_test_type]["test_sockets"][str(socket)]["resource_strings"])
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
        result = (
            d["test_type"],         # str
            d["station_id"],        # str
            d["dsp_api_base_url"],  # str
            d["line_id"],           # int
            _ns                     # int
        )
        return result

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = StationConfiguration(CONF_FILENAME_PROD)
    #pprint(cfg._CONFIG)
    pprint(cfg.get_station_configuration())
    pprint(cfg.get_resource_strings_for_socket(1))
    pprint(cfg.get_i2c_mux_configuration())


# END OF FILE