from typing import List, Tuple
from enum import Enum
import json
import yaml
from hashlib import md5
from base64 import b64decode, b64encode
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import timezone, datetime
import pandas as pd


from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV
# import SQL managing modules
from sqlalchemy import text
from sqlalchemy.orm import Session
from rrc.dbcon import get_protocol_db_connector

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

def read_results_x(filepath: Path):
    engine, session_maker = get_protocol_db_connector()
    with session_maker() as session:
        response = session.execute(text(
                f"SELECT wm.udi,wm.position,wm.result,wm.counter,wm.measurements FROM `welding_measurements` AS wm "+\
                f"  ORDER BY wm.udi,wm.position ASC"+\
                f"  LIMIT 100"
                ))
        rows = response.fetchall()
    if len(rows) == 0:
        # not found! -> do not proceed
        raise Exception(f"No Data in Database found, cannot proceed!")
    print(f"Got records: {len(rows)}")
    print(rows)


def read_results(filepath: Path):
    engine, session_maker = get_protocol_db_connector()
    #with session_maker() as session:
    with engine.connect() as session:
        sql=text(
                f"SELECT wm.udi,wm.part_number,wm.position,wm.result,wm.counter,wm.ts,wm.measurements FROM `welding_measurements` AS wm "+\
                f"  ORDER BY wm.udi,wm.position ASC"+\
                f"  LIMIT 10000"
        )
        df = pd.read_sql(sql, session)
        #df = pd.read_sql_table("welding_measurements", session, "protocol")
    print(f"Read {len(df)} data records. Normalize records...")
    lst_meas = [
        pd.json_normalize({
            **row[:-1],  # measurements was the last in row (see SQL above)
            **json.loads(row["measurements"])
        })
        for index, row in df.iterrows()
    ]
    print(f"Combine into new DataFrame() ...")
    full_df = pd.concat(lst_meas, axis="index")
    print(f"Save EXCEL ...")
    full_df.to_excel(filepath / "export-welding-results.xlsx")
    print(f"Save CSV ...")
    full_df.to_csv(filepath / "export-welding-results.csv")


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # need to initialize logger on load

    print("=== ANALYZE WELDING_RESULTS ===")

    #_default_export_filepath_ = Path(__file__).parent / "../.." / "logs"
    _default_export_filepath_= Path(__file__).parent

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--filepath", action="store", default=_default_export_filepath_, help="Path and filename prefix for export .CSV and .XLSX files")

    args = parser.parse_args()

    read_results(args.filepath)

# END OF FILE