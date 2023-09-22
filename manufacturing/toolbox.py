from typing import Tuple, List, Callable
from time import perf_counter
from datetime import datetime, timedelta, date
from pathlib import Path
import re
import pandas as pd
import numpy as np
import json

# UI
from IPython.display import display, clear_output, Image, Markdown
from ipywidgets import widgets, interactive, jslink, link, Layout, Accordion, Text, HBox, VBox

# our libs
# ...


#--------------------------------------------------------------------------------------------------


def get_test_count_for_serial_number(full_dataset: pd.DataFrame) -> pd.DataFrame:
    """Caclulates pass/failed/terminated tests count by serial from the given dataset.
    It needs to have UUT_SERIAL_NUMBER, UUT_STATUS and TEST_ID which corresponds
    to the UUT_RESULT table's ID.

    Args:
        full_dataset (pd.DataFrame): _description_

    Returns:
        pd.DataFrame: Indes is UUT_SERIAL_NUMBER, columns are
    """

    def _count_tests(uut_status: str) -> pd.DataFrame:
        grp_df = full_dataset.loc[full_dataset["UUT_STATUS"] == uut_status].groupby('UUT_SERIAL_NUMBER').agg({'TEST_ID': ['nunique']}) #'TEST_ID': ['sum', 'count']})
        # to flatten the multi-level columns
        grp_df.columns = ["_".join(col).strip() for col in grp_df.columns.values]
        # set the index to the serial number for the merge later on
        return grp_df.reset_index(inplace=False).set_index("UUT_SERIAL_NUMBER", inplace=False)


    _df_passed = _count_tests("Passed").rename(columns={"TEST_ID_nunique": "tests_passed"}).convert_dtypes()  # .convert_dtypes() ensures that there is no need to convert int to float because of NaN fill!
    _df_failed = _count_tests("Failed").rename(columns={"TEST_ID_nunique": "tests_failed"}).convert_dtypes()
    _df_terminated = _count_tests("Terminated").rename(columns={"TEST_ID_nunique": "tests_terminated"}).convert_dtypes()
    # outer join all three data sets on serial number
    _df_merged = pd.concat([_df_passed, _df_failed, _df_terminated], axis="columns")
    df = _df_merged.fillna(0).sort_values("tests_passed", ascending=False)
    return df


#--------------------------------------------------------------------------------------------------


def find_measurement_steps(df: pd.DataFrame) -> pd.DataFrame:
    """Get one pass test for a random serial and use these information to present.

    Args:
        df (pd.DataFrame): _description_

    Raises:
        ValueError: _description_

    Returns:
        pd.DataFrame: Steps of one part (same UDI) which are not failed, terminated or skipped in step order.
    """

    _pn = df.loc[(df["UUT_STATUS"] == "Passed")]["PART_NUMBER"].unique()
    _sn = df.loc[(df["UUT_STATUS"] == "Passed")]["UUT_SERIAL_NUMBER"].unique()

    if len(_sn) == 0:
        raise ValueError("There is no 'Passed' test in this time frame which is needed to get the full test steps.")

    _xx = df.loc[(df["UUT_STATUS"] == "Passed") & (df["UUT_SERIAL_NUMBER"] == _sn[0])]
    #_xx = df.loc[(df["UUT_STATUS"] == "Passed") & (df["UUT_SERIAL_NUMBER"] == _sn[0])].groupby(by="STEP_ORDER").first()
    #print("???", len(_xx), _xx.head())
    _xx = df.loc[(df["UUT_STATUS"] == "Passed") & (df["UUT_SERIAL_NUMBER"] == _sn[0]) & (~df["INTRINSIC_VALUE"].isnull()) &
                 (df["STEP_STATUS"] != "Skipped") &
                 (df["STEP_STATUS"] != "Terminated") &
                 (df["STEP_STATUS"] != "Failed")    # besides "Passed" we are also using this field on certain tests for numbers of measurements
                ].groupby(by="STEP_ORDER").first()  # get first row of each group
    #print("???", len(_xx), _xx.head())
    #print(_xx.T)
    _zz = _xx
    for key in ["INTRINSIC_VALUE", "LOW_LIMIT", "HIGH_LIMIT"]:
        _zz[key] = pd.to_numeric(_xx[key], errors="coerce")

    # reduce the long pathname to just sequence filename with suffix
    _zz.loc[:,"PARENT_SEQUENCE_FILE_PATH"] = _zz["PARENT_SEQUENCE_FILE_PATH"].str.replace(r"(.*\\)(.*)", (lambda m: m.group(2)), regex=True)
    #print("\n\n\n",_zz.T)
    # get everything in step order that has a PATH which could then result in a measurement
    _res = _zz.loc[(_zz["PARENT_SEQUENCE_NAME"].notnull() | _zz["PROPERTY_PATH"].notnull())]
    return _res.sort_values("STEP_ORDER")


