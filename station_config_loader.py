import yaml
from pathlib import Path
from pprint import pprint

class StationConfiguration:

    def __init__(self) -> None:
        self._CONFIG = None
        #_filename = Path(".") / "station_config_example.yaml"  # development
        _filename = Path("C:/") / "Production" / "station_config.yaml"  # production
        self._read_yaml_file(_filename)

    def _read_yaml_file(self, filepath: str | Path) -> dict:
        with open(Path(filepath), "rt") as file:
            self._CONFIG = yaml.safe_load(file)

    # --- TestStand Interfaces --------------------------------------------------------------------

    def get_resource_strings_for_socket(self, socket: int | str) -> tuple:
        # return the selected socket configuration in a convenient way for teststand
        socket = int(socket)
        if socket == -1: socket = 1  # -1 is the SingleSequential setting
        d = self._CONFIG
        _ns = len(d["test_sockets"])
        assert (socket > 0 and socket <= _ns), ValueError(f"Socket must be in [1..{_ns}].")
        r = dict(self._CONFIG["test_sockets"][str(socket)]["resource_strings"])
        return tuple([v for k,v in r.items()])
        
    def get_station_configuration(self) -> tuple:
        # return the station's configuration in a convenient way for teststand       
        d = self._CONFIG
        _ns = len(d["test_sockets"])
        result = (
            d["test_type"], 
            d["station_id"], 
            d["line_id"], 
            _ns,
            d["dsp_api_base_url"],
            #tuple([self.get_resource_strings_for_socket(s+1) for s in range(_ns)]),
        )
        return result

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = StationConfiguration()
    #pprint(cfg._CONFIG)
    pprint(cfg.get_station_configuration())
    #pprint(cfg.get_resource_strings_for_socket(2))


# END OF FILE