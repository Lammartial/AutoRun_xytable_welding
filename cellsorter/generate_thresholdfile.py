from re import I
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter
from datetime import timezone, datetime
import pyodbc
import pandas as pd
import numpy as np


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init

logger_init(filename_base=None)
_log = getLogger(__name__, DEBUG)

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #


ACCESSDB_FILEPATH = Path("C:/Projekte/Cellsorter/MG1T.accdb")
ACCESSDB_FILEPATH_DEVELOPMENT = Path("C:/Projekte/V-Kong/Teststand-Deployment/Python_Libs/rrc/sampledata/MG1T.accdb")

DB_COLUMN_NAMES = ["Cellsn", "Bin_Number", "Ir", "Ocv", "TestTime", "Batchid", "TestResult"]


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

#
# You need to install the 64bit ODBC Microsoft Access Driver 2016
# Download the file from Microsoft as "AccessDatabaseEngine_x64".
#
# How to install 64-bit Microsoft Access database engine alongside 32-bit Microsoft Office?
# it may throw an error that alongside the 32bit version its not possible to install.
# Then:
#   run "AccessDatabaseEngine_x64.exe /quiet"
#
# then with regedit as admin,
#
#   delete or rename the mso.dll registry value in the following registry key:
#     HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\14.0\Common\FilesPaths
#     HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\16.0\Common\FilesPaths
#
# (from https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-64-bit-Microsoft-Database-Drivers-alongside-32-bit-Microsoft-Office.html)
#

def read_from_access_databasefile(fp : Path, selected_table: int | str = -1) -> pd.DataFrame:
    global DEBUG, DB_COLUMN_NAMES

    pyodbc.lowercase = False
    with pyodbc.connect(
        "Driver={Microsoft Access Driver (*.mdb, *.accdb)};" +
        f"Dbq={fp.absolute()};") as conn:
        with conn.cursor() as cur:
            tables = [i.table_name for i in cur.tables(tableType="Table")]
            print("Tables found:", tables)
            if isinstance(selected_table, str):
                _idx = tables.index(selected_table)
            else:
                _idx = selected_table
            print(f"Using table: '{tables[_idx]}'")
            cols = DB_COLUMN_NAMES
            cur.execute(f"SELECT {','.join(cols)} FROM {tables[_idx]}");
            data = cur.fetchall()

    df = pd.DataFrame.from_records(data, columns=cols)
    #df.replace(-10000.0, np.nan, inplace=True)
    df = df.astype({"Bin_Number": "int64", "Ir": "float64", "Ocv": "float64",})
    df = df.loc[~((df["Ir"] == -10000) | (df["Ocv"] == -10000))]
    print(f"Found {len(df)} valid records.")
    return df


#--------------------------------------------------------------------------------------------------


