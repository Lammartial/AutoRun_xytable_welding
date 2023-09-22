#
# Modul containing queries and modification functions to extract Teststand test results
# from our new Teststand layout (>TS 2019, teststand) as well as from our old ones
# (<=TS 4.0, trackR2)
#
from typing import Tuple, List
from time import perf_counter
from datetime import datetime, timedelta, date
from pathlib import Path
import re
import pandas as pd
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker


#--------------------------------------------------------------------------------------------------

def query_main_sequence_filepaths(engine: sa.Engine, seqfile_pattern: str, show_performance: bool = False) -> pd.DataFrame | None:
    sql = sa.text(f"""SELECT
	    distinct(xsq.SEQUENCE_FILE_PATH)
    FROM (
        (SELECT ts,ID,STEP_RESULT,SEQUENCE_FILE_PATH FROM step_seqcall WHERE (SEQUENCE_FILE_PATH like '{seqfile_pattern}')) as xsq
        LEFT JOIN (SELECT ts,ID,UUT_RESULT FROM step_result) xsr ON (xsq.STEP_RESULT = xsr.ID)
        LEFT JOIN (SELECT ts,ID,UUT_SERIAL_NUMBER,PART_NUMBER,UUT_STATUS,UUT_ERROR_MESSAGE,START_DATE_TIME FROM uut_result) xur ON (xsr.UUT_RESULT = xur.ID)
    )""")
    #print(sql)
    with engine.connect() as session:
        if show_performance:
            tic = perf_counter()
        df = pd.read_sql(sql, session)
        if show_performance:
            toc = perf_counter()
            print(f"Fetched {len(df)} datasets.")
            print(f"Need {toc - tic:0.4f} seconds")
    return df


#--------------------------------------------------------------------------------------------------


