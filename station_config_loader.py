import yaml
from pathlib import Path
from pprint import pprint

class StationConfiguration:

    def __init__(self) -> None:
        self._CONFIG = None
        _filename = Path(".") / "station_config_example.yaml"
        self._read_yaml_file(_filename)

    def _read_yaml_file(self, filepath: str | Path) -> dict:
        with open(Path(filepath), "rt") as file:
            self._CONFIG = yaml.safe_load(file)

    # --- TestStand Interfaces --------------------------------------------------------------------

    def get_station_configuration(self) -> tuple:
        # return the station's configuration in a convenient way for teststand
        order = ["test_type", "station_id", "line_id"]
        result = tuple([(field, self._CONFIG[field]) for field in order])
        result += (("test_sockets", len(self._CONFIG["test_sockets"])),)
        #result = tuple([self._CONFIG[field] for field in order])
        return result

    def get_resource_strings_for_socket(self, socket: str) -> tuple:
        # return the selected socket configuration in a convenient way for teststand
        assert (socket > 0 and socket <= 3), ValueError("Socket must be in [1..3].")
        d = dict(self._CONFIG["test_sockets"][str(socket)]["resource_strings"])
        return tuple([(k, v) for k,v in d.items()])
        #return tuple([self._CONFIG[field] for field in order])

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = StationConfiguration()
    pprint(cfg._CONFIG)

    pprint(cfg.get_station_configuration())
    pprint(cfg.get_resource_strings_for_socket(2))


# END OF FILE