#--------------------------------------------------------------------------------------------------


def get_datarows_strings(df: pd.DataFrame) -> List[str]:
    """Generates a List of unique names for each Step.

    Args:
        df (pd.DataFrame): _description_

    Returns:
        List[str]: _description_
    """
    data_rows = []
    for index, row in df.iterrows():
        _name = f'{row["PARENT_SEQUENCE_NAME"]} | {row["STEP_NAME"]} | {row["PROPERTY_PATH"] if row["PROPERTY_PATH"] else row["PROPERTY_TYPE"]}'
        data_rows.append((_name, index))
    return data_rows


#--------------------------------------------------------------------------------------------------


def generate_steps_selection_list(df: pd.DataFrame) -> Tuple[List, pd.DataFrame]:
    """_summary_

    Args:
        df (pd.DataFrame): _description_

    Returns:
        Tuple[List, pd.DataFrame]: _description_
    """
    named_test_steps_list = []
    corrected_unit_column = []
    # sort the rows so that they appear as they are in the Teststand Sequence file:
    #_sdf = df.sort_values(["PARENT_SEQUENCE_NAME", "STEP_INDEX", "STEP_ORDER"], ascending = [True, True, True])
    _sdf = df.sort_values(["STEP_ORDER_NUMBER", "PROPERTY_ORDER_NUMBER"], ascending = [True, True])
    for index, row in _sdf.iterrows():  # index is combined by "parent name.step_index.pop_order" = STEP_ORDER
        _has_measurements = any([(p in row["PROPERTY_PATH"]) for p in ["Numeric", "Measurement.["]]) if row["PROPERTY_PATH"] else ("Numeric" in row["PROPERTY_TYPE"])
        if not _has_measurements:
            continue
        # simulate widget
        def _get_plausibe_units(given_units, row) -> str:
            if row["PROPERTY_PATH"] and ("Measurement.[" in row["PROPERTY_PATH"]):
                # this multi measurement need to have the right unit in place
                if given_units:
                    return given_units.capitalize()
            # if not, try to generate the units correct
            if any((p in str(row["STEP_NAME"]).lower() for p in ("volt", "vcc", "gnd", "ocv", "cell balance", "cell_balance"))):
                # note: last one (cell balance) is to fix forgotten unit in Corepack test
                units = "Voltage"
            elif "current" in str(row["STEP_NAME"]).lower():
                units = "Ampere"
            elif any(p in str(row["STEP_NAME"]).lower() for p in ("percent", "efficiency", "soc")):
                units = "Percent"
            elif any(p in str(row["STEP_NAME"]).lower() for p in ("ntc", "resistance")):
                units = "Ohm"
            else:
                units = given_units if given_units else ""
            return units.capitalize()

        #_units = str(row["UNITS"]) if row["UNITS"] else ("Volt" if "volt" in str(row["STEP_NAME"]).lower() else ("Ampere" if "current" in str(row["STEP_NAME"]).lower() else ""))
        match row["UNITS"]:
            case "A":
                _units = _get_plausibe_units("Ampere", row)
            case "V":
                _units = _get_plausibe_units("Voltage", row)
            case None:
                _units = _get_plausibe_units(None, row)
            case _:  # default case
                _units = _get_plausibe_units(str(row["UNITS"]).capitalize(), row)
        # we are creating a new column that contains the corrected unit string
        corrected_unit_column.append((index, _units))
        items = [
            index,  # this is STEP_ORDER
            str(row["PARENT_SEQUENCE_NAME"]),  # index 1
            str(row["STEP_NAME"]),  # index 2
            str(row["PROPERTY_PATH"]) if row["PROPERTY_PATH"] else str(row["PROPERTY_TYPE"]), # index 3
            _units,  # index 4
            str(row["LOW_LIMIT"]) if not np.isnan(row["LOW_LIMIT"]) else "",  # index 5
            str(row["HIGH_LIMIT"]) if not np.isnan(row["HIGH_LIMIT"]) else "",  # index 6
            # this shoulb be hidden from user:
            str(row["STEP_ID"]),    # index 7
            str(row["STEP_INDEX"]), # index 8
        ]
        #print("|".join(items))
        named_test_steps_list.append(items)
    # set the corrected unit strings as separate column to keep the original UNITS col
    _idx, _col = zip(*corrected_unit_column)
    df["UNITS_CORRECTED"] = pd.Series(_col, index=_idx)
    return named_test_steps_list, df


