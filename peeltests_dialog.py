from sys import maxsize
from typing import List, Tuple
from enum import Enum
import os
import json
import yaml
import pandas as pd
import multiprocessing as mp
import itertools
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.messagebox import showinfo
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

#--------------------------------------------------------------------------------------------------

import random
import string


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
            ORDER BY m.ts DESC
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


class WindowUI(object):

    def __init__(self, command_queue: mp.Queue, scan_queue: mp.Queue, username: str, title: str = "PEEL TEST DIALOG"):
        global DEBUG, PRODUCTION_MODE

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        self.q_scan = scan_queue
        row_itr = itertools.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        #self.var_position = [tk.IntVar(self.root, i) for i in range(4)]
        self.var_part_number = tk.StringVar(self.root, "")
        self.var_operator = tk.StringVar(self.root, username)
        self.var_udi = tk.StringVar(self.root, "")

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
        _w = 740  # width set manually
        _h = 500
        #_w = int(self.root.winfo_screenwidth() / 2)
        #_h = self.root.winfo_screenheight()
        # Set a minsize for the window
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        #self.root.minsize(_w, int(_h/2))
        self.root.minsize(_w, _h)
        #_x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        _x = int(self.root.winfo_screenwidth() - _w - _padall)
        _y = int((self.root.winfo_screenheight() / 2) - (_h / 2))
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")
        #
        # setup widgets
        #
        # button
        style.configure('W.Toggle.TButton', font = ('calibri', 16, 'bold',))
        style.map("W.Toggle.TButton", foreground = [("active", "blue"), ("!active", "black")])
        #style.map("W.Toggle.TButton", foreground = [("active", "lightgreen"), ("!active", "green")])
        #style.map("W.Toggle.TButton", foreground = [("active", "red"), ("!active", "darkred")])

        #style.configure('W.Toggle.TButton', font =('calibri', 10, 'bold', 'underline'), foreground = 'red')
        #style.configure('C.TButton.TLabel', padding=[30,10,50,60])
        #style.configure('C.TLabel', foreground = 'black', width = 20, borderwidth=1, focusthickness=4, focuscolor="none")
        #style.map("C.TLabel",
        #    foreground = [('pressed','red'),('active','blue')],
        #    background = [('pressed','!disabled','black'),('active','gray')],
        #    relief=[('pressed', 'sunken'),
        #            ('!pressed', 'raised')]
        #)
        #style.configure('TButton', background = 'gray', foreground = 'black', width = 20, borderwidth=1, focusthickness=4, focuscolor="none")
        # style.map("TButton",
        #   background = [("active", "red"), ("!active", "blue")],
        #   foreground = [("active", "yellow"), ("!active", "red")])
        # style.map("TButton.Button.label", background = "gray", foreground="yellow")
        #style.map('TButton', foreground=[('active','green')], background=[('active','orange')])
        #style.configure('B1.TButton', foreground="red", background='#232323')
        #style.map('B1.TButton', background=[("active","#ff0000")])


        self.mainframe = self._create_head_ui(self.root)
        self.mainframe.pack(side="top", fill="both", expand=True)
        #self.mainframe.grid(column=0, row=0, sticky=tk.NSEW)
        self.positions_ui, e_pos = self._create_position_ui(self.root, 0)  # empty list
        self.positions_ui.pack(side="top", fill="both", expand=True)
        #self.positions_ui.grid(column=0, row=1, sticky=tk.NSEW)

        # _colspan = 2
        # #_row = next(row_itr)
        # label_1 = ttk.Label(self.mainframe,text="PART NUMBER",justify="center", font=("-size", 10))
        # label_1.grid(row=next(row_itr), column=0, columnspan=_colspan , ipady=5)
        # label_2 = ttk.Label(self.mainframe,
        #                     textvariable=self.var_label_part_number,
        #                     justify="center", font=("-size", 16, "-weight", "bold"))
        # label_2.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)
        # # label_s = ttk.Label(self.mainframe,
        # #                     textvariable=self.var_label_sequence,
        # #                     justify="center", font=("-size", 10, "-weight", "bold"))
        # # label_s.grid(row=next(row_itr), column=0, columnspan=2, ipadx=10, ipady=10)
        # if PRODUCTION_MODE:
        #     self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center",
        #                                font=("-size", 14, "-weight", "bold"), background="gray", foreground="black")
        #     self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=50, sticky="ew")
        # else:
        #     self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center", font=("-size", 12))
        #     self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5, sticky="ew")

        # #_row = next(row_itr)
        # label3 = ttk.Label(self.mainframe,text="SEQUENCE POS",justify="center", font=("-size", 10))
        # label3.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)
        # label4 = ttk.Label(self.mainframe,
        #                     textvariable=self.var_label_position,
        #                     justify="center", font=("-size", 20, "-weight", "bold"))
        # label4.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)

        # label5 = ttk.Label(self.mainframe,text="PROGRAM",justify="center",font=("-size", 18))
        # label5.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)
        # label6 = ttk.Label(self.mainframe,
        #     textvariable=self.var_label_program,
        #     justify="center", font=("-size", 32, "-weight", "bold"))
        # label6.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)

        # if not PRODUCTION_MODE:
        #     # Buttons
        #     _row = next(row_itr)
        #     style.configure('B1.TButton', foreground="red", background='#232323')
        #     style.map('B1.TButton', background=[("active","#ff0000")])
        #     style.configure('B2.TButton', foreground="green", background='#232323')
        #     style.map('B2.TButton', background=[("active","#ff0000")])
        #     #style.configure('TButton', background = 'red', foreground = 'green', width = 20, borderwidth=1, focusthickness=3, focuscolor='none')

        #     step_back_button = ttk.Button(self.mainframe, text="STEP BACK",  style="B1.TButton",
        #         command=lambda: self.q_cmd.put({"move_counter": -1}))
        #     step_back_button.grid(row=_row, column=0, ipady=50, ipadx=20, sticky=tk.NSEW)

        #     step_forward_button = ttk.Button(self.mainframe, text="STEP FORWARD",  style="B2.TButton",
        #         command=lambda: self.q_cmd.put({"move_counter": +1}))
        #     step_forward_button.grid(row=_row, column=1, ipady=50, ipadx=5, sticky=tk.NSEW)

        #     # separator = ttk.Separator(self.mainframe)
        #     # separator.grid(row=next(row_itr), column=0, columnspan=2, padx=(20, 10), pady=10, sticky="ew")
        #     reset_seq_button = ttk.Button(self.mainframe, text="RESET SEQUENCE",
        #         command=lambda: self.q_cmd.put({"reset_counter": 0}))
        #     #ok_button.bind("<Return>", _accept_udi)
        #     #ok_button.bind("<Key-Escape>", _cancel)
        #     reset_seq_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, sticky=tk.NSEW)
        #     #ok_button.grid_forget()


        # # Some more information labels
        # _row = next(row_itr)
        # #label_10 = ttk.Label(self.mainframe, textvariable=self.var_label_sequence, font=("-size", 8))
        # #label_10.grid(row=_row, column=0,  ipady=10)
        # label_10 = ttk.Label(self.mainframe, anchor=tk.CENTER, textvariable=self.var_label_sequence_length, font=("-size", 8))
        # label_10.grid(row=_row, column=0,  ipady=10, sticky="ew")
        # label_11 = ttk.Label(self.mainframe, anchor=tk.CENTER, textvariable=self.var_label_sequence_revision, font=("-size", 8))
        # label_11.grid(row=_row, column=1, ipady=10, sticky="ew")

        # label_12 = ttk.Label(self.mainframe, textvariable=self.var_label_resource_str, font=("-size", 8))
        # label_12.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)

        # # Sizegrip
        # #sizegrip = ttk.Sizegrip(self.root)
        # #sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))

        # ## Add an information widget.
        # #label = ttk.Label(mainframe, text=f'\nWelcome to hello_world*4.py.\n')
        # #label.grid(column=0, row=next(row_itr), sticky='w')

        # schedule queue processing callback
        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)




    def _create_head_ui(self, root: tk.Tk) -> ttk.Frame:
        _padall = 4
        frame = ttk.Frame(root, pad=(_padall,_padall,_padall,_padall), takefocus=True)
        frame.columnconfigure(5)
        frame.rowconfigure(6, minsize=10)

        # configure the column width equally to center everything nicely
        #frame.grid(row=0, column=0, sticky="NESW")
        #frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)

        # Labels + entry fields
        _row = 1
        ttk.Label(frame, text="Operator", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        e_op = ttk.Entry(frame, textvariable=self.var_operator, state="disabled")
        e_op.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="").grid(row=_row, column=0, columnspan=2, ipady=10)
        _row += 1
        ttk.Label(frame, text="Part Number", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        e_pn = ttk.Entry(frame, textvariable=self.var_part_number, state="disabled")
        e_pn.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="UDI", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        e_udi = ttk.Entry(frame, textvariable=self.var_udi, state="disabled")
        e_udi.grid(row=_row, column=1, columnspan=2, sticky=tk.NSEW)
        _row += 1
        ttk.Label(frame, text="").grid(row=_row, column=0, columnspan=2, ipady=10)
        _row += 1

        save_button = ttk.Button(frame,
            text="SAVE to DB",
            #style="Accent.TButton",
            #style="Toggle.TButton",
            style="W.Toggle.TButton",

            #command=lambda: self.q_cmd.put({"move_counter": -1})
        )  # grid does NOT return self object, so we need to split the grid call!
        # save_button = tk.Button(frame,
        #     text="SAVE to DB",
        #     bg='grey',
        #     fg='black',
        #     relief='flat',
        #     width=20
        # )
        save_button.grid(row=1, column=3, columnspan=2, rowspan=4, ipady=30, ipadx=15)
        save_button.focus_set()
        return frame


    def _update_position_ui(self, frame: ttk.Frame, number_of_positions: int) -> Tuple[ttk.Frame, List[Tuple]]:
        count_columns, count_rows = frame.grid_size()

        _row = 1
        ttk.Label(frame, text=f"Welding Position", justify="left").grid(row=_row, column=0, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Visual Inspection Before", justify="left").grid(row=_row, column=1, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Peel Force Ax1", justify="left").grid(row=_row, column=2, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Peel Force Ax2", justify="left").grid(row=_row, column=3, sticky=tk.NSEW)
        ttk.Label(frame, text=f"Visual Inspection After", justify="left").grid(row=_row, column=4, sticky=tk.NSEW)
        _row += 1
        ttk.Separator(frame, orient="horizontal").grid(row=_row, column=0,columnspan=5, ipady=2, sticky=tk.NSEW)

        # we need to generate the vars dynamically
        self.var_peelforce_ax1 = [tk.DoubleVar(self.root, None) for i in range(number_of_positions)]
        self.var_peelforce_ax2 = [tk.DoubleVar(self.root, None) for i in range(number_of_positions)]
        self.var_visual_inspection_ax1 = [tk.BooleanVar(self.root, None) for i in range(number_of_positions)]
        self.var_visual_inspection_ax2 = [tk.BooleanVar(self.root, None) for i in range(number_of_positions)]
        e_pos = []
        _row += 1
        for i in range(number_of_positions):
            ttk.Label(frame, text=f"Position {i}:", justify="left").grid(row=_row, column=0, sticky=tk.NSEW),
            _visual_inspection_ax1 = ttk.Checkbutton(frame, variable=self.var_visual_inspection_ax1[i], onvalue=1, offvalue=0)
            _visual_inspection_ax1.grid(row=_row, column=1)
            _peelforce_ax1 = ttk.Entry(frame, textvariable=self.var_peelforce_ax1[i])
            _peelforce_ax1.grid(row=_row, column=2)
            _peelforce_ax2 = ttk.Entry(frame, textvariable=self.var_peelforce_ax2[i])
            _peelforce_ax2.grid(row=_row, column=3)
            _visual_inspection_ax2 = ttk.Checkbutton(frame, variable=self.var_visual_inspection_ax2[i], onvalue=1, offvalue=0)
            _visual_inspection_ax2.grid(row=_row, column=4)
            # list them for later access
            e_pos.append((_peelforce_ax1, _peelforce_ax2, _visual_inspection_ax1, _visual_inspection_ax2))
            _row += 1

        return frame, e_pos


    def _create_position_ui(self, root: tk.Tk, number_of_positions: int) -> Tuple[ttk.Frame, List[Tuple]]:
        _padall = 4
        frame = ttk.Frame(root, pad=(_padall,_padall,_padall,_padall), takefocus=False)
        frame.columnconfigure(5)
        #frame.rowconfigure(6, minsize=10)

        # configure the column width equally to center everything nicely
        #frame.grid(row=0, column=0, sticky="NESW")
        #frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)
        return self._update_position_ui(frame, number_of_positions)


    def _collect_operator_information(self, card_id: str) -> Tuple[bool, dict]:
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


    def process_command_queue(self):
        if not self.q_scan.empty():
            a = self.q_scan.get()
            #print("UI:", a)
            _do_update = False
            _play_soundfile = None
            if a:
                if "card_id_scanned" in a:
                    _card_id = a["card_id_scanned"]
                    _op_ok, _operator_info = self._collect_operator_information(_card_id)
                    if _op_ok:
                        pass

                if "udi_scanned" in a:
                    _udi = a["udi_scanned"]
                    print("UI:UPDATE UDI:", _udi)
                    # 1) read excel file for validation of human entries
                    try:
                        fn = find_excel_for_udi(_udi)
                        forces_df = read_excel_of_peeltester(fn)
                        print(forces_df.dtypes, forces_df.head(20),)
                    except Exception as ex:
                        # cannot read
                        print(f"Cannot read data for UDI {_udi}", ex)
                        forces_df = None
                    # 2) read database for welding measurements of this UDI
                    _uut_df = self._collect_uut_information(_udi)
                    # 3) Prepare UI with needed positions
                    if len(_uut_df):
                        _positions = len(_uut_df)
                    else:
                        _positions = randint(0, len(forces_df)) if forces_df else 0

                    #self._update_position_ui(self.positions_ui, randint(0, len(forces_df)))
                    self.positions_ui.destroy()
                    self.positions_ui, _ = self._create_position_ui(self.root, _positions)
                    #self.positions_ui.grid(column=0, row=1, sticky=tk.NSEW)
                    self.positions_ui.pack(side="top", fill="both", expand=True)

                    #self.label_udi.config(background="lightblue", foreground="black")
                    self.var_udi.set(_udi)
                    _do_update = True

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

        else:
            # ********** Simulation Profile *************
            while True:
                # sleep(3.0)
                # _card_id = "007"
                # self.ui_queue.put({"card_id_scanned": _card_id})  # FAIL
                # sleep(2.0)
                # _card_id = "00"
                # self.ui_queue.put({"card_id_scanned": _card_id})  # SUCCESS

                sleep(5.0)
                _udi = "1CELL" + get_random_digits_string(12)
                self.ui_queue.put({"udi_scanned": _udi})  # FAIL
                sleep(2.0)
                _udi = "1CELL00000002555"
                self.ui_queue.put({"udi_scanned": _udi})  # SUCCESS


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    # need to initialize logger on load

    print("=== PEEL TEST DIALOG ===")

    _default_scanner_resource = "COM1"
    _default_peeltester_filepath_ = Path(__file__).parent / "sampledata"
    _product_list = ["RRC2020B", "RRC2040B", "RRC2054S", "RRC2040-2S", "RRC2054-2S", "SPINEL"]

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    parser.add_argument("--excelfilepath", action="store", default=_default_peeltester_filepath_, help="Path to search for peel tester output excel files containing UDI in filename.")
    parser.add_argument("--scannerport", action="store", default=_default_scanner_resource, help="Resource string for scanner, which can be IP:PORT or local PORT.")
    parser.add_argument("--simulate_scan", action="store_false", help="Set a product for simulated UDI scan interface.")

    args = parser.parse_args()

    PRODUCTION_MODE = not args.development
    ENABLE_UDI_SCAN = (PRODUCTION_MODE or args.simulate_scan)
    SIMULATE_UDI_SCAN = args.simulate_scan
    EXCELFILES_SEARCH_PATH = Path(args.excelfilepath)

    # test of read function:
    #fn = find_excel_for_udi("1CELL00000002555")
    #forces_df = read_excel_of_peeltester(fn)
    #print(forces_df.dtypes, forces_df.head(20),)

    w = None
    s = None
    try:
        # STEP 1: login operator
        access = 0
        while not access > 0:
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