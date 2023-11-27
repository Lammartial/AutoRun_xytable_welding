#
# Modul containing queries and modification functions to extract welding measurements and
# results from our protocol database.
#
from typing import Tuple, List
from time import perf_counter
from datetime import datetime, timedelta, date
from pathlib import Path
import re
import json
import pandas as pd
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker


#def get_welding_measurements(start_date: datetime | str = None, end_date: datetime | str = None, limit: int = 1000) -> pd.DataFrame:
def query_welding_measurements(engine: sa.Engine, start_ts: datetime, end_ts: datetime,
                       part_number: str = None,
                       limit: int = None, show_performance: bool = False) -> pd.DataFrame | None:

    _limit_pattern = f"LIMIT {limit}" if limit else ""
    _dt_pattern = f" m.ts BETWEEN '{start_ts}' AND '{end_ts}'"

    with engine.connect() as session:
        sql=sa.text(f"""SELECT
                m.ts,
                m.udi,
                m.counter,
                m.position,
                m.part_number,
                m.line_id,
                m.station_id,
                m.`result`,
                p.device_name,
                p.program_no,
                m.measurements as measurements_json,
                p.parameters as parameters_json,
                w.waveforms as waveforms_json
            FROM protocol.welding_measurements AS m
            LEFT JOIN protocol.welding_parameters AS p ON (m.ref_parameter = p.hash)
            LEFT JOIN protocol.welding_waveforms AS w ON (m.udi = w.udi and m.counter = w.counter)
            WHERE {_dt_pattern}
            ORDER BY m.udi, m.position ASC
            {_limit_pattern}
        """)
        if show_performance:
            tic = perf_counter()
        print(sql)
        df = pd.read_sql(sql, session)
        #df = pd.read_sql_table("welding_measurements", session, "protocol")
        print(f"Read {len(df)} data records.", end="")
        if show_performance:
            toc = perf_counter()
            print(f"Need {toc - tic:0.4f} seconds")
        else:
            print()  # add only linefeed

        if len(df) == 0:
            return df  # empty data frame
        return df
        print("Normalize records...")
        lst_meas = [
            pd.json_normalize({
                **row[:-3],  # measurements was the 3rd last in row (see SQL above)
                **json.loads(row["measurements_json"]),
                **json.loads(row["parameters_json"])
            })
            for index, row in df.iterrows()
        ]
        print(f"Combine into new DataFrame() ...")
        full_df = pd.concat(lst_meas, axis="index")
        return full_df


def normalize_json_records(records_df: pd.DataFrame, show_performance: bool = False,
                           normalize_measurements: bool = True,
                           normalize_parameters: bool = True,
                           generate_extra_waveform_df: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Note: the Waveforms need to be extracted into a separate data
    #       frame to hanlde them as they would blow up the standard
    #       frame too much. Also they are provided only for failed weldings.

    print("Normalize records...", end="")
    if show_performance:
        tic = perf_counter()
    lst_meas = [
        pd.json_normalize({
            **row[:-3],  # measurements was the 3rd last in row (see SQL above)
            **(json.loads(row["measurements_json"]) if normalize_measurements else {}),
            **(json.loads(row["parameters_json"]) if normalize_parameters else {})
        })
        for index, row in records_df.loc[
            (((~records_df["measurements_json"].isnull()) & (records_df["measurements_json"] != "null"))
                if normalize_measurements else ())
            &
            ((~records_df["parameters_json"].isnull()) if normalize_parameters else ())
        ].iterrows()
    ]
    if show_performance:
        toc = perf_counter()
        print(f"Need {toc - tic:0.4f} seconds")
    else:
        print()  # add only linefeed
    print(f"Combine into full data frame...", end="")
    if show_performance:
        tic = perf_counter()
    full_df = pd.concat(lst_meas, axis="index")
    if show_performance:
        toc = perf_counter()
        print(f"Need {toc - tic:0.4f} seconds")
    else:
        print()  # add only linefeed
    if generate_extra_waveform_df:
        print("Generate 2nd data frame for waveform records")
        waveform_df = pd.DataFrame()
    else:
        waveform_df = None
    return full_df, waveform_df


    #--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   #
   # tests are moved out to tests/test_db_queries.py
   #
   pass

# END OF FILE