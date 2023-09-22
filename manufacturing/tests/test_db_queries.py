from typing import Tuple, List, Callable
from time import perf_counter
from datetime import datetime, timedelta, date
from pathlib import Path
import re
import pandas as pd
import numpy as np
import json
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker as SessionMaker

from IPython.display import display, clear_output, Image, Markdown
from ipywidgets import widgets, interactive, jslink, link, Layout, Accordion, Text, HBox, VBox

# our libs
import rrc.manufacturing.db as mndb
from rrc.manufacturing.db.query_teststand import query_measurements, query_uut_results
from rrc.manufacturing.toolbox import find_measurement_steps, generate_steps_selection_list, \
        get_datarows_strings, generate_selection_accordion, get_datarows_based_on_selection, \
        get_datarows_strings, cpk_preparation, split_df_pass_fail, abbreviate_sheetname

#--------------------------------------------------------------------------------------------------


tsdb_engine : Engine = None
tsdb_session_maker: SessionMaker = None
tr2db_engine : Engine = None
tr2db_session_maker: SessionMaker = None


#--------------------------------------------------------------------------------------------------


def process_measurements(meas_df: pd.DataFrame, title: str):
     #print("EMI:  \n",_df_EMI.loc[~_df_EMI["INTRINSIC_VALUE"].isnull()].T)
    print(title, ":", len(meas_df))

    _steps_df = find_measurement_steps(meas_df)
    print(_steps_df.T)
    #_steps_df.info(show_counts=True)
    print(get_datarows_strings(_steps_df))
    names_list, _steps_df = generate_steps_selection_list(_steps_df)
    print(_steps_df.T)
    for name in names_list:
        _abbrev = abbreviate_sheetname(name[1:])
        if name[0][-1] == "0":
            _exname = f'{_abbrev:.32}'
        else:
            # need to add the property index
            _exname = f'{_abbrev:.30}#{name[0][-1]}'
        print(name, _exname)

    acc, checkboxes = generate_selection_accordion(names_list, None)

    # check some
    checkboxes[2].value = True
    checkboxes[4].value = True

    # query again for full dataset
    #full_meas_df = query_measurements(tr2db_engine, date.fromisoformat("2022-09-20"), date.fromisoformat("2022-09-23"),
    #        seqfile_pattern="%411826-02_A.seq", part_number="411826-02")
    #_lst = get_datarows_based_on_selection(checkboxes, names_list, full_meas_df)
    _lst = get_datarows_based_on_selection(checkboxes, names_list, meas_df)
    print(len(_lst))
    print(_lst)

#--------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    tsdb_engine, tsdb_session_maker = mndb.create_connection_teststand(server_host="172.22.2.42")   # RRC DE
    #tsdb_engine_vn, tsdb_session_maker = mndb.create_connection_teststand(server_host="172.25.100.42")   # RRC VN
    #tr2db_engine, tr2db_session_maker = mndb.create_connection_trackr2(server_host="172.23.129.1")  # EMI/CN

    _df_DE = query_measurements(tsdb_engine, date.fromisoformat("2023-06-01"), date.fromisoformat("2023-07-01"),
                seqfile_pattern="%_Leanpack-Test%", part_number="110282S-02", limit=5000)

    #heinz = _df_DE.loc[~_df_DE["PROPERTY_PATH"].isnull() & _df_DE["PROPERTY_PATH"].str.contains("Measurement.[", regex=False)]
    #print(heinz[["INTRINSIC_VALUE", "STEP_ORDER", "UUT_SERIAL_NUMBER"]].head(10))
    process_measurements(_df_DE, "DE")


    #_df_EMI = query_measurements(tr2db_engine, date.fromisoformat("2022-09-20"), date.fromisoformat("2022-09-23"),
    #            seqfile_pattern="%411826-02_A.seq", part_number="411826-02", limit=None)

    #process_measurements(_df_EMI, "EMI")

# END OF FILE