def query_measurements(engine: sa.Engine, start_ts: datetime, end_ts: datetime, use_start_date_time: bool = False,
                       part_number: str = None, seqfile_pattern: str = None,
                       limit: int = None, show_performance: bool = False) -> pd.DataFrame | None:
    """Queries a series of tests, restricted by time span, part number and a sequence filename pattern.

    Distinguieshes between new teststand and old trackR2 layout of database, based on "trackr2" pattern
    found in engine connection string.

    Args:
        engine (sa.Engine): _description_
        start_ts (datetime): _description_
        end_ts (datetime): _description_
        use_start_date_time (bool, optional): _description_. Defaults to False.
        part_number (str, optional): _description_. Defaults to None.
        seqfile_pattern (str, optional): _description_. Defaults to None.
        limit (int, optional): _description_. Defaults to None.
        show_performance (bool, optional): _description_. Defaults to False.

    Returns:
        pd.DataFrame: _description_
    """
    _limit_pattern = f"LIMIT {limit}" if limit else ""
    #_seqfile_pattern = f"AND sq.SEQUENCE_FILE_PATH LIKE '{seqfile_pattern}'" if seqfile_pattern else ""
    _seqfile_pattern = f"AND SEQUENCE_FILE_PATH LIKE '{seqfile_pattern}'" if seqfile_pattern else ""
    _join_start_ts = (datetime.combine(start_ts, datetime.min.time()) - timedelta(hours=1)).isoformat()
    _join_end_ts = (datetime.combine(end_ts, datetime.min.time()) + timedelta(hours=1)).isoformat()
    _pn_pattern = f"AND ur.PART_NUMBER='{part_number}'" if part_number else ""
    _dt_pattern = f"ur.START_DATE_TIME >= '{start_ts}' AND ur.START_DATE_TIME < '{end_ts}'" if use_start_date_time else f" ur.ts >= '{start_ts}' AND ur.ts < '{end_ts}'"
    _order_pattern = f"ORDER BY ur.START_DATE_TIME" if use_start_date_time else "ORDER BY ur.ts"
    if "trackr2" in str(engine).lower():
        # --- old teststand layout ---
        _from_pattern = f"""(av_uut_result AS ur
            JOIN (
                (SELECT * FROM av_step_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) AS sr
                    LEFT JOIN (SELECT * FROM av_step_passfail WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) AS sp ON sr.ID = sp.STEP_RESULT
                    LEFT JOIN (SELECT * FROM av_step_seqcall WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) AS sq ON sr.STEP_PARENT = sq.STEP_RESULT
                    LEFT JOIN (SELECT * FROM av_meas_numericlimit WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) AS mn ON sr.ID = mn.STEP_RESULT
            ) ON (ur.ID = sr.UUT_RESULT)) """
        # old trackR2 layout
        # (has no STEP_ID)
        sql = sa.text(f"""
            SELECT
                sr.ts AS ts,
                ur.SequenceFilename AS SEQUENCE_FILENAME,
                ur.PART_NUMBER AS PART_NUMBER,
                ur.UUT_SERIAL_NUMBER AS UUT_SERIAL_NUMBER,
                ur.UUT_STATUS AS UUT_STATUS,
                ur.UUT_ERROR_MESSAGE AS UUT_ERROR_MESSAGE,
                ur.START_DATE_TIME AS START_DATE_TIME,
                sr.ORDER_NUMBER AS STEP_ORDER,
                sr.STEP_INDEX AS STEP_INDEX,
                sr.STEP_NAME AS STEP_NAME,
                sr.STATUS AS STEP_STATUS,
                sr.STEP_TYPE AS PROPERTY_TYPE,
                mn.NAME AS PROPERTY_PATH,
                mn.STATUS AS MEAS_STATUS,
                mn.DATA AS INTRINSIC_VALUE,
                mn.UNITS AS UNITS,
                mn.LOW_LIMIT AS LOW_LIMIT,
                mn.HIGH_LIMIT AS HIGH_LIMIT,
                sq.SEQUENCE_NAME AS PARENT_SEQUENCE_NAME,
                sq.SEQUENCE_FILE_PATH AS PARENT_SEQUENCE_FILE_PATH
            FROM
                {_from_pattern}
            WHERE
                {_dt_pattern}
                {_seqfile_pattern}
                {_pn_pattern}
            {_limit_pattern}
        """)
    else:
        # --- new teststand layout ---
        # extract ONLY numeric measurements
        # _from_pattern = f"""(uut_result ur
        #             JOIN (((SELECT * FROM step_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) sr
        #                 LEFT JOIN ((SELECT * FROM prop_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) pr
        #                     LEFT JOIN (SELECT * FROM prop_numericlimit  WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) pnl
        #                     ON (pr.ID = pnl.PROP_RESULT))
        #                 ON (sr.ID = pr.STEP_RESULT))
        #                 LEFT JOIN (SELECT * FROM step_seqcall WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) sq
        #                 ON (sr.STEP_PARENT = sq.STEP_RESULT))
        #         ON (ur.ID = sr.UUT_RESULT)) """

        # first part of the select generates a list of distinct devices (by serial their serial number)
        # this is (outer) joined with the comination of numeric measurement steps and their data up
        # to the UUT_RESULT table
        _from_pattern = f"""(SELECT DISTINCT
            xur.UUT_SERIAL_NUMBER,
            xur.PART_NUMBER,
            xur.UUT_STATUS,
            xur.UUT_ERROR_MESSAGE,
            xur.START_DATE_TIME,
            xur.ID,
            xur.ts,
            xsq.SEQUENCE_FILE_PATH as SPECIFIC_SEQUENCE_FILE_PATH
        FROM
            (SELECT ts,STEP_RESULT,SEQUENCE_FILE_PATH,ID
             FROM step_seqcall WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}') {_seqfile_pattern}) as xsq
            LEFT JOIN (SELECT ts,UUT_RESULT,ID
                       FROM step_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) xsr ON (xsq.STEP_RESULT = xsr.ID)
            LEFT JOIN (SELECT ts,UUT_SERIAL_NUMBER,PART_NUMBER,UUT_STATUS,UUT_ERROR_MESSAGE,START_DATE_TIME,ID
                       FROM uut_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) xur ON (xsr.UUT_RESULT = xur.ID)
        ) ur
        JOIN ((SELECT * FROM prop_numericlimit  WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) pnl
            LEFT JOIN (SELECT * FROM prop_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) pr ON (pr.ID = pnl.PROP_RESULT)
            LEFT JOIN (SELECT * FROM step_result WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) sr ON (sr.ID = pr.STEP_RESULT)
            LEFT JOIN (SELECT * FROM step_seqcall WHERE (ts >= '{_join_start_ts}') AND (ts < '{_join_end_ts}')) sq ON (sr.STEP_PARENT = sq.STEP_RESULT)
        ) ON (ur.ID = sr.UUT_RESULT)"""

        _pn_pattern = ""

        sql = sa.text(f"""
            SELECT
                ur.ts AS ts,
                ur.ID AS TEST_ID,
                ur.PART_NUMBER AS PART_NUMBER,
                ur.UUT_SERIAL_NUMBER AS UUT_SERIAL_NUMBER,
                ur.UUT_STATUS AS UUT_STATUS,
                ur.UUT_ERROR_MESSAGE AS UUT_ERROR_MESSAGE,
                ur.START_DATE_TIME AS START_DATE_TIME,
                CONCAT(sq.SEQUENCE_NAME, ".", sr.STEP_INDEX, ".", pr.ORDER_NUMBER) AS STEP_ORDER,
                sr.ORDER_NUMBER AS STEP_ORDER_NUMBER,
                sr.STEP_ID AS STEP_ID,
                sr.STEP_INDEX AS STEP_INDEX,
                sr.STEP_NAME AS STEP_NAME,
                sr.STATUS AS STEP_STATUS,
                pr.ORDER_NUMBER AS PROPERTY_ORDER_NUMBER,
                pr.PATH AS PROPERTY_PATH,
                pr.TYPE_NAME AS PROPERTY_TYPE,
                pr.DATA AS INTRINSIC_VALUE,
                pnl.UNITS AS UNITS,
                pnl.LOW_LIMIT AS LOW_LIMIT,
                pnl.HIGH_LIMIT AS HIGH_LIMIT,
                sq.SEQUENCE_NAME AS PARENT_SEQUENCE_NAME,
                sq.SEQUENCE_FILE_PATH AS PARENT_SEQUENCE_FILE_PATH,
                ur.SPECIFIC_SEQUENCE_FILE_PATH AS SPECIFIC_SEQUENCE_FILE_PATH
            FROM
                {_from_pattern}
            WHERE
                {_dt_pattern}
                {_pn_pattern}
            {_order_pattern}
            {_limit_pattern}
        """)
    print(sql)
    with engine.connect() as session:
        if show_performance:
            tic = perf_counter()
        df = pd.read_sql(sql, session)
        if show_performance:
            toc = perf_counter()
            print(f"Fetched {len(df)} datasets.")
            print(f"Need {toc - tic:0.4f} seconds")
    return df


#--------------------------------------------------------------------------------------------------


def query_uut_results(engine: sa.Engine, limit: int = 1000) -> pd.DataFrame | None:
    with engine.connect() as session:
        sql=sa.text(
                    f"SELECT * FROM view_step_results_all_measurements AS ur "+\
                    f"  ORDER BY ur.ts DESC"+\
                    f"  LIMIT {limit}"
            )
        df = pd.read_sql(sql, session)
    return df


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
   #
   # tests are moved out to tests/test_db_queries.py
   #
   pass

# END OF FILE