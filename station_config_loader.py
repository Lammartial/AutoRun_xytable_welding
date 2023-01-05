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
        pass

cfg = StationConfiguration()
pprint(cfg._CONFIG)

# END OF FILE