#--------------------------------------------------------------------------------------------------


def get_datarows_based_on_selection(checkboxes: list, steps_selection_list: List[List[str]], full_df: pd.DataFrame) -> list:
    """Filters the data rows based on the selected rows in checkboxes:
    Each checked box references a data row to filter for result.

    Args:
        checkboxes (list): _description_
        steps_selection_df (pd.DataFrame): _description_
        full_df (pd.DataFrame): _description_

    Returns:
        list: _description_
    """

    steps_selection_map = {}
    for item in steps_selection_list:
        steps_selection_map[item[0]] = item[1:]
    data_rows = []
    for c in checkboxes:
        if not c.value:
            continue
        # identify the row in dataset by step_order number which is encoded in the description of the checkbox
        _index = c.extra_step_order
        _row = steps_selection_map[_index]
        _name = " | ".join(_row[1:4])  # PARENT_SEQUENCE_NAME | STEP_NAME | PATH/STEP_TYPE
        #_index = c.description.replace("#", "")
        data = full_df.loc[
            ##(full_df["PARENT_SEQUENCE_NAME"] == _row[0])
            ##(full_df["STEP_NAME"] == _row[1])
            #(full_df["STEP_ID"] == _row[6])
            # this is needed even when using STEP_ID as the multiple numeric results have
            # same STEP_ID, same STEP_INDEX, same STEP_NAME ....
            ((full_df["PROPERTY_PATH"] == _row[2]) | (full_df["PROPERTY_TYPE"] == _row[2]))
            & (full_df["STEP_ORDER"] == _index)
            ##& (full_df["STEP_INDEX"] == _row[7])
        ]
        data_rows.append((_name, _index, _row, data))
    return data_rows


#--------------------------------------------------------------------------------------------------

class ExtraCheckbox(widgets.Checkbox):
    extra_step_order = None

def generate_selection_accordion(list_of_test_steps: List[List[str]], on_step_selected_callback: Callable) -> Tuple[Tuple , List]:
    """_summary_

    Args:
        list_of_test_steps (List[List[str]]): _description_
        on_step_selected_callback (Callable): _description_

    Returns:
        Tuple[tuple , list]: _description_
    """

    checkboxes = []
    _tree = Accordion(children=())
    _parent_name = None
    _parent_index = 0
    _list_of_nodes = []
    for row in list_of_test_steps:
        _cb = ExtraCheckbox(
            value=False,
            description=f'#{".".join(row[0].split(".")[1:])}',
            disabled=False,
            layout={"width": "13em"}
        )
        _cb.extra_step_order = row[0]  # this is the map index STEP_ORDER for data selection
        if on_step_selected_callback:
            # set a callback for that checkbox
            _cb.observe(on_step_selected_callback, names=["value"])
        checkboxes.append(_cb)
        items = [
            #widgets.Label(row[1]),  # PARENT_SEQUENCE_NAME"
            widgets.Label(row[2]),  # STEP_NAME
            widgets.Label(row[3]),  # PATH/STEP_TYPE
            widgets.Label(row[4] if row[4] else ""),  # UNITS_CORRECTED
            #widgets.Label(row[5] if not np.isnan(row[5]) else ""),  # LOW_LIMIT
            #widgets.Label(row[6] if not np.isnan(row[6]) else ""),  # HIGH_LIMIT
            widgets.Label(row[5]),  # LOW_LIMIT
            widgets.Label(row[6]),  # HIGH_LIMIT
        ]
        _box = widgets.HBox([
            _cb,
            widgets.GridBox(items[:2], layout=widgets.Layout(grid_template_columns="repeat(2, 20em)")),
            widgets.GridBox(items[2:], layout=widgets.Layout(grid_template_columns="repeat(3, 10em)"))
        ])
        if _parent_name:
            if _parent_name != row[1]:
                _tree.children += (widgets.VBox(_list_of_nodes),)
                _tree.set_title(_parent_index, _parent_name)
                _parent_index += 1
                # reset
                _parent_name = row[1]
                _list_of_nodes = []
        else:
            _parent_name = row[1]
            _list_of_nodes = []

        _list_of_nodes.append(_box)
    if len(_list_of_nodes) > 0:
        _tree.children += (widgets.VBox(_list_of_nodes),)
        _tree.set_title(_parent_index, _parent_name)
    _tree.selected_index = None
    return (_tree,), checkboxes