def do_the_bango(df :pd.DataFrame, center: str, buckets_ocv: str, buckets_ir: str) -> list:

    print("Bin numbers used:", sorted(df["Bin_Number"].unique()))
    range_ocv = df["Ocv"].max() - df["Ocv"].min()
    avg_ocv = df["Ocv"].mean()
    median_ocv = df["Ocv"].median()
    mode_ocv = df["Ocv"].mode()
    std_ocv = df["Ocv"].std()
    print(f"Ocv: Range={range_ocv}, Std={std_ocv}, Mean={avg_ocv}, Median={median_ocv}, Mode={mode_ocv.to_list()}")
    range_ir = df["Ir"].max() - df["Ir"].min()
    avg_ir = df["Ir"].mean()
    median_ir = df["Ir"].median()
    mode_ir = df["Ir"].mode()
    std_ir = df["Ir"].std()
    print(f"Ir: Range={range_ir}, Std={std_ir}, Mean={avg_ir}, Median={median_ir}, Mode={mode_ir.to_list()}")
    if "median" in center:
        center_ocv = median_ocv
        center_ir = median_ir
    elif "mode" in center:
        center_ocv = mode_ocv[0]
        center_ir = mode_ir[0]
    else:
        # valid for "mean, average, range, etc."
        center_ocv = avg_ocv
        center_ir = avg_ir
    print(f"Selected center type: {center} => Ocv={center_ocv}V, Ir={center_ir}mOhm")

    # parse the ranges given by the user
    print(f"Buckets Ocv: {buckets_ocv}")
    if "s" in buckets_ocv:
        # sigma thresholds,
        _br = [center_ocv + int(n)*std_ocv for n in buckets_ocv.replace("s","").split(",")]
        #print(_br)
        pass
    else:
        # thresholds as mV values with sign
        _br = [center_ocv + float(n) for n in buckets_ocv.split(",")]
        #print(_br)
        pass
    if (len(_br) % 2) != 0:
        raise ValueError(f"Need even length list, but has {len(_br)}")
    _s = int(len(_br)/2)
    sort_ocv = _br[:_s] + [center_ocv] + _br[_s:]
    print(f"Thresholds Ocv(V): {sort_ocv}")

    # make ranges for Ocv
    print("Created Ocv ranges:")
    ocv_ranges = []
    for previous, current in zip(sort_ocv, sort_ocv[1:]):
        ocv_ranges.append((previous, current))
        print(f"[{previous}..{current}]")

    print(f"Buckets Ir: {buckets_ir}")
    if "s" in buckets_ir:
        # sigma thresholds,
        _br = [center_ir + int(n)*std_ir for n in buckets_ir.replace("s","").split(",")]
        #print(_br)
        pass
    else:
        # thresholds as mV values with sign
        _br = [center_ir + float(n) for n in buckets_ir.split(",")]
        #print(_br)
        pass
    if (len(_br) % 2) != 0:
        raise ValueError(f"Need even length list, but has {len(_br)}")
    _s = int(len(_br)/2)
    sort_ir = _br[:_s] + [center_ir] + _br[_s:]
    print(f"Thresholds Ir(mOhm): {sort_ir}")

    # make ranges for Ir
    print("Created Ir ranges:")
    ir_ranges = []
    for previous, current in zip(sort_ir, sort_ir[1:]):
        ir_ranges.append((previous, current))
        print(f"[{previous}..{current}]")

    # create a 2d array in numpy
    #slots = list(zip(ir_ranges, ocv_ranges))
    #slots = list(filter(lambda i: i is not None, chain.from_iterable(zip(ocv_ranges, ir_ranges))))
    slots = []
    for n in ocv_ranges:
        for m in ir_ranges:
            slots.append((n,m))
    if len(slots) > 10:
        raise ValueError(f"Buckts array may have up to 10 elements but has {len(slots)}")
    return slots


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # need to initialize logger on load

    print("=== Cellsorter Bucket Generator ===")

    _default_accessdb = ACCESSDB_FILEPATH_DEVELOPMENT if ACCESSDB_FILEPATH_DEVELOPMENT.exists() else ACCESSDB_FILEPATH

    parser = ArgumentParser(description="""
        The Cellsorter Bucket Generator creates a set of range buckets for Ocv and Ir sorting of
        cells based on a given input data set and a method to generate.
        The Ocv and Ir are forming a 2D array which has to have less than or up to 10 elements,
        as the cellsorter has a maximum of 10 bucket ranges available only.

        In the default setup this tool takes the last table from the default access database file
        and creates a set of 4x Ocv and 2x Ix ranges, resulting in use of 8 buckets altogether.
        """,
        formatter_class=RawDescriptionHelpFormatter,
        #formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("center", choices=["mean", "median", "modus"], help="The way to select the center value of the sample set read from DB.")
    parser.add_argument("--filepath", action="store", default=_default_accessdb.absolute(), help="Path and filename prefix for Access DB file.")
    parser.add_argument("--table", default=-1, help="Index (0=first, -1=last) or name of table to read data from.")
    #parser.add_argument("--center", choices=["mean","median", "modus"], default="median", help="The way to select the center value of the sample set read from DB.")
    parser.add_argument("--buckets_ocv", default="-4s,-2s,2s,4s", help="Comma separated list of buckets for the ranges of Ocv either as sigma, if 's' is appended, or as value steps in volts (not millivolts!).")
    parser.add_argument("--buckets_ir", default="-2s,2s", help="Comma separated list of buckets for the ranges of Ir either as sigma, if 's' is appended, or as value steps in ohms (not milliohms!).")
    args = parser.parse_args()

    df = read_from_access_databasefile(args.filepath, args.table)
    #print(df)
    #print(df.describe())
    slots = do_the_bango(df, args.center, args.buckets_ocv, args.buckets_ir)
    print("\n\n", len(slots), slots)

    print("\nDONE.")

# END OF FILE