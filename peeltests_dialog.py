from sys import maxsize
from typing import List, Tuple
from enum import Enum
import os
import json
import yaml
import pandas as pd
import multiprocessing as mp
import itertools as it
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.messagebox import showinfo, showerror, showwarning, askquestion
#import ttkbootstrap as ttk
#from ttkbootstrap.constants import *
#import sv_ttk

from hashlib import md5
from base64 import b64decode, b64encode
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import timezone, datetime
from winsound import PlaySound, SND_FILENAME
from random import randint

from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV

# import SQL managing modules
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rrc.dbcon import get_protocol_db_connector, get_teststand_users_db_connector
from rrc.barcode_scanner import create_barcode_scanner
from rrc.ui.login_dialog import identify_user_with_title


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init

# this is necessary to enable modbus logging
_log_fp = Path(__file__).parent / "../.." / "logs"
#logger_init(filename_base=_log_fp / "aws3_sps")  ## init root logger with different filename
logger_init(filename_base=None)
_log = getLogger(__name__, DEBUG)


# --------------------------------------------------------------------------- #

PRODUCTION_MODE: int = None  # is being overwritten by argument
ENABLE_UDI_SCAN: int = None  # is being overwritten by argument
EXCELFILES_SEARCH_PATH: Path = None  # where to search for peel tester measurement excel files
MANUAL_UDI_EDIT: bool = None  # is being overwritten by argument

#--------------------------------------------------------------------------------------------------

import random
import string

def heinz(x, reason):
    pass

def get_random_letter_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    numbers = string.digits
    return "".join(random.choice(letters) for i in range(length))


def get_random_digits_string(length):
    # choose from all digits
    numbers = string.digits
    return "".join(random.choice(numbers) for i in range(length))


def get_hash(o: dict) -> bytes:
    """Create a 24 base64 encoded characters hash of a dict.

    Args:
        o (dict): an dict

    Returns:
        str: hash as base64 encoded byte array
    """
    _s = json.dumps(o, sort_keys=True, ensure_ascii=True)
    _h = md5(_s.encode("utf8")).digest()
    return b64encode(_h)


def find_excel_for_udi(udi: str) -> Path:
    global EXCELFILES_SEARCH_PATH

    files = sorted(EXCELFILES_SEARCH_PATH.glob(f"*{udi}*.xls*"), key=os.path.getmtime)  # sort in ASCending time
    #files = reversed(sorted(list(EXCELFILES_SEARCH_PATH.glob(f"**/*{udi}.xls*"))))
    return files[-1]  # last one is most recent


def read_excel_of_peeltester(fp: Path) -> pd.DataFrame:
    df = pd.read_excel(fp)
    # we need to finde the line range which contains the interesting data in the first 4 columns
    start_line = df.loc[df.iloc[:,0] == "No."].index.values[0]    # !! Critical: could change when PeelTester software changes !!
    end_line = df.loc[df.iloc[:,0] == "Maximum"].index.values[0]  # !! Critical: could change when PeelTester software changes !!
    forces_df = df.iloc[(start_line + 1):end_line, [0,1,2,3]]
    forces_df.rename(columns={
        forces_df.columns[0]: "No.",
        forces_df.columns[1]: "MaxForce (N)",
        forces_df.columns[2]: "MinForce (N)",
        forces_df.columns[3]: "AvgForce (N)"
    }, inplace=True)
    return forces_df.astype({"No.": "int32", "MaxForce (N)": "float64", "MinForce (N)": "float64", "AvgForce (N)": "float64" })


def query_teststand_users_for_match(engine: sa.Engine, card_id: str, show_performance: bool = False) -> pd.DataFrame | None:
    #
    # UNUSED HERE - we are using the login dialog conform to Teststand
    #
    with engine.connect() as session:
        sql=sa.text(f"""SELECT
            username,
            pwd,
            access
            FROM `teststand_users` AS mu
            WHERE card_id='{card_id}'
        """)
        if show_performance:
            tic = perf_counter()
        print(sql)
        df = pd.read_sql(sql, session)
        print(f"Read {len(df)} data records.", end="")
        if show_performance:
            toc = perf_counter()
            print(f"Need {toc - tic:0.4f} seconds")
        else:
            print()  # add only linefeed
    return df


def query_welding_measurements(engine: sa.Engine, udi: str, show_performance: bool = False) -> pd.DataFrame | None:
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
                p.program_no
            FROM protocol.welding_measurements AS m
            LEFT JOIN protocol.welding_parameters AS p ON (m.ref_parameter = p.hash)
            WHERE m.udi = '{udi}'
            ORDER BY m.position ASC
        """)
        if show_performance:
            tic = perf_counter()
        print(sql)
        df = pd.read_sql(sql, session)
        print(f"Read {len(df)} data records.", end="")
        if show_performance:
            toc = perf_counter()
            print(f"Need {toc - tic:0.4f} seconds")
        else:
            print()  # add only linefeed
    return df



#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class PassFailCombobox(ttk.Combobox):
    def __init__(self, *args, **kwargs):
        _pass_fail = ("Pass", "Fail")
        super().__init__(*args, **kwargs, values=_pass_fail, state="readonly")
        _pd = self.tk.call('ttk::combobox::PopdownWindow', self)  # get popdownWindow reference
        lb = _pd + '.f.l' #get popdown listbox
        self._bind(('bind', lb),"<KeyPress>", self.popup_key_pressed, None)
        self.bind("<Key>", self.find_value_by_keypress)

    def popup_key_pressed(self, event):
        """Method allows by key selection if the dropdown has already opened."""

        values = self.cget("values")
        for i in it.chain(range(self.current() + 1, len(values)), range(0,self.current())):
            if event.char.lower() == values[i][0].lower():
                self.current(i)
                self.icursor(i)
                self.tk.eval(event.widget + ' selection clear 0 end')  # clear current selection
                self.tk.eval(event.widget + ' selection set ' + str(i))  # select new element
                self.tk.eval(event.widget + ' see ' + str(i))  # spin combobox popdown for selected element will be visible
                return

    def find_value_by_keypress(self, event) -> None:
        """method allows user to search through Combobox values by keyboard press
        as long as dropdown not is open."""

        keypress = event.char
        # If key pressed is a letter in alphabet
        if keypress.isalpha():
            values = self.cget("values")
            for i, c in enumerate(values):
                if keypress.lower() in c.lower():
                    self.current(i)
                    return


#--------------------------------------------------------------------------------------------------


class WindowUI(object):

    def __init__(self, command_queue: mp.Queue, scan_queue: mp.Queue, username: str, title: str = "PEEL TEST DIALOG"):
        global DEBUG, PRODUCTION_MODE, FORCES_LIMITS_SELECTION, MANUAL_UDI_EDIT

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        self.q_scan = scan_queue
        row_itr = it.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        #self.var_position = [tk.IntVar(self.root, i) for i in range(4)]
        self.var_part_number = tk.StringVar(self.root, "")
        self.var_operator = tk.StringVar(self.root, username)
        self.var_line_id = tk.StringVar(self.root, "")
        self.var_udi = tk.StringVar(self.root, "")
        self.var_positions = tk.StringVar(self.root, "")  # need to be converted to int on validation !
        self.var_forces_limits = tk.StringVar(self.root, "")
        self.var_label_status = tk.StringVar(self.root, "")
        # these are empty list on purpose - they'll be poulated later by callbacks
        self.var_peelforce_ax1 = []
        self.var_peelforce_ax2 = []
        self.var_result_peelforce_ax1 = []
        self.var_result_peelforce_ax2 = []
        self.var_visual_inspection_before = []
        self.var_visual_inspection_after = []
        # to build the combobox
        self.forces_limits_selection = FORCES_LIMITS_SELECTION
        # these are the converted limits
        self.limit_force_single_axis = float(0.0)
        self.limit_forces_sum = float(0.0)

        self.root.withdraw()  # hide window
        self.root.title(title)
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "ui" / "robot-icon.ico")
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "ui" / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        # This is where the magic happens
        #sv_ttk.set_theme("light")
        #style.theme_use("alt")
        style = ttk.Style()

        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        _padall = 8
        _w = 840  # width set manually
        _h = 750
        #_w = int(self.root.winfo_screenwidth() / 2)
        #_h = self.root.winfo_screenheight()
        # Set a minsize for the window
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        #self.root.minsize(_w, int(_h/2))
        self.root.minsize(_w, _h)
        #_x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        _x = int((self.root.winfo_screenwidth() - _w - _padall) / 2)
        _y = int((self.root.winfo_screenheight() - _h ) / 2)
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")
        #
        # setup widgets
        #
        # button
        style.configure('W.Toggle.TButton', font = ('calibri', 16, 'bold',))
        style.map("W.Toggle.TButton", foreground = [("active", "blue"), ("!active", "black")])
        #style.map("W.Toggle.TButton", foreground = [("active", "lightgreen"), ("!active", "green")])
        #style.map("W.Toggle.TButton", foreground = [("active", "red"), ("!active", "darkred")])

        # to debug layout we can use colored frame backgrounds
        style.configure('Frame1.TFrame', background='red')
        style.configure('Frame2.TFrame', background='blue')


        # we group two layouts on top of each other:
        #
        #   mainframe -> the common data of operatorand product
        #   positions_ui -> dynamic list of positions to enter by operator
        #
        self.vcmd_validate_positions_change = self.root.register(self.validate_positions_change)
        self.vcmd_validate_force_limits_selection = self.root.register(self.validate_force_limits_selection)
        self.vcmd_validate_forces_against_limits = self.root.register(self.validate_forces_against_limits)
        self.vcmd_validate_udi_in_db = self.root.register(self.validate_udi_in_db)
        self.positions_ui = None  # the self.positions_ui will be created by the positons change callback!
        self.mainframe = self._create_head_ui(self.root)
        self.mainframe.pack(side="top", anchor="n", fill="x", expand=False, padx=_padall, pady=_padall)
        # the self.positions_ui will be created by the positons change callback!
        self.validate_positions_change(force=True)  # we need to trigger a change validation here to create a zero list
        #self.positions_ui = self._create_position_ui_and_show(self.root, 0)  # empty list

        # hidden "ok" button to programmatically close this app
        # ok_button.bind("<Return>", _accept_udi)
        # ok_button.bind("<Key-Escape>", _cancel)
        # ok_button.grid_forget()

        # schedule queue processing callback
        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)
        if MANUAL_UDI_EDIT:
            self.entry_udi.focus_set()
        else:
            self.save_button.focus_set()

    #----------------------------------------------------------------------------------------------


    def _selection_to_limits(self):
        s = self.var_forces_limits.get()
        f = s.split("/")
        # we ignore the thickness
        self.limit_force_single_axis = float(f[1].replace("N", ""))
        self.limit_forces_sum = float(f[2].replace("N", ""))


    #----------------------------------------------------------------------------------------------


    def validate_udi_in_db(self, event) -> bool:
        _udi = self.var_udi.get()
        # simulate a scan to validate UDI in database
        self.q_scan.put({"udi_scanned": _udi})
        return True


    #----------------------------------------------------------------------------------------------


    def validate_force_limits_selection(self, event) -> bool:
        self._selection_to_limits()
        self.entry_force_limits.selection_clear()
        return self.validate_forces_against_limits(event)


    #----------------------------------------------------------------------------------------------

    def validate_forces_against_limits(self, event) -> bool:
        for i in range(len(self.var_peelforce_ax1)):
            # check the axis forces against the selected thresholds
            try:
                _ax1 = float(self.var_peelforce_ax1[i].get())
                self.var_result_peelforce_ax1[i].set("Pass" if (_ax1 >= self.limit_force_single_axis) else "Fail")
            except Exception as ex:
                _ax1 = 0
                showwarning(title="Force not numeric", message=f"Please correct numeric value '{_ax1}' at Ax1 position {i}.")
                return False

            try:
                _ax2 = float(self.var_peelforce_ax2[i].get())
                self.var_result_peelforce_ax2[i].set("Pass" if (_ax2 >= self.limit_force_single_axis) else "Fail")
            except Exception as ex:
                _ax2 = 0
                showwarning("Force not numeric", f"Please correct numeric value '{_ax2}' at Ax2 position {i}.")
                return False

            # check sum of axis forces
            self.var_result_peelforces_sum[i].set("Pass" if ((_ax1 + _ax2) >= self.limit_forces_sum) else "Fail")
        return True

    #----------------------------------------------------------------------------------------------


    def validate_positions_change(self, force: bool = False) -> bool:
        # using focusout as event
        try:
            value = int(self.var_positions.get())
            if (not force) and (value == len(self.var_peelforce_ax1)):
                return True
            if not (value >= 0) and (value < 30):
                return False
            if self.positions_ui:
                self.positions_ui.destroy()
            self.positions_ui = self._create_position_ui_and_show(self.root, value)
            return True
        except Exception as ex:
            pass  # ignore
        return False


    #----------------------------------------------------------------------------------------------

    def clear_dialog(self) -> None:
        pass


    #----------------------------------------------------------------------------------------------


    def count_peelforce_data_in_db_for_udi(self, udi: str) -> int:
        engine, _ = get_protocol_db_connector()
        sql = sa.text(f"SELECT position FROM peel_tests WHERE udi='{udi}'")
        check_records = pd.read_sql(sql, engine.connect())
        return len(check_records)


    #----------------------------------------------------------------------------------------------
    #
    # Validation of data & Save to DB
    #
    #----------------------------------------------------------------------------------------------

    def qualify_and_save_to_db(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        global PRODUCTION_MODE

        if not self.qualify_save_button_state():
            showwarning("WARNING", "Data not complete, cannot save to database yet.")
            #showerror("ERROR", "Cannot save to database")
            return False
        # save the positions data set to the DB
        df = pd.DataFrame({
            "position": [idx for idx, v in enumerate(self.var_peelforce_ax1)],
            "max_peelforce_ax1": [float(v.get()) for v in self.var_peelforce_ax1],
            "max_peelforce_ax2": [float(v.get()) for v in self.var_peelforce_ax2],
            "result_peelforce_ax1": [(v.get()[0].upper() if (v.get() and (v.get() != "")) else None) for v in self.var_result_peelforce_ax1],
            "result_peelforce_ax2": [(v.get()[0].upper() if (v.get() and (v.get() != "")) else None) for v in self.var_result_peelforce_ax2],
            "result_peelforces_sum": [(v.get()[0].upper() if (v.get() and (v.get() != "")) else None) for v in self.var_result_peelforces_sum],
            "visual_inspection_before": [(v.get()[0].upper() if (v.get() and (v.get() != "")) else None) for v in self.var_visual_inspection_before],
            "visual_inspection_after": [(v.get()[0].upper() if (v.get() and (v.get() != "")) else None) for v in self.var_visual_inspection_after],
        })
        # fill in all same values
        df["limit_peel_force_per_axis"] = self.limit_force_single_axis
        df["limit_peel_forces_sum"] = self.limit_forces_sum
        df["operator_name"] = self.var_operator.get()
        df["part_number"] = self.var_part_number.get()
        df["line_id"] = self.var_line_id.get()
        _udi = self.var_udi.get()
        df["udi"] = _udi

        # double check if there is an excel file present meanwhile
        self._collect_excel_information(_udi)

        # if we have an excel record, we can compare the forces against the excel ones
        if len(self.forces_df) > 0:
            # we can put the two axis lists together and compare them with the excel (both sorted!)
            user_input = sorted(df["max_peelforce_ax1"].to_list() + df["max_peelforce_ax2"].to_list())
            excel_input = sorted(self.forces_df["MaxForce (N)"].to_list())
            if user_input != excel_input:
                showwarning("Validation Failed",
                            f"The forces entered by user differ from the forces found in the Excel file for that UDI:\n{excel_input}\nCannot proceed!")
                return False

        engine, _ = get_protocol_db_connector()
        try:
            if not PRODUCTION_MODE:
                _count_records = self.count_peelforce_data_in_db_for_udi(_udi)
                if _count_records > 0:
                    res = askquestion("Request?", f"There are already {_count_records} records in DB.\nShould we delete then write again?")
                    if res == "yes" :
                        # do overwrite here!
                        sql = sa.text(f"DELETE FROM peel_tests WHERE udi='{_udi}'")
                        with engine.connect() as session:
                            r = session.execute(sql)
                            session.commit()
                    else:
                        showwarning("Abort saving to DB", f"Cannot save to DB as records altready exists.")
                        return False
            with engine.connect() as session:
                r = df.to_sql("peel_tests", session, if_exists="append", index=False, method="multi")
                session.commit()
            showinfo("Success saving to DB", f"Dataset with {len(df)} positions saved to DB.")
            self.clear_dialog()  # its easier to just scan a new UDI!
        except IntegrityError:
            showwarning("Abort saving to DB", f"Cannot save to DB as records altready exists.")
            return False
        except Exception as ex:
            showerror("Error while saving to DB", ex)
            return False
        return True

    #----------------------------------------------------------------------------------------------
    def _create_head_ui(self, root: tk.Tk) -> ttk.Frame:
        global MANUAL_UDI_EDIT

        _padall = 8
        frame = ttk.Frame(root, pad=(_padall,_padall,_padall,_padall), takefocus=False,
                          #style="Frame2.TFrame"  # DEBUG
        )
        frame.columnconfigure(8)
        frame.rowconfigure(6, minsize=10)

        # configure the column width equally to center everything nicely
        #frame.grid(row=0, column=0, sticky="NESW")
        #frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)
        frame.grid_columnconfigure(5, weight=1)
        frame.grid_columnconfigure(6, weight=1)
        frame.grid_columnconfigure(7, weight=1)

        # Labels + entry fields
        _row = 1
        ttk.Label(frame, text="Operator", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        self.entry_operator = ttk.Entry(frame, textvariable=self.var_operator, state="disabled")
        self.entry_operator.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="").grid(row=_row, column=0, columnspan=2)
        _row += 1

        ttk.Label(frame, text="UDI", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        if MANUAL_UDI_EDIT:
            # manual edit allowed
            self.entry_udi = ttk.Entry(frame, textvariable=self.var_udi, state="enabled", validate="focusout", validatecommand=(self.vcmd_validate_udi_in_db, "%P"))
        else:
            self.entry_udi = ttk.Entry(frame, textvariable=self.var_udi, state="disabled")
        self.entry_udi.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        
        _row += 1
        ttk.Label(frame, text="Part Number", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        self.entry_part_number = ttk.Entry(frame, textvariable=self.var_part_number, state="disabled")
        self.entry_part_number.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="Line", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        self.entry_line_id = ttk.Entry(frame, textvariable=self.var_line_id, state="disabled")
        self.entry_line_id.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="Positions", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        self.entry_positions = ttk.Entry(frame, textvariable=self.var_positions,
                                         validatecommand=self.vcmd_validate_positions_change,
                                         validate="focusout",
                                         state="disabled" if PRODUCTION_MODE else "enabled")
        self.entry_positions.grid(row=_row, column=1, columnspan=1, sticky=tk.NSEW)
        #_row += 1

        # the button needs to focus before the force limits -> define here
        self.save_button = ttk.Button(frame,
            text="SAVE to DB",
            #style="Accent.TButton",
            #style="Toggle.TButton",
            style="W.Toggle.TButton",
            #state="disabled",
            command=lambda: self.qualify_and_save_to_db(),
        )  # grid does NOT return self object, so we need to split the grid call!
        # save_button = tk.Button(frame,
        #     text="SAVE to DB",
        #     bg='grey',
        #     fg='black',
        #     relief='flat',
        #     width=20
        # )
        self.save_button.grid(row=1, column=3, columnspan=5, rowspan=4, ipady=30, ipadx=15)


        ttk.Label(frame, text="Limits of Forces", justify="left").grid(row=_row, column=3, sticky=tk.NSEW)
        self.entry_force_limits = ttk.Combobox(frame, textvariable=self.var_forces_limits,
                                               validate="focusout",
                                               validatecommand=(self.vcmd_validate_force_limits_selection, "%P"),
                                               values=self.forces_limits_selection, 
                                               state="readonly")
        self.entry_force_limits.bind("<<ComboboxSelected>>", lambda x: self.validate_force_limits_selection(x))
        self.entry_force_limits.current(0)  # preselect no. 1 in the list
        self.entry_force_limits.grid(row=_row, column=4, columnspan=3, sticky=tk.NSEW)
        self._selection_to_limits()
        _row += 1
        ttk.Label(frame, text="STATUS", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        self.label_status = ttk.Label(frame,
            textvariable=self.var_label_status, justify="left",
            #font=("-size", 12, "-weight", "bold"),
            #font=("-size", 12),
        )
        self.label_status.grid(row=_row, column=1, columnspan=6, pady=15, sticky=tk.NSEW)
        _row += 1


        return frame


    #----------------------------------------------------------------------------------------------
    def _update_position_ui(self, frame: ttk.Frame, number_of_positions: int) -> ttk.Frame:
        count_columns, count_rows = frame.grid_size()

        _pass_fail = ("Pass", "Fail")

        _row = 1
        ttk.Label(frame, text=f"Welding\nPosition", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        ttk.Label(frame, text=f"VI\nBefore", justify="left").grid(row=_row, column=1, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Peel Force (N)\nMax Ax1", justify="left").grid(row=_row, column=2, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Result\nAx1", justify="left").grid(row=_row, column=3, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Peel Force (N)\n Max Ax2", justify="left").grid(row=_row, column=4, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Result\nAx2", justify="left").grid(row=_row, column=5, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Result\nSum", justify="left").grid(row=_row, column=6, sticky=tk.NSEW)
        ttk.Label(frame, text=f"VI\n After", justify="left").grid(row=_row, column=7, sticky=tk.NSEW)
        _row += 1
        ttk.Separator(frame, orient="horizontal").grid(row=_row, column=0,columnspan=7, ipady=2, sticky=tk.NSEW)

        # we need to generate the vars dynamically
        self.var_peelforce_ax1 = [tk.DoubleVar(self.root, None) for i in range(number_of_positions)]
        self.var_peelforce_ax2 = [tk.DoubleVar(self.root, None) for i in range(number_of_positions)]
        self.var_result_peelforce_ax1 = [tk.StringVar(self.root, None) for i in range(number_of_positions)]
        self.var_result_peelforce_ax2 = [tk.StringVar(self.root, None) for i in range(number_of_positions)]
        self.var_result_peelforces_sum = [tk.StringVar(self.root, None) for i in range(number_of_positions)]
        self.var_visual_inspection_before = [tk.StringVar(self.root, None) for i in range(number_of_positions)]
        self.var_visual_inspection_after = [tk.StringVar(self.root, None) for i in range(number_of_positions)]

        _row += 1
        _combo_width = 8
        for i in range(number_of_positions):
            ttk.Label(frame, text=f"Position {i}:", justify="left").grid(row=_row, column=0, sticky=tk.NSEW),
            _visual_inspection_before = PassFailCombobox(frame, textvariable=self.var_visual_inspection_before[i], width=_combo_width)
            _visual_inspection_before.grid(row=_row, column=1)
            _peelforce_ax1 = ttk.Entry(frame, textvariable=self.var_peelforce_ax1[i], validate="focusout", validatecommand=(self.vcmd_validate_forces_against_limits, "%P"))
            _peelforce_ax1.grid(row=_row, column=2)
            #_result_peelforce_ax1 = PassFailCombobox(frame, textvariable=self.var_result_peelforce_ax1[i], width=_combo_width)
            #_result_peelforce_ax1.grid(row=_row, column=3)
            _result_peelforce_ax1 = ttk.Checkbutton(frame, variable=self.var_result_peelforce_ax1[i], state="disabled", onvalue="Pass", offvalue="Fail")
            _result_peelforce_ax1.grid(row=_row, column=3)
            _peelforce_ax2 = ttk.Entry(frame, textvariable=self.var_peelforce_ax2[i], validate="focusout", validatecommand=(self.vcmd_validate_forces_against_limits, "%P"))
            _peelforce_ax2.grid(row=_row, column=4)
            #_result_peelforce_ax2 = PassFailCombobox(frame, textvariable=self.var_result_peelforce_ax2[i], width=_combo_width)
            #_result_peelforce_ax2.grid(row=_row, column=5)
            _result_peelforce_ax2 = ttk.Checkbutton(frame, variable=self.var_result_peelforce_ax2[i], state="disabled", onvalue="Pass", offvalue="Fail")
            _result_peelforce_ax2.grid(row=_row, column=5)
            _result_peelforces_sum = ttk.Checkbutton(frame, variable=self.var_result_peelforces_sum[i], state="disabled", onvalue="Pass", offvalue="Fail")
            _result_peelforces_sum.grid(row=_row, column=6)
            _visual_inspection_after = PassFailCombobox(frame, textvariable=self.var_visual_inspection_after[i], width=_combo_width)
            _visual_inspection_after.grid(row=_row, column=7)
            _row += 1
        return frame


    #----------------------------------------------------------------------------------------------
    def _create_position_ui_and_show(self, root: tk.Tk, number_of_positions: int) -> ttk.Frame:
        _padall = 4
        frame = ttk.Frame(root, pad=(_padall,_padall,_padall,_padall), takefocus=False,
                          #style="Frame1.TFrame"  # DEBUG
        )
        frame.columnconfigure(8)
        #frame.rowconfigure(6, minsize=10)

        # configure the column width equally to center everything nicely
        #frame.grid(row=0, column=0, sticky="NESW")
        #frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)
        frame.grid_columnconfigure(5, weight=1)
        frame.grid_columnconfigure(6, weight=1)
        frame.grid_columnconfigure(7, weight=1)
        frame  = self._update_position_ui(frame, number_of_positions)
        # show
        frame.pack(side="top", anchor="n", fill="both", expand=True, padx=10, pady=5)
        return frame


    #----------------------------------------------------------------------------------------------
    def qualify_save_button_state(self) -> bool:
        try:
            _pass_fail = ("Pass", "Fail")
            _positions = int(self.var_positions.get())
            # check number of entries is equal positions definition
            ok = ((_positions > 0) and
                len(self.var_peelforce_ax1) == _positions and
                len(self.var_peelforce_ax2) == _positions and
                len(self.var_result_peelforce_ax1) == _positions and
                len(self.var_result_peelforce_ax2) == _positions and
                len(self.var_visual_inspection_before) == _positions and
                len(self.var_visual_inspection_after) == _positions)
            ok = (ok and
                all([(v.get() and (float(v.get()) > 0)) for v in self.var_peelforce_ax1]) and
                all([(v.get() and (float(v.get()) > 0)) for v in self.var_peelforce_ax2]))
            ok = (ok and
                all([(v.get() and (v.get() in _pass_fail)) for v in self.var_result_peelforce_ax1]) and
                all([(v.get() and (v.get() in _pass_fail)) for v in self.var_result_peelforce_ax2]))
            ok = (ok and
                all([(v.get() and (v.get() in _pass_fail)) for v in self.var_visual_inspection_before]) and
                all([(v.get() and (v.get() in _pass_fail)) for v in self.var_visual_inspection_after]))
        except Exception as ex:
            ok = False
        #self.save_button.state = "enabled" if ok else "disabled"
        return ok

    #----------------------------------------------------------------------------------------------
    def _collect_operator_information(self, card_id: str) -> Tuple[bool, dict]:
        #
        # UNUSED HERE - we are using the login dialog conform to Teststand
        #
        print(f"CHECK ID {card_id} from database...")
        engine, _ = get_teststand_users_db_connector()
        user_df = query_teststand_users_for_match(engine, card_id)

        if len(user_df) == 0:
            # not found! -> do not login
            showinfo("WARNING", f"User login not found in database.")
            return False, {}

        user = {
            "username": user_df.iloc[0, 0],
            "pwd": user_df.iloc[0, 1],
            "access": int(user_df.iloc[0, 2]),
        }
        if user["access"] == 0:
            # has no access!
            showinfo("WARNING", f'User {user["username"]} is not allowed to login.')
            return False, user
        return True, user


    #----------------------------------------------------------------------------------------------
    def _collect_uut_information(self, udi: str) -> Tuple[bool, pd.DataFrame]:
        print("Requesting database for UDI to get welding positions...")
        engine, _ = get_protocol_db_connector()
        uut_df = query_welding_measurements(engine, udi, show_performance=True)
        if len(uut_df) == 0:
            # not found! -> do not proceed
            txt = f"No Data in Database for UDI {udi} found, cannot proceed!"
            print(txt)
            showinfo("WARNING", txt)
            return False, uut_df
        print(f"Got record: {len(uut_df)}")
        return True, uut_df


    def _collect_excel_information(self, udi) -> str:
        try:
            fn = find_excel_for_udi(udi)
            self.forces_df = read_excel_of_peeltester(fn)
            print(self.forces_df.dtypes, self.forces_df.head(20),)
            _e = f"Found Excel file with {len(self.forces_df)} entries of forces."
        except Exception as ex:
            # cannot read
            print(f"Cannot read Excel file data for UDI {udi}", ex)
            self.forces_df = pd.DataFrame()  # empty
            _e = "No Excel file found, cannot validate forces."
        return _e

    def process_command_queue(self):
        if not self.q_scan.empty():
            a = self.q_scan.get()
            #print("UI:", a)
            _do_update = False
            _play_soundfile = None
            while a:
                if "card_id_scanned" in a:
                    _card_id = a["card_id_scanned"]
                    _op_ok, _operator_info = self._collect_operator_information(_card_id)
                    if _op_ok:
                        pass

                if "udi_scanned" in a:
                    _udi = a["udi_scanned"]
                    print("UI:UPDATE UDI:", _udi)

                    # 1) read excel file for validation of human entries
                    _e = self._collect_excel_information(_udi)

                    # 2) check peelforce database for this UDI
                    if PRODUCTION_MODE:
                        _count_forces = self.count_peelforce_data_in_db_for_udi(_udi)
                        if _count_forces > 0:
                            showwarning("Warning", f"Peelforces already assigned for UDI '{_udi}'\nCannot proceed!")
                            break  # DIRTY SANCHEZ!

                    # 3) read database for welding measurements of this UDI
                    ok, self.uut_df = self._collect_uut_information(_udi)
                    # 4) Prepare UI with needed positions
                    if len(self.uut_df):
                        _positions = len(self.uut_df)
                        if len(self.uut_df) > 0:
                            # get some overall info from the first entry of DB
                            head_info = self.uut_df.iloc[0].to_dict()
                            print(head_info)
                            self.var_part_number.set(head_info["part_number"])
                            self.var_line_id.set(head_info["line_id"])
                            #head_info["ts"]
                            _p = f"Found {len(self.uut_df)} welding positions in DB."
                            if len(self.forces_df)>0:
                                _v = "Validation possible." if (2*len(self.uut_df) == len(self.forces_df)) \
                                                            else "Number of entries differ: Validation not possible."
                            else:
                                _v = ""
                    else:
                        _p = "No welding positions found in DB !"
                        _v = ""
                        _positions = randint(0, len(self.forces_df)) if (len(self.forces_df) > 0) else 0

                    self.var_label_status.set(f"{_e} {_p} {_v}")
                    self.var_positions.set(_positions)
                    self.validate_positions_change(force=True)  # we need to trigger a change validation here

                    #self.label_udi.config(background="lightblue", foreground="black")
                    self.var_udi.set(_udi)
                    _do_update = True

                break  # DIRTY SANCHEZ!

                # if "udi_rejected" in a:
                #     self.label_udi.config(background="orange", foreground="black")
                #     self.var_label_udi.set("UDI REJECTED")
                #     _play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz")
                #     print("UI:REJECTED UDI")
                #     _do_update = True
                #     pass
                # if "udi_not_confirmed" in a:
                #     self.label_udi.config(background="orange", foreground="red")
                #     self.var_label_udi.set(a["udi_not_confirmed"])
                #     print("UI:BLACKLISTED UDI")
                #     _do_update = True
                #     pass
                # if "welding_check" in a:
                #     # position of welding
                #     _fgcolor = "white"
                #     if "passed" in a["welding_check"]:
                #         self.label_udi.config(background="LimeGreen", foreground=_fgcolor)
                #     else:
                #         self.label_udi.config(background="OrangeRed", foreground=_fgcolor)
                #         _play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz-hard")
                #     self.var_label_udi.set(a["udi"])
                #     print("UI:RESULT")
                #     _do_update = True
                # if "result" in a:
                #     # result overall
                #     #_fgcolor = "black" if "\n" in a["udi"] else "white"
                #     _fgcolor = "black"
                #     if "passed" in a["result"]:
                #         self.label_udi.config(background="green", foreground=_fgcolor)
                #     else:
                #         self.label_udi.config(background="red", foreground=_fgcolor)
                #         #_play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz")
                #     self.var_label_udi.set(a["udi"])
                #     print("UI:RESULT")
                #     _do_update = True
            if _do_update:
                self.root.update()
            if _play_soundfile:
                PlaySound(_play_soundfile, SND_FILENAME)
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())


    def run_mainloop(self):
        self.root.mainloop()




#--------------------------------------------------------------------------------------------------
# *** PROCESS ***
#

def _esc(v) -> str:
    """Return the value v as either string with parentheses or number.

    Intended to be used with sql statements.

    Args:
        v (Any): Does expect v being a basic type of either float,int, bytes or str.

    Returns:
        str: String with parentheses or plain number as string without parentheses.
    """
    if v is None:
        # None -> NULL
        return "NULL"
    else:
        if isinstance(v, (int,float)):
            return str(v)
        else:
            return f"'{v}'"


def esc_values(lst: List[tuple]) -> str:
    """
    Converts a list of key,value tuples into comma separated list of key=value string.
    The List is separated by comma.

    Intended to be used with sql statements.

    Args:
        lst (List[tuple]): _description_

    Returns:
        str: "key=value|'value', ..."
    """
    return ",".join([f"{k}={_esc(v)}" for k,v in lst])




#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#
# *** SCANNER ***
#
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class ProcessScanner(mp.Process):

    def __init__(self, resource_str: str, ui_queue: mp.Queue) -> None:
        mp.Process.__init__(self)
        global DEBUG, SIMULATE_UDI_SCAN
        self._log = getLogger(__name__, DEBUG)
        self.ui_queue = ui_queue
        self.simulate_scan = SIMULATE_UDI_SCAN
        self.resource_str = resource_str

    def run(self) -> None:
        """
        This is the process context in which we run the scanner.
        Create all relevant objects from here!
        """

        proc_name = self.name
        resource_str = self.resource_str
        scanner = None
        _retry_timeout = 1
        if not self.simulate_scan:
            while True:
                _udi = None
                try:
                    if not scanner:
                        scanner = create_barcode_scanner(resource_str)
                    _udi = scanner.request(None, timeout=None).strip()
                    # after successful scan, reset the timeout
                    print(_udi)
                    _retry_timeout = 1
                except TimeoutError:
                    pass  # this is ok to keep the loop running
                except Exception as ex:
                    # this is a real failure to stop this process
                    print(f"Cannot connect scanner {resource_str}: {ex}")
                    print(f"Trying to reconnect scanner.")
                    scanner = None
                    #print(f"{proc_name}:End")
                    #return
                    sleep(_retry_timeout)  # give a bit until reconnect
                    _retry_timeout = min(2*_retry_timeout, 30)  # fibonacci
                if _udi:
                    msg = {"udi_scanned": _udi}
                    self.ui_queue.put(msg)  # this goes to the UI process

        # else:
        #     # ********** Simulation Profile *************
        #     #while True:
        #         # sleep(3.0)
        #         # _card_id = "007"
        #         # self.ui_queue.put({"card_id_scanned": _card_id})  # FAIL
        #         # sleep(2.0)
        #         # _card_id = "00"
        #         # self.ui_queue.put({"card_id_scanned": _card_id})  # SUCCESS

        #         sleep(2.0)
        #         _udi = "1CELL" + get_random_digits_string(12)
        #         self.ui_queue.put({"udi_scanned": _udi})  # FAIL
        #         sleep(3.0)
        #         _udi = "1CELL00000002555"
        #         self.ui_queue.put({"udi_scanned": _udi})  # SUCCESS (missing positions)
        #         sleep(3.0)
        #         _udi = "1CELL00000002B84"
        #         self.ui_queue.put({"udi_scanned": _udi})  # SUCCESS (full positions)

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    # need to initialize logger on load

    print("=== PEEL TEST DIALOG ===")

    _default_scanner_resource = "COM1,9600,8N1"
    _default_peeltester_filepath_ = Path(__file__).parent / "sampledata"  # DEVELOPMENT
    _default_peeltester_filepath_ = Path(__file__).parent  # PRODUCTION

    _product_list = ["RRC2020B", "RRC2040B", "RRC2054S", "RRC2040-2S", "RRC2054-2S", "SPINEL"]

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    parser.add_argument("--excelfilepath", action="store", default=_default_peeltester_filepath_, help="Path to search for peel tester output excel files containing UDI in filename.")
    parser.add_argument("--scannerport", action="store", default=_default_scanner_resource, help="Resource string for scanner, which can be IP:PORT or local PORT,[baud],[8N1|8E1|8O1].")
    parser.add_argument("--simulate_scan", action="store_true", help="Set a product for simulated UDI scan interface.")
    parser.add_argument("--manual_udi", action="store_true", help="Enables the manual entry of an UDI in parallel to a scanner.")

    args = parser.parse_args()

    PRODUCTION_MODE = not args.development
    ENABLE_UDI_SCAN = (PRODUCTION_MODE or args.simulate_scan)
    SIMULATE_UDI_SCAN = args.simulate_scan
    EXCELFILES_SEARCH_PATH = Path(args.excelfilepath)
    MANUAL_UDI_EDIT = args.manual_udi

    FORCES_LIMITS_SELECTION = [
        "0.15mm / 20N / 60N",   # connector thickness / single / sum
        "0.30mm / 35N / 100N"   # connector thickness / single / sum
    ]

    # test of read function:
    #fn = find_excel_for_udi("1CELL00000002555")
    #forces_df = read_excel_of_peeltester(fn)
    #print(forces_df.dtypes, forces_df.head(20),)

    w = None
    s = None
    try:
        # STEP 1: login operator
        access = 0
        username = None if PRODUCTION_MODE else "administrator"
        while not username and not access > 0:
            ok, username, _, access = identify_user_with_title(allow_manual_edit=True, title="PEEL TEST DIALOG - User Login")
            if not ok:
                print("User has terminated dialog.")
                exit()
        # STEP 2: start dialog for this operator
        #
        # Establish communication queues
        q_cmd = mp.Queue()
        q_scan = mp.Queue()
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, q_scan, username)
        # start sub-process for scanner
        s = ProcessScanner(args.scannerport, q_scan)
        s.start()
        w.run_mainloop()
    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        # Add a poison pill
        #q_cmd.put(None)
        if s and s.is_alive():
            s.terminate()
            s.join(timeout=0.5)  # short process ...

# END OF FILE