#--------------------------------------------------------------------------------------------------


def filter_rows(df: pd.DataFrame, match: dict) -> pd.DataFrame:
    """
    match = {
        "PARENT_SEQUENCE_NAME": value to search for,
        "PATH": value to search for,
        "STEP_NAME": value to search for
    }
    """
    #df_all = df.loc[all([(df[k] == v) for k,v in match.items()])  # generic way
    df_all = df.loc[(df["PARENT_SEQUENCE_NAME"] == match["PARENT_SEQUENCE_NAME"]) & \
                    (df["PATH"] == match["PATH"]) & \
                    (df["STEP_NAME"] == match["STEP_NAME"])]
    return df_all


#--------------------------------------------------------------------------------------------------


def split_df_pass_fail(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits the given data frame based on UUT_STATUS into two passed/failed frames
    if they have populated measurement values.

    Args:
        df (pd.DataFrame): DataFrame with columns UUT_STATUS and INTRINSIC_VALUE

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: passed DataFrame, failed DataFrame
    """

    #df_failed = df.loc[(df["UUT_STATUS"] == "Failed") & (~df["INTRINSIC_VALUE"].isna())]
    #df_passed = df.loc[(df["UUT_STATUS"] == "Passed") & (~df["INTRINSIC_VALUE"].isna())]
    df_failed = df.loc[(df["UUT_STATUS"] == "Failed")]
    df_passed = df.loc[(df["UUT_STATUS"] == "Passed")]
    return df_passed, df_failed


#--------------------------------------------------------------------------------------------------


def cpk_preparation(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame with columns INTRINSIC_VALUE, LOW_LIMIT and HIGH_LIMIT,
    which are being converted into numeric values of type float64.
    All rows having NaN in INTRINSIC_VALUE are dropped.

    Args:
        df (pd.DataFrame): _description_

    Returns:
        pd.DataFrame: input dataframe with converted columns INTRINSIC_VALUE,
        LOW_LIMIT and HIGH_LIMIT as float64
    """

    LSL = df["LOW_LIMIT"].astype("float64").min()
    USL = df["HIGH_LIMIT"].astype("float64").max()
    if np.isnan(LSL) or np.isnan(USL):
        # was less than comparision
        LSL = 0
        USL = df["LOW_LIMIT"].astype("float64").max()

    print(LSL, USL)
    data = df["INTRINSIC_VALUE"].dropna().astype("float")
    print(len(data))
    return data, LSL, USL


#--------------------------------------------------------------------------------------------------


def abbreviate_sheetname(name: str | list) -> str:
    """Expects either a string which splits the data by | char leaded by 'order number:' or
    a list of column data as strings in the same order, having '#order number' in first element.

    Example:

        ['#12', 'Start-Test', 'Messure VCC', 'NumericLimitTest', 'Volt', '3.22', '3.39'] -> ST_Messure_VCC

    Args:
        name (str | list): str = "Step Name | Path | Units "
                           list = [Step name, Path, Units,  ...ignored stuff... ]


    Returns:
        str: Abbreviated name containing sequence parent name fully abbreviated and
             test step name a little bit abbreviated.
    """

    if isinstance(name, str):
        _parts = [word for word in re.sub("\s", "", name, flags=re.DOTALL).split("|") if word != ""]
        #_abbrev = "_".join([e for e in (re.sub("\:|\s", "_", re.sub("\s", "", name)).split("|")) if e != ""][:-1])
        #_abbrev = "".join(filter(str.isupper, name.title()))
        #_abbrev = ''.join(word[0] for word in name.upper().split())
        _abbrev = "_".join(["".join(filter(str.isupper, _parts[1])), re.sub("\:|\s", "_", _parts[2], flags=re.DOTALL)])
        #_abbrev = re.sub("\:|\s", "_", _parts[0], flags=re.DOTALL)
    else:
        #_parts = [re.sub("\s", "", word) for word in name[1:] if word != ""]
        _abbrev = "_".join(["".join(filter(str.isupper, name[0])), re.sub("\:|\s", "_", name[1], flags=re.DOTALL)])
        #_abbrev = re.sub("\:|\s", "_", name[2], flags=re.DOTALL)
    _abbrev = re.sub("\[|\]", "", _abbrev, flags=re.DOTALL)
    return _abbrev


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":

   pass

# END OF FILE