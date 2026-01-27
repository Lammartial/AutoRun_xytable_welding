from cProfile import label
from typing import List, Tuple
from enum import Enum
import multiprocessing as mp
import itertools
import tkinter as tk
import tkinter.ttk as ttk
import json
import uuid
from fastapi import background
import yaml
from hashlib import md5
from base64 import b64decode, b64encode
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import timezone, datetime
from winsound import PlaySound, SND_FILENAME

from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV
from rrc.dsp.interface import DspInterface, DspInterface_SIMULATION, DSPInterfaceError
# import SQL managing modules
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DatabaseError
from rrc.dbcon import get_protocol_db_connector
from rrc.barcode_scanner import create_barcode_scanner, decode_rrc_udi_label
from pymodbus.exceptions import ModbusException
from pymodbus import version as modbus_version
from rrc.modbus.aws3 import AWS3Modbus, AWS3Modbus_DUMMY

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

getLogger("pymodbus.client", DEBUG)
getLogger("pymodbus.protocol", DEBUG)
getLogger("pymodbus.payload", DEBUG)
getLogger("pymodbus.transaction", DEBUG)
getLogger("pymodbus", DEBUG)


# --------------------------------------------------------------------------- #


PRODUCTION_MODE: int = None # is being overwritten by argument
ENABLE_UDI_SCAN: int = None  # is being overwritten by argument
SIMULATED_DSP_PRODUCT: str = None # is being overwritten by argument
STORE_MEASUREMENTS: str = None # is being overwritten by argument
VERIFICATION_SUPPORT: int = False  # is being overwritten by argument


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


def show_options(wg):
    #wg = e.widget
    s = ttk.Style()
    if wg['style']:
        classe = wg['style']
    else:
        classe = wg.winfo_class()

    print(classe)
    layout = s.layout(classe)

    btnborder = layout[0][1]
    btn_style = s.element_options('Button.border')

    btnfocus = btnborder['children'][0][1]
    btn_style += s.element_options('Button.focus')

    btnpadding = btnfocus['children'][0][1]
    btn_style += s.element_options('Button.padding')

    btnlabel = btnpadding['children'][0][1]
    btn_style += s.element_options('Button.label')

    btn_style = sorted(set(btn_style))

    for o in btn_style:
        print(o, s.lookup('TButton', o))

    print('\n')

#--------------------------------------------------------------------------------------------------

class WindowUI(object):

    def __init__(self, command_queue: mp.JoinableQueue, response_queue: mp.Queue, title: str = "POOR MAN'S SPS"):
        global DEBUG, PRODUCTION_MODE, VERIFICATION_SUPPORT

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        self.q_res = response_queue
        row_itr = itertools.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        self.var_label_position = tk.StringVar(self.root, "")
        self.var_label_program = tk.StringVar(self.root, "")
        self.var_label_program_name = tk.StringVar(self.root, "")
        self.var_label_part_number = tk.StringVar(self.root, "")
        self.var_label_sequence = tk.StringVar(self.root, "")
        self.var_label_sequence_revision = tk.StringVar(self.root, "")
        self.var_label_sequence_length = tk.StringVar(self.root, "")
        self.var_label_resource_str = tk.StringVar(self.root, "")
        self.var_label_udi = tk.StringVar(self.root, "")

        self.root.withdraw()  # hide window
        self.root.title(title)
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "ui" / "robot-icon.ico")
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "ui" / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        style = ttk.Style()
        style.theme_use("alt")

        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        _padall = 8
        _w = 300  # width set manually
        _h = self.root.winfo_screenheight() #480  # height set manually
        # Set a minsize for the window
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        self.root.minsize(_w, int(_h/2))
        #_x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        _x = int(self.root.winfo_screenwidth() - _w - _padall)
        _y = int((self.root.winfo_screenheight() / 2) - (_h / 2))
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")
        #
        # setup widgets
        #
        style.configure("MainFrame.TFrame")  # to change the background color dynamically on whole Window
        self.mainframe = ttk.Frame(self.root, pad=(_padall,_padall,_padall,_padall), takefocus=True, style="MainFrame.TFrame")
        self.mainframe.grid(row=0, column=0, sticky="NESW")
        #self.mainframe.grid_rowconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)


        # Labels

        _colspan = 2
        #_row = next(row_itr)
        label_1 = ttk.Label(self.mainframe,text="PART NUMBER",justify="center", font=("-size", 10))
        label_1.grid(row=next(row_itr), column=0, columnspan=_colspan , ipady=5)
        label_2 = ttk.Label(self.mainframe,
                            textvariable=self.var_label_part_number,
                            justify="center", font=("-size", 16, "-weight", "bold"))
        label_2.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)
        # label_s = ttk.Label(self.mainframe,
        #                     textvariable=self.var_label_sequence,
        #                     justify="center", font=("-size", 10, "-weight", "bold"))
        # label_s.grid(row=next(row_itr), column=0, columnspan=2, ipadx=10, ipady=10)
        if PRODUCTION_MODE:
            self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center",
                                       font=("-size", 14, "-weight", "bold"), background="gray", foreground="black")
            self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=50, sticky="ew")
        else:
            self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center", font=("-size", 12))
            self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5, sticky="ew")

        #_row = next(row_itr)
        label3 = ttk.Label(self.mainframe,text="SEQUENCE POS",justify="center", font=("-size", 10))
        label3.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)
        label4 = ttk.Label(self.mainframe,
                            textvariable=self.var_label_position,
                            justify="center", font=("-size", 20, "-weight", "bold"))
        label4.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)

        label5 = ttk.Label(self.mainframe,text="PROGRAM",justify="center",font=("-size", 18))
        label5.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)
        label6 = ttk.Label(self.mainframe,
            textvariable=self.var_label_program,
            justify="center", font=("-size", 32, "-weight", "bold"))
        label6.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)
        label7 = ttk.Label(self.mainframe,
            textvariable=self.var_label_program_name,
            justify="center", font=("-size", 8, "-weight", "bold"))
        label7.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)

        #print("BUTTON-LAYOUT:", style.layout('TButton'))
        #print("BUTTON-MAP:",    style.map("TButton"))
        #print("BUTTON-LOOKUP:", style.lookup("TButton", "background", state=['pressed']))
        if PRODUCTION_MODE:
            _row = next(row_itr)
            #
            # 'alt' style TButton map = {'highlightcolor': [('alternate', 'black')], 'relief': [('pressed', '!disabled', 'sunken'), ('active', '!disabled', 'raised')]}
            # NOTE: sv-style cannot change background of button, thus we fall back to "alt"
            #
            style.configure('ValWelding.TButton', foreground='blue')
            style.map('ValWelding.TButton', background=[ ("pressed", "lightblue")])
            style.configure('SkipPosition.TButton', background='blue', foreground='white', justify="center")  # "justify" is to center text of button in both lines
            style.map('SkipPosition.TButton', background=[("active","!pressed","steel blue"),('pressed', 'lightblue')])

            self.validation_welding_button = None
            self.skip_position_button = None
            self.is_validation_welding_mode = True

            self.skip_position_button = ttk.Button(self.mainframe, text="VALIDATION WELDING\nNEXT POSITION",  style="SkipPosition.TButton",
                command=lambda: self.q_cmd.put({"move_counter": +1}))
            self.skip_position_button.grid(row=_row, column=0, columnspan=2, ipady=50, ipadx=5, sticky=tk.NSEW)
            self.skip_position_button.grid_remove()

            #print(self.skip_position_button.config())

            self.validation_welding_button = ttk.Button(self.mainframe, text="ACTIVATE VALIDATION WELDING",  style="ValWelding.TButton",
                command=lambda: self.q_cmd.put({"validation_welding": True}))
            self.validation_welding_button.grid(row=_row, column=0, columnspan=2, ipady=50, ipadx=20, sticky=tk.NSEW)

        else:
            self.validation_welding_button = None
            self.skip_position_button = None
            self.is_validation_welding_mode = False

            # Buttons
            _row = next(row_itr)
            #
            # 'alt' style TButton map = {'highlightcolor': [('alternate', 'black')], 'relief': [('pressed', '!disabled', 'sunken'), ('active', '!disabled', 'raised')]}
            #
            style.configure('Forward.TButton', foreground="green")  #, borderwidth=4, focusthickness=3,)
            style.map('SForward.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
            style.configure('SBackward.TButton', foreground="red")
            style.map('SBackward.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
            style.configure('SReset.TButton', foreground="blue", )
            style.map('SReset.TButton', background=[("active","!pressed","white"), ("pressed","lightblue")])

            #print("RESET-BUTTON-LAYOUT:", style.layout('SReset.TButton'))
            #print("RESET-BUTTON-MAP:",    style.map("SReset.TButton"))
            #print("RESET-BUTTON-LOOKUP:", style.lookup("SReset.TButton", "background", state=['pressed']))

            step_back_button = ttk.Button(self.mainframe, text="STEP BACK",  style="SBackward.TButton",
                command=lambda: self.q_cmd.put({"move_counter": -1}))
            step_back_button.grid(row=_row, column=0, ipady=50, ipadx=20, sticky=tk.NSEW)

            step_forward_button = ttk.Button(self.mainframe, text="STEP FORWARD",  style="SForward.TButton",
                command=lambda: self.q_cmd.put({"move_counter": +1}))
            step_forward_button.grid(row=_row, column=1, ipady=50, ipadx=5, sticky=tk.NSEW)

            reset_seq_button = ttk.Button(self.mainframe, text="RESET SEQUENCE", style="SReset.TButton",
                command=lambda: self.q_cmd.put({"reset_counter": 0}))
            reset_seq_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, sticky=tk.NSEW)

        # add verification helper BUTTONS
        if VERIFICATION_SUPPORT:
            _row = next(row_itr)

            style.configure('VForceScanUdi.TButton', foreground="blue")  #, borderwidth=4, focusthickness=3,)
            style.map('VForceScanUdi.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
            style.configure('VForcePass.TButton', foreground="green")  #, borderwidth=4, focusthickness=3,)
            style.map('VForcePass.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
            style.configure('VForceFail.TButton', foreground="red")
            style.map('VForceFail.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])

            vforce_scan_udi_button = ttk.Button(self.mainframe, text="VERIFICATION\nSIM SCAN UDI",  style="VForceScanUdi.TButton",
                command=lambda: self.q_cmd.put({"udi_scanned": self.create_udi_for_scan_simulation()}))
            vforce_scan_udi_button.grid(row=_row, column=0, columnspan=2, ipady=25, ipadx=5, sticky=tk.NSEW)

            _row = next(row_itr)

            vforce_pass_button = ttk.Button(self.mainframe, text="VERIFICATION\nFORCE PASS WELD",  style="VForcePass.TButton",
                command=lambda: self.q_cmd.put({"verification_force_weld": "P"}))
            vforce_pass_button.grid(row=_row, column=0, ipady=25, ipadx=5, sticky=tk.NSEW)

            vforce_fail_button = ttk.Button(self.mainframe, text="VERIFICATION\nFORCE FAIL WELD",  style="VForceFail.TButton",
                command=lambda: self.q_cmd.put({"verification_force_weld": "F"}))
            vforce_fail_button.grid(row=_row, column=1, ipady=25, ipadx=5, sticky=tk.NSEW)

        # Some more information labels
        _row = next(row_itr)
        #label_10 = ttk.Label(self.mainframe, textvariable=self.var_label_sequence, font=("-size", 8))
        #label_10.grid(row=_row, column=0,  ipady=10)
        label_10 = ttk.Label(self.mainframe, anchor=tk.CENTER, textvariable=self.var_label_sequence_length, font=("-size", 8))
        label_10.grid(row=_row, column=0,  ipady=10, sticky="ew")
        label_11 = ttk.Label(self.mainframe, anchor=tk.CENTER, textvariable=self.var_label_sequence_revision, font=("-size", 8))
        label_11.grid(row=_row, column=1, ipady=10, sticky="ew")

        label_12 = ttk.Label(self.mainframe, textvariable=self.var_label_resource_str, font=("-size", 8))
        label_12.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)

        # Sizegrip
        #sizegrip = ttk.Sizegrip(self.root)
        #sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))

        ## Add an information widget.
        #label = ttk.Label(mainframe, text=f'\nWelcome to hello_world*4.py.\n')
        #label.grid(column=0, row=next(row_itr), sticky='w')

        # schedule queue processing callback
        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)

        if not PRODUCTION_MODE:
            reset_seq_button.focus_set()


    def create_udi_for_scan_simulation(self) -> str:
        import string
        import random
        return "0CELLFFF" + ''.join(random.choices(string.digits, k=8))  #''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


    def validation_welding_mode(self, enabled: bool) -> None:
        global PRODUCTION_MODE

        self.is_validation_welding_mode = enabled
        if PRODUCTION_MODE:
            if self.is_validation_welding_mode:
                self.skip_position_button.config(state="normal")
                self.skip_position_button.grid()
                self.validation_welding_button.grid_remove()
            else:
                self.skip_position_button.grid_remove()
                #self.validation_welding_button.config(state="enabled")
                self.validation_welding_button.grid()


    def validation_done(self) -> None:
        if PRODUCTION_MODE:
            self.skip_position_button.config(state="disabled")
            #self.validation_welding_button.config(state="disabled")
            self.root.focus_set()  # removes the focus from the button


    def process_command_queue(self):
        if not self.q_res.empty():
            a = self.q_res.get()
            #print("UI:", a)
            _do_update = False
            _play_soundfile = None
            if a:
                if "resource_str" in a:
                    self.var_label_resource_str.set(a["resource_str"])
                    #print("UI:UPDATE RESOURCE")
                    _do_update = True
                if "revision" in a:
                    self.var_label_sequence_revision.set(f'Rev.: {a["revision"]}')
                    #print("UI:UPDATE REVISION")
                    _do_update = True
                if "part_number" in a:
                    self.var_label_part_number.set(a["part_number"])
                    #print("UI:UPDATE PART NUMBER")
                    _do_update = True
                if "sequence" in a:
                    self.var_label_sequence.set(a["sequence"])
                    self.var_label_sequence_length.set(f'Seq. length: {len(a["sequence"])}')
                    #print("UI:UPDATE SEQUENCE")
                    _do_update = True
                if "position" in a:
                    _txt = a["position"]
                    # !!!
                    # WE show Postion 1-based (!ROBERT)
                    # !!!
                    self.var_label_position.set((_txt + 1) if _txt != -1 else "")
                    #print("UI:UPDATE COUNTER")
                    _do_update = True
                if "program" in a:
                    _txt = a["program"]
                    self.var_label_program.set(_txt if _txt != -1 else "")
                    #print("UI:UPDATE PROGRAM")
                    _do_update = True
                if "program_name" in a:
                    _txt = a["program_name"]
                    self.var_label_program_name.set(_txt if _txt != -1 else "")
                    #print("UI:UPDATE PROGRAM_NAME")
                    _do_update = True
                if "udi" in a:
                    if a["udi"] is None:
                        self.label_udi.config(background="gray", foreground="black")
                        self.var_label_udi.set("PLEASE SCAN UDI")
                        print("UI:RESET UDI")
                    else:
                        self.label_udi.config(background="blue", foreground="white")
                        self.var_label_udi.set(a["udi"])
                    #self.validation_welding_mode(False)
                    _do_update = True
                if "udi_scanned" in a:
                    self.label_udi.config(background="lightblue", foreground="black")
                    self.var_label_udi.set(a["udi_scanned"])
                    print("UI:UPDATE UDI")
                    _do_update = True
                if "udi_rejected" in a:
                    self.label_udi.config(background="orange", foreground="black")
                    self.var_label_udi.set("UDI REJECTED")
                    _play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz")
                    print("UI:REJECTED UDI")
                    _do_update = True
                    pass
                if "udi_not_confirmed" in a:
                    self.label_udi.config(background="orange", foreground="red")
                    self.var_label_udi.set(a["udi_not_confirmed"])
                    print("UI:BLACKLISTED UDI")
                    _do_update = True
                    pass
                if "welding_check" in a:
                    # position of welding
                    _fgcolor = "white"
                    if "passed" in a["welding_check"]:
                        self.label_udi.config(background="LimeGreen", foreground=_fgcolor)
                    else:
                        self.label_udi.config(background="OrangeRed", foreground=_fgcolor)
                        _play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz-hard")
                    self.var_label_udi.set(a["udi"])
                    print("UI:RESULT")
                    _do_update = True
                if "validation_welding" in a:
                    _vw_enabled = a["validation_welding"]
                    self.validation_welding_mode(_vw_enabled)
                if "result" in a:
                    # result overall
                    #self.validation_welding_mode(False)
                    if self.is_validation_welding_mode:
                        self.validation_done()
                    #_fgcolor = "black" if "\n" in a["udi"] else "white"
                    _fgcolor = "black"
                    if "passed" in a["result"]:
                        _bgcolor = "green"
                        if self.is_validation_welding_mode:
                            _bgcolor = "dark slate gray"
                    else:
                        _bgcolor = "red"
                        if self.is_validation_welding_mode:
                            _bgcolor = "violet red"
                    self.label_udi.config(background=_bgcolor, foreground=_fgcolor)
                        #_play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz")
                    self.var_label_udi.set(a["udi"])
                    print("UI:RESULT")
                    _do_update = True
                if "database_error" in a:
                    _er = a["database_error"]["text"]
                    _code = a["database_error"]["code"]  # this is an API-Error code that can be tracked back into the SQLAlchemy code
                    _play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz-hard")
                    self.var_label_udi.set(f"Database Error\n Code: '{_code}'")
                    print(f"UI:DATABASE_ERROR '{_code}'")
                    _do_update = True
            if _do_update:
                self.root.update()
            if _play_soundfile:
                PlaySound(_play_soundfile, SND_FILENAME)
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())


    def run_mainloop(self):
        self.root.mainloop()


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class SPSStates(Enum):
    START = 0
    INIT = 2
    SYNC_ON_MACHINE_COUNTER = 3  # unused
    SYNC_ON_TOGGLE_BIT = 4
    WAIT_MACHINE_READY = 5  # unused
    SHOW_PROGRAM_STEP = 6
    FETCH_NEXT_PROGRAM = 7
    WAIT_READY_TO_SET_PROGRAM = 8  # unused
    SET_PROGRAM_ON_MACHINE = 9
    SEQUENCE_DONE = 10
    CHECK_WELDING_RESULT = 11
    FAILED = 77
    POSITION_PASSED = 87
    PASSED = 88
    STOP = 99

#--------------------------------------------------------------------------------------------------

class SPSStateMachineBase(object):

    def __init__(self, dev: AWS3Modbus | str, program_sequence: List[int] = [1], have_read_measurements: bool = False) -> None:
        self.state: SPSStates = SPSStates.START
        self.program_sequence = program_sequence
        self.sequence_pos = 0
        self.program_no = -1
        self.next_program_no = -1
        self.program_name = None  # this is for human verification purposes
        self.counter_base_ax1 = None
        self.counter_ax1 = None
        self.last_counter_ax1 = -1
        self._throttle_pause = 0.020  # need to be >=20ms according to AWS3 spec
        # Option to read measurements - need to be implemented in the derived classes as needed
        # e.g. the Rotating version does write files, the Production version writes to DB
        self.have_read_measurements = have_read_measurements
        self.welding_status = None
        self.welding_parameters = None
        self.welding_measurements = None
        self.welding_waveforms = None
        # MODBUS communication - either real or DUMMY
        if isinstance(dev, str):
            try:
                self.dev = AWS3Modbus(dev)
                self.dev.open()
                self.dev.setup_device()
                # keep open
            except Exception as ex:
                print(ex)
                print("Using dummy AWS3 Modbus driver for test purposes.")
                self.dev = AWS3Modbus_DUMMY(dev)  # this starts a simulation to support testing
        else:
            self.dev = dev
        #self._machine_locked = self.dev.read_machine_lock_status()
        self._machine_locked = None
        print(f"Poor man's SPS machine: {self.dev.machine_name}, at {repr(self.dev)}")


    def __str__(self) -> str:
        return f"State Machine BASE on modbus {repr(self.dev)} with sequence {self.program_sequence}"

    def __repr__(self) -> str:
        return f"SPSStateMachineBase({repr(self.dev)}, {self.program_sequence})"

    #----------------------------------------------------------------------------------------------

    # to provide the with ... statement protector
    def __enter__(self):
        self.dev.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.dev.close()

    #----------------------------------------------------------------------------------------------

    def is_ready_for_commands(self) -> bool:
        return (self.state not in [SPSStates.START, SPSStates.INIT])


    #----------------------------------------------------------------------------------------------

    def fetch_program_name(self) -> str:

        def _combine_program_name(ax1, ax2) -> str:
            return f"{ax1} {ax2}"

        if self.welding_parameters and "program_name" in self.welding_parameters:
            # we can build the program name from the parameters read
            self.program_name = _combine_program_name(self.welding_parameters["program_name"][1], self.welding_parameters["program_name"][2])
        else:
            # we need to read the program name from the machine
            self.program_name = _combine_program_name(self.dev.read_program_name(1), self.dev.read_program_name(2))

        return self.program_name

    #----------------------------------------------------------------------------------------------


    def set_state(self, new_state: SPSStates) -> None:
        self.state = new_state

    def _offset_sequence(self, offset: int) -> None:
        self.sequence_pos = (self.sequence_pos + offset) % len(self.program_sequence)

    def run_loop(self):
        while True:
            self.do_one_loop()

    def lock_machine(self) -> None:
        try:
            if not self._machine_locked:
                self.dev.lock_machine_step()
                self._machine_locked = self.dev.read_machine_lock_status()
                #self._machine_locked = True
        except ModbusException as ex:
            print(f"SPS-lock: {ex}")
            pass  # ignore

    def unlock_machine(self) -> None:
        try:
            self.dev.unlock_machine_step()
            self._machine_locked = False
        except ModbusException as ex:
            print(f"SPS-unlock: {ex}")
            pass  # ignore


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class _MyBreak(Exception): pass

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class SPSStateMachineRotating(SPSStateMachineBase):

    def __init__(self, dev: AWS3Modbus | str, program_sequence: List[int] = [1], have_read_measurements: bool = False) -> None:
        super().__init__(dev, program_sequence=program_sequence, have_read_measurements=have_read_measurements)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.is_sequence_done = False
        self._debug_trigger_ = False


    def __str__(self) -> str:
        return f"Rotating State Machine for SPS on modbus {repr(self.dev)} with sequence {self.program_sequence}"

    def __repr__(self) -> str:
        return f"SPSStateMachineRotating({repr(self.dev)}, {self.program_sequence})"

    #----------------------------------------------------------------------------------------------

    def move_seqence_step(self, step: int) -> SPSStates:
        if self.sequence_pos + step >= len(self.program_sequence):
            # sequence is done
            # (here in Rotating StateMachine its only a hint but will not block further counting)
            self.is_sequence_done = True
        else:
            self.is_sequence_done = False
        self._offset_sequence(step)
        self.next_program_no = self.program_sequence[self.sequence_pos]
        print(f"Move program step to {self.sequence_pos} with program no {self.next_program_no}")
        self.last_counter_ax1 = self.counter_ax1
        #return SPSStates.WAIT_READY_TO_SET_PROGRAM
        return SPSStates.SET_PROGRAM_ON_MACHINE


    def reset_seqence(self) -> None:
        self.sequence_pos = 0
        self.is_sequence_done = False
        self.next_program_no = self.program_sequence[self.sequence_pos]
        #self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
        self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)


    # --- Rotating loop ---
    def do_one_loop(self):
        try:
            match self.state:

                case SPSStates.START:
                    self.unlock_machine()
                    self.set_state(SPSStates.INIT)

                case SPSStates.INIT:
                    self._machine_locked = self.dev.read_machine_lock_status()
                    self.counter_base_ax1 = self.dev.read_axis_counter(1)
                    self.program_no = self.dev.read_program_no()
                    self.counter_ax1 = self.counter_base_ax1
                    self.last_counter_ax1 = self.counter_ax1
                    print(f"Counters at init: Ax1={self.counter_ax1}")
                    print(f"Program no at init: {self.program_no}")
                    self.next_program_no = self.program_sequence[self.sequence_pos]
                    print(f"Next program on sequence on {self.sequence_pos}: {self.next_program_no}")
                    if self.next_program_no != self.program_no:
                        self.program_no = self.next_program_no  # to avoid blitting a -1 on UI
                    #self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
                    self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)

                case SPSStates.SHOW_PROGRAM_STEP:
                    print(f"Program step: {self.sequence_pos} of {len(self.program_sequence)}")
                    print(f"Program set {self.program_no} {self.program_name}")
                    self.set_state(SPSStates.SYNC_ON_TOGGLE_BIT)

                case SPSStates.SYNC_ON_TOGGLE_BIT:
                    _do_pause = True
                    if self._machine_locked:
                        self.unlock_machine()  # make sure we are not locked here
                    if self.dev.is_toggle_bit_changed():
                        #self.set_state(SPSStates.WAIT_MACHINE_READY)
                        _machine_ready, _status = self.dev.is_machine_ready()
                        self.lock_machine() # lock machine to have control for read measurements
                        self.welding_status = _status  # store result
                        self.counter_ax1 = self.dev.read_axis_counter(1)
                        self.last_counter_ax1 = self.counter_ax1
                        print(f"Counters: Ax1={self.counter_ax1}")
                        self.set_state(SPSStates.CHECK_WELDING_RESULT)
                        _do_pause = False
                    if _do_pause:
                        sleep(self._throttle_pause)  # throttle polling


                case SPSStates.CHECK_WELDING_RESULT:
                    # We do this task here to have quick feedback on UI before the
                    # long task for read the information begins.
                    if self.have_read_measurements:
                        self.lock_machine() # lock machine to have control for read measurements
                        print(f"Read measurements {self.sequence_pos}")
                        # get the machine's measurements if required
                        # and store 'em into protocol database
                        t0 = perf_counter()
                        self.welding_measurements = self.dev.fetch_welding_measurements()
                        print("M1:", perf_counter()-t0)
                        print("Read waveforms")
                        self.welding_waveforms = {
                            1: self.dev.read_waveform_data(1, ("I","U","s3")),  # ??? selectable sets ???
                            2: self.dev.read_waveform_data(2, ("s3"))
                        }
                        print("M2:", perf_counter()-t0)
                    else:
                        # reset to avoid false database storage
                        self.welding_measurements = None
                        self.welding_waveforms = None
                    # switch to indication state, allowing the outer loop to handle the
                    # measurements accordingly
                    #self.unlock_machine()
                    if self.welding_status["ok"] > 0:
                        self.set_state(SPSStates.PASSED)
                    else:
                        if self.welding_status["reject"] > 0:
                            # should we do more here ?
                            pass
                        else:
                            # we got neither a pass nor fail - what's up here ?
                            pass
                        self.set_state(SPSStates.FAILED)

                case SPSStates.PASSED:
                    # This state is to let the outer loop do write the measurement data
                    # for a FAILED position.
                    print(f"PASSED at position {self.sequence_pos}")
                    # Then Get next position's program or PASS on end of sequence
                    self.set_state(SPSStates.FETCH_NEXT_PROGRAM)

                case SPSStates.FAILED:
                    # This state is to let the outer loop do write the measurement data
                    # for a PASS position.
                    print(f"FAILED at position {self.sequence_pos}")
                    # Then Get next position's program or PASS on end of sequence
                    self.set_state(SPSStates.FETCH_NEXT_PROGRAM)

                case SPSStates.FETCH_NEXT_PROGRAM:
                    # yes we have finished a cycle -> move to next program step SET_PROGRAM_ON_MACHINE
                    self.set_state(self.move_seqence_step(+1))

                #case SPSStates.WAIT_READY_TO_SET_PROGRAM:
                #    self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)

                case SPSStates.SET_PROGRAM_ON_MACHINE:
                    #t0 = perf_counter()
                    #self.lock_machine()
                    #print("T0:", perf_counter()-t0)
                    # check if the correct program step is set
                    self.program_no = self.dev.read_program_no()
                    if self.next_program_no != self.program_no:
                        print(f"Set program {self.next_program_no} on machine.")
                        t0 = perf_counter()
                        self.dev.write_program_no(self.next_program_no)
                        print("T1:", perf_counter()-t0)
                        self.program_no = self.dev.read_program_no()
                        print("T2:", perf_counter()-t0)
                        if self.program_no != self.next_program_no:
                            # retry until program is being set
                            # simulate an early break
                            raise _MyBreak(f"PRG_NO: {self.program_no} != {self.next_program_no}")
                    else:
                        print(f"Program {self.program_no} already set.")
                    if 1:
                    #if self.have_read_measurements:
                        # read the parameters of the current program
                        # to be able to write them on "SHOW_PROGRAM" step
                        print("Read parameters")
                        t0 = perf_counter()
                        self.welding_parameters = self.dev.fetch_welding_parameters()
                        print("P1:", perf_counter()-t0)
                    # this uses either the already read parameters or just reads
                    # the program names of both axis while machine is locked:
                    self.fetch_program_name()
                    if self._machine_locked:
                        self.unlock_machine()
                    #print("T3:", perf_counter()-t0)
                    self.set_state(SPSStates.SHOW_PROGRAM_STEP)

                #
                # Note: here we do not have a STOP
                #
                case other:
                    self.set_state(SPSStates.START)

        except _MyBreak as ex:
            self._log.error(f"BREAK: {ex}")
            pass  # simulate break from match
        except ModbusException as ex:
            #print(f"SPS: {ex}")
            self._log.error(f"SPS: {ex}")
            pass  # swallow
        except AssertionError as ex:
            #print(f"SPS ignores: {ex}")
            self._log.error(f"SPS ignores: {ex}")
            pass  # swallow
        except Exception as ex:
            #print(f"SPS complains: {type(ex)}:{ex}")
            self._log.critical(f"SPS complains: {type(ex)}:{ex}")
            #raise
            pass  # swallow
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            if self._machine_locked:
                self.unlock_machine() # verifies the _machine_locked state
            # do not change the state here
            pass



#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class SPSStateMachine(SPSStateMachineBase):
    """This is the "production" state machine.

    Args:
        SPSStateMachineBase (_type_): _description_
    """
    def __init__(self, dev: AWS3Modbus | str, program_sequence: List[int] = [1], have_read_measurements: bool = True) -> None:
        super().__init__(dev, program_sequence=program_sequence, have_read_measurements=have_read_measurements)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)


    def __str__(self) -> str:
        return f"State Machine for SPS on modbus {repr(self.dev)} with sequence {self.program_sequence}"

    def __repr__(self) -> str:
        return f"SPSStateMachine({repr(self.dev)}, {self.program_sequence})"

    #----------------------------------------------------------------------------------------------

    def close(self):
        try:
            self.dev.lock_machine_step()
        except ModbusException as ex:
            print(f"SPS-close: {ex}")
            pass
        super().close()

    #----------------------------------------------------------------------------------------------

    def move_seqence_step(self, step: int) -> SPSStates:
        if self.sequence_pos + step >= len(self.program_sequence):
            # sequence is done, do not proceed by wrap around
            return SPSStates.PASSED
        else:
            self._offset_sequence(step)
            self.next_program_no = self.program_sequence[self.sequence_pos]
            print(f"Move program step to {self.sequence_pos} with program no {self.next_program_no}")
            self.last_counter_ax1 = self.counter_ax1
            # next welding to be prepared
            #return SPSStates.WAIT_READY_TO_SET_PROGRAM
            return SPSStates.SET_PROGRAM_ON_MACHINE


    def reset_seqence(self) -> None:
        self.sequence_pos = 0
        self.next_program_no = self.program_sequence[self.sequence_pos]
        #self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
        self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)


    # --- locked production loop ---
    def do_one_loop(self):
        try:
            match self.state:

                case SPSStates.START: # locked
                    self.lock_machine()
                    self.set_state(SPSStates.INIT)

                case SPSStates.INIT:
                    self._machine_locked = self.dev.read_machine_lock_status()
                    self.counter_base_ax1 = self.dev.read_axis_counter(1)
                    self.program_no = self.dev.read_program_no()
                    self.counter_ax1 = self.counter_base_ax1
                    self.last_counter_ax1 = self.counter_ax1
                    print(f"Counters at init: Ax1={self.counter_ax1}")
                    print(f"Program no at init: {self.program_no}")
                    self.next_program_no = self.program_sequence[self.sequence_pos]
                    print(f"Next program on sequence on {self.sequence_pos}: {self.next_program_no}")
                    if self.next_program_no != self.program_no:
                        self.program_no = self.next_program_no  # to avoid blitting a -1 on UI
                    #self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
                    self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)

                case SPSStates.SHOW_PROGRAM_STEP:
                    print(f"Program step: {self.sequence_pos} of {len(self.program_sequence)}")
                    print(f"Program set {self.program_no} {self.program_name}")
                    #self.set_state(SPSStates.SYNC_ON_MACHINE_COUNTER)
                    self.set_state(SPSStates.SYNC_ON_TOGGLE_BIT)

                case SPSStates.SYNC_ON_TOGGLE_BIT:
                    _do_pause = True
                    if self._machine_locked:
                        self.unlock_machine()  # make sure we are not locked here
                    if self.dev.is_toggle_bit_changed():
                        #self.set_state(SPSStates.WAIT_MACHINE_READY)
                        _machine_ready, _status = self.dev.is_machine_ready()
                        self.lock_machine() # lock machine to have control for read measurements
                        self.welding_status = _status  # store result
                        self.counter_ax1 = self.dev.read_axis_counter(1)
                        self.last_counter_ax1 = self.counter_ax1
                        print(f"Counters: Ax1={self.counter_ax1}")
                        self.set_state(SPSStates.CHECK_WELDING_RESULT)
                        _do_pause = False
                    if _do_pause:
                        sleep(self._throttle_pause)  # throttle polling

                # UNUSED !!!
                case SPSStates.WAIT_MACHINE_READY:
                    _do_pause = True
                    _machine_ready, _status = self.dev.is_machine_ready()
                    if _machine_ready:
                        self.lock_machine() # lock machine to have control for read measurements
                        self.welding_status = _status  # store result
                        self.counter_ax1 = self.dev.read_axis_counter(1)
                        self.last_counter_ax1 = self.counter_ax1
                        print(f"Counters: Ax1={self.counter_ax1}")
                        self.set_state(SPSStates.CHECK_WELDING_RESULT)
                        _do_pause = False
                    if _do_pause:
                        sleep(self._throttle_pause)  # throttle polling


                case SPSStates.CHECK_WELDING_RESULT:
                    # We do this task here to have quick feedback on UI before the
                    # long task for read the information begins.
                    if self.have_read_measurements:
                        print(f"Read measurements of pos.{self.sequence_pos}")
                        # get the machine's measurements if required
                        # and store 'em into protocol database
                        self.welding_measurements = self.dev.fetch_welding_measurements()
                        self.welding_waveforms = None
                    else:
                        # reset to avoid false database storage
                        self.welding_measurements = None
                        self.welding_waveforms = None
                    # switch to indication state, allowing the outer loop to handle the
                    # measurements accordingly
                    if self.welding_status["ok"] > 0:
                        # we do NOT read waveforms as it takes too long
                        self.set_state(SPSStates.POSITION_PASSED)
                    else:
                        if self.welding_status["reject"] > 0:
                            # should we do more here ?
                            pass
                        else:
                            # we got neither a pass nor fail - what's up here ?
                            pass
                        if self.have_read_measurements:
                            # we do read waveforms only on FAILED welding position in production mode
                            print("Read waveforms")
                            self.welding_waveforms = {
                                1: self.dev.read_waveform_data(1, ("I","U","s3")),  # ??? selectable sets ???
                                2: self.dev.read_waveform_data(2, ("s3"))
                            }
                        self.set_state(SPSStates.FAILED)

                case SPSStates.POSITION_PASSED:
                    # This state is to let the outer loop do write the measurement data
                    # for a PASS position.
                    # MEASUREMENT DATA VALID
                    # Then Get next position's program or PASS on end of sequence
                    self.set_state(SPSStates.FETCH_NEXT_PROGRAM)

                case SPSStates.FAILED:
                    # This state is to let the outer loop react on FAILED
                    # MEASUREMENT DATA VALID
                    print(f"FAILED at position {self.sequence_pos}")
                    self.set_state(SPSStates.STOP)

                case SPSStates.FETCH_NEXT_PROGRAM:
                    # yes we have finished a cycle -> move to next program step
                    self.set_state(self.move_seqence_step(+1))
                    # next is either PASSED or SET_PROGRAM_ON_MACHINE

                case SPSStates.PASSED:
                    print(f"Sequence PASSED")
                    self.set_state(SPSStates.STOP)

                #case SPSStates.WAIT_READY_TO_SET_PROGRAM:
                #    self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)

                case SPSStates.SET_PROGRAM_ON_MACHINE:
                    #self.lock_machine()
                    # check if the correct program step is set
                    self.program_no = self.dev.read_program_no()
                    if self.next_program_no != self.program_no:
                        print(f"Set program {self.next_program_no} on machine.")
                        self.dev.write_program_no(self.next_program_no)
                        #sleep(self._throttle_pause)  # throttle polling
                        self.program_no = self.dev.read_program_no()
                        if self.program_no != self.next_program_no:
                            # retry until program is being set
                            # simulate an early break
                            sleep(self._throttle_pause)  # throttle polling
                            raise _MyBreak(f"PRG_NO: {self.program_no} != {self.next_program_no}")
                    else:
                        #self.welding_parameters = None  # signal not to store ths set again
                        print(f"Program {self.program_no} already set.")
                    if 1:
                    #if self.have_read_measurements:
                        # read the parameters of the current program
                        # to be able to write them on "SHOW_PROGRAM" step
                        print("Read parameters")
                        self.welding_parameters = self.dev.fetch_welding_parameters()
                    # this uses either the already read parameters or just reads
                    # the program names of both axis while machine is locked:
                    self.fetch_program_name()
                    if self._machine_locked:
                        self.unlock_machine()
                    sleep(self._throttle_pause)  # throttle polling
                    self.set_state(SPSStates.SHOW_PROGRAM_STEP)

                case SPSStates.STOP:
                    self.lock_machine()  # Note: issues a MODBUS only if not locked
                    sleep(self._throttle_pause)  # throttle polling

                case other:
                    self.set_state(SPSStates.START)

        except _MyBreak as ex:
            pass  # simulate break from match
        except ModbusException as ex:
            #print(f"SPS: {ex}")
            self._log.error(f"SPS: {ex}")
            pass  # swallow
        except AssertionError as ex:
            #print(f"SPS ignores: {ex}")
            self._log.error(f"SPS ignores: {ex}")
            pass  # swallow
        except Exception as ex:
            #print(f"SPS complains: {type(ex)}:{ex}")
            self._log.critical(f"SPS complains: {type(ex)}:{ex}")
            #raise
            pass  # swallow
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            # do not change the state here
            pass


#--------------------------------------------------------------------------------------------------
# *** SPS ***
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


def _create_interfaces(simulation: None | str = None) -> Tuple[StationConfiguration, DspInterface]:
    """Creates the interfaces for configuration and DSP.

    Note: this is called from process context,
            do NOT call it from anywhere else except you want to test this function only!

    Returns:
        Tuple[StationConfiguration, DspInterface]: _description_
    """
    global DEBUG
    _log = getLogger(__name__, DEBUG)

    # 1. we need the station config
    try:
        cfg = StationConfiguration("CELL_WELDING") #, filename=CONF_FILENAME_DEV)
    except FileNotFoundError:
        # comfort for testing: using the development configuration
        cfg = StationConfiguration("CELL_WELDING", filename=CONF_FILENAME_DEV)
        _log.info(f"USING DEVELOPMENT CONFIGURATION {CONF_FILENAME_DEV}")
    _, __, _dsp_api_base_url, _, _ = cfg.get_station_configuration()
    # 2. we can create the DSP interface
    if simulation:
        _log.info(f"Use simulation for DSP interface configured {simulation}")
        dsp = DspInterface_SIMULATION(simulation, None)
    else:
        dsp = DspInterface(_dsp_api_base_url, None)
    return cfg, dsp



class ProcessSPS(mp.Process):

    def __init__(self, command_queue: mp.JoinableQueue, response_queue: mp.Queue) -> None:
        mp.Process.__init__(self)
        global DEBUG, ENABLE_UDI_SCAN, PRODUCTION_MODE, SIMULATED_DSP_PRODUCT, STORE_MEASUREMENTS, SCAN_UDI_FORCE_RESTART, VERIFICATION_SUPPORT

        self._log = getLogger(__name__, DEBUG)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.enable_udi_scan = ENABLE_UDI_SCAN
        self.simulated_dsp_product = SIMULATED_DSP_PRODUCT
        self.have_read_measurements = True if STORE_MEASUREMENTS is not None else False
        self.measurements_filepath = Path(STORE_MEASUREMENTS) if STORE_MEASUREMENTS is not None else None
        self.production_mode = PRODUCTION_MODE
        self.scan_udi_force_restart = SCAN_UDI_FORCE_RESTART
        self.welding_for_process_validation = False  # setting this to True hinders the SPS to transmit the result to MES service
        self.verification_support = VERIFICATION_SUPPORT

    def collect_parameters(self, cfg: StationConfiguration, dsp: DspInterface) -> Tuple[List[int], str, str, str]:
        """ Read configuration from DSP + DB connection

        Note: this is called from process context,
              do NOT call it from anywhere else except you want to test this function only!

        Raises:
            Exception: _description_
        """

        # 1. we need the station config
        _, _station_id, _dsp_api_base_url, _line_id, _ = cfg.get_station_configuration()
        # 2. with station config we can request the part number from DSP
        print("Fetching part number from DSP...")
        _dsp_info = dsp.get_parameter_for_testrun("CELL_WELDING", _station_id, _line_id, "0")
        #_dsp_info = dsp.get_parameter_for_welding(_station_id, _line_id)
        _part_number = _dsp_info["part_number"]
        _sequence_revision = _dsp_info["test_program_id"]
        # 3. with station config we can get the IP resource for the welder MODBUS
        _resources = cfg.get_resource_strings_for_socket(0)
        _controller_resource_str = _resources[0]
        print(f"PART NUMBER: {_part_number}")
        # 4. we need the program sequence of the AWS welder for the given part number
        print("Requesting database for sequence...")
        # 3. create the database interface (recreate it here as the connecton could time-out otherwise)
        engine, session_maker = get_protocol_db_connector()
        with session_maker() as session:
            response = session.execute(text(
                    f"SELECT revision,program_sequence,parameter FROM `spsconfig` AS sc "+\
                    f"  WHERE sc.part_number={_esc(_part_number)} "+\
                    f"  AND sc.revision={_esc(_sequence_revision)}"
                    #f"  ORDER BY revision DESC"
                    ))
            rows = response.fetchall()
        if len(rows) == 0:
            # not found! -> do not proceed
            raise Exception(f"No Data in Database for part {_part_number} found, cannot proceed!")
        print(f"Got record: {rows[0]}")
        return [int(i) for i in rows[0][1].split(",")], str(rows[0][0]), _controller_resource_str, _part_number, session_maker, _line_id, _station_id


    def run(self) -> None:
        """
        This is the process context in which we run the SPS.
        Create all relevant objects from here!
        """

        #global DEBUG
        #_log = getLogger(__file__, DEBUG)
        # getLogger("pymodbus.client.*", 2)
        # getLogger("pymodbus.protocol.*", 2)
        # getLogger("pymodbus.payload.*", 2)
        # getLogger("pymodbus.transaction.*", 2)
        # getLogger("pymodbus.*", 2)

        #------------------------------------------------------------------------------------------

        def store_db(udi: str, part_number: str, line_id: int, station_id: str, SM: SPSStateMachine, db_session_maker: Session) -> None:

            print("STORE DB")
            _result = "P" if SM.welding_status["ok"]>0 else ("F" if SM.welding_status["reject"]>0 else "A")  # Pass, Fail, Abort
            _counter = SM.counter_ax1
            _udi = udi if udi else "undefined"  # database uses UDI as prim key -> not null
            __retries_db__ = 3
            while __retries_db__ > 0:
                __retries_db__ -= 1
                try:
                    with db_session_maker() as session:
                        if SM.welding_parameters:
                            # store a new parameter-set; linked by a hash over the set which keeps it unique
                            #_device_name = SM.welding_parameters["name"]
                            _device_name = SM.dev.get_identification_str()
                            _wp_str = json.dumps({
                                "device_name": _device_name,
                                # we include the device name consisting of IP name@address into the hash calculation to
                                #  a) distinct between different machines
                                #  b) have reference to the execting machine in data
                                **SM.welding_parameters}, sort_keys=True, ensure_ascii=True)  # create a JSON to store in db and generate a HASH
                            _hash_params = get_hash(_wp_str).decode(encoding="utf-8", errors="strict")
                            _program_no = SM.welding_parameters["parameters"]["ProgramNumber"]
                            _attr = (("hash",_hash_params), ("device_name",_device_name), ("program_no",_program_no), ("parameters",_wp_str))
                            _vstr = esc_values(_attr)
                            _updstr = esc_values(_attr[1:])
                            _sql = text(f"INSERT INTO `welding_parameters` SET {_vstr} ON DUPLICATE KEY UPDATE {_updstr}")
                            response = session.execute(_sql)
                        else:
                            _hash_params = None
                        if SM.welding_waveforms:
                            # Store waveforms. linked by (udi,counter) index to "measurements" table
                            _ww_str = json.dumps(SM.welding_waveforms)
                            _vstr = esc_values((("udi", _udi), ("counter", _counter), ("waveforms", _ww_str)))
                            _sql = text(f"INSERT INTO `welding_waveforms` SET {_vstr}")
                            response = session.execute(_sql)
                        # always store the measurement data; (udi,counter) is primary key
                        _seq_pos = SM.sequence_pos
                        _wm_str = json.dumps(SM.welding_measurements)
                        _vstr = esc_values((("udi", _udi), ("counter", _counter), ("position", _seq_pos), ("part_number", part_number),
                                        ("line_id", line_id), ("station_id", station_id), ("result", _result),
                                        ("ref_parameter", _hash_params), ("measurements", _wm_str)))
                        _sql = text(f"INSERT INTO `welding_measurements` SET {_vstr}")
                        response = session.execute(_sql)
                        session.commit()
                        print("Measurements stored successfully.")
                        break  # DONE
                except DatabaseError as dex:
                    self.response_queue.put({"database_error": { "text": str(dex), "code": dex.code } })
                    print(f"Database Error: {dex}.")
                    sleep(1.05)  # so we can wait in sum to the next second to generate a new and unique key in
                                 # measurements, if this was the root cause of the error (see error code in display)
                    print(f"Retries left: {__retries_db__}.")
                    continue  # try again


        #------------------------------------------------------------------------------------------

        def store_file(udi: str, part_number: str, line_id: int, station_id: str, SM: SPSStateMachine, fp_pattern: Path = "aws_readings"):
            print("SAVE FILES")
            _counter = SM.counter_ax1
            _device_name = SM.dev.get_identification_str()
            try:
                with open(fp_pattern.parent /  f"{fp_pattern.name}_measurements_{line_id}_{station_id}_{_counter}.yaml", "wt") as file:
                    file.write(yaml.dump({
                        "counter": _counter,
                        "position": SM.sequence_pos,
                        "status": SM.welding_status,
                        **SM.welding_measurements
                        },
                        Dumper=yaml.Dumper))
            except Exception as ex:
                print(ex) # swallow
                print("Measurements:", SM.welding_measurements)

            try:
                with open(fp_pattern.parent /  f"{fp_pattern.name}_waveforms_{line_id}_{station_id}_{_counter}.yaml", "wt") as file:
                    file.write(yaml.dump({
                        "counter": _counter,
                        "status": SM.welding_status,
                        **SM.welding_waveforms
                        },
                        Dumper=yaml.Dumper))
            except Exception as ex:
                print(ex) # swallow
                print("Waveforms:", SM.welding_waveforms)

            try:
                with open(fp_pattern.parent /  f"{fp_pattern.name}_parameters_{line_id}_{station_id}_{_counter}.yaml", "wt") as file:
                    file.write(yaml.dump({
                        "counter": _counter,
                        "status": SM.welding_status,
                        "device_name": _device_name,
                        **SM.welding_parameters
                        },
                        Dumper=yaml.Dumper))
            except Exception as ex:
                print(ex) # swallow
                print("Parameters:", SM.welding_parameters)

        #------------------------------------------------------------------------------------------

        # we need to keep the _dsp interface for UDI presentation and result transmission
        _cfg, _dsp = _create_interfaces(self.simulated_dsp_product)

        SM = None
        proc_name: str = self.name
        n = 0
        _start_datetime: str = ""
        _execution_start: float = 0
        _udi: str = None
        _store_to_db = False
        _store_to_file = False
        try:
            while True:
                if SM is None:
                    _start_datetime = datetime.utcnow().isoformat()
                    _execution_start = perf_counter()  # we use _execution_time as start timestamp
                    # need to create a new State Machine to work with
                    # get configuration from DSP + DB connection
                    program_sequence, sequence_revision, resource_str, part_number, db_session_maker, line_id, station_id = self.collect_parameters(_cfg, _dsp)
                    print("Create new SPS state machine")
                    if self.verification_support:
                        print("VERIFICATION SUPPORT ENABLED!")
                    if self.production_mode: # and (not self.welding_for_process_validation):
                        # production version must be started by UDI scan
                        # and can run only once
                        self.have_read_measurements = True  # overrides the command line parameter
                        SM = SPSStateMachine(
                            resource_str,
                            program_sequence,
                            have_read_measurements=self.have_read_measurements,
                        )
                        _store_to_db = True  # overrides the command line parameter
                        #_store_to_file = self.have_read_measurements  # depending on the command line
                    else:
                        # we use a development state-machine here
                        SM = SPSStateMachineRotating(
                            resource_str,
                            program_sequence,
                            have_read_measurements=self.have_read_measurements,
                        )
                        #_store_to_db = True  # DEBUG
                        _store_to_db = self.welding_for_process_validation
                        _store_to_file = self.have_read_measurements  # depending on the command line

                    print(f"STATE-MACHINE: {repr(SM)}")
                    # let the UI show the correct data
                    self.response_queue.put({
                        # global infos
                        "resource_str": SM.dev.get_identification_str(),  # only to inform user about the connected welder
                        "part_number": part_number,
                        "sequence": program_sequence,
                        "revision": sequence_revision,
                        # infos about the current sequence
                        "position": SM.sequence_pos,
                        "program": SM.next_program_no,
                        "udi": _udi,
                    })

                # execute the state-machine if configured
                SM.do_one_loop()

                if _udi is None and self.enable_udi_scan:
                    SM.lock_machine()
                    #SM.set_state(SPSStates.LOCK_MACHINE)

                # check actions depending on state
                match SM.state:
                    case SPSStates.CHECK_WELDING_RESULT:
                        # KNAUP!
                        if SM.welding_status["reject"] > 0:
                            # update UI (red) while read waveforms taking a lot of time
                            self.response_queue.put({"welding_check": "failed", "udi": _udi})
                        if SM.welding_status["ok"] > 0:
                            # update UI (green) while read waveforms taking a lot of time
                            self.response_queue.put({"welding_check": "passed", "udi": _udi})
                    case SPSStates.FAILED:
                        # complete sequence has failed
                        if _udi:
                            if not self.welding_for_process_validation:
                                print("Sending FAILED result to MES")
                                _dsp.ts_send_result_for_testrun("failed", _start_datetime, perf_counter() - _execution_start, _udi, None)
                            else:
                                print("Validation mode enabled: do NOT send FAIL result to MES.")
                        else:
                            print("WARNING: UDI is None and we will update the DB now.")
                        print("POSITION (PART) FAILED:")
                        if _store_to_db:
                            print("Store measurements into DB.")
                            store_db(_udi, part_number, line_id, station_id, SM, db_session_maker)
                        if _store_to_file:
                            print("Store measurements to file.")
                            store_file(None, part_number, line_id, station_id, SM, fp_pattern=self.measurements_filepath)
                        self.response_queue.put({"result": "failed", "udi": f"{_udi}\nSCAN NEXT UDI"})  # update UI (red)
                        self.welding_for_process_validation = False  # need to reset validation welding after finished all positions or having a failed position in between
                        _udi = None  # finished
                    case SPSStates.POSITION_PASSED:
                        # only to store a passed welding position's measurement
                        print("WELD POSITION PASSED:")
                        if _store_to_db:
                            store_db(_udi, part_number, line_id, station_id, SM, db_session_maker)
                        if _store_to_file:
                            store_file(None, part_number, line_id, station_id, SM, fp_pattern=self.measurements_filepath)
                    case SPSStates.PASSED:
                        if _udi:
                            if not self.welding_for_process_validation:
                                # the validation welding mode disables the result to MES sending
                                # which avoids having this part counted as "scrap" in our statistics
                                print("Sending FAILED result to MES")
                                _dsp.ts_send_result_for_testrun("passed", _start_datetime, perf_counter() - _execution_start, _udi, None)
                            else:
                                print("Validation mode enabled: do NOT send PASS result to MES.")
                        else:
                            print("WARNING: UDI is None and we will update the DB now.")
                        print("PART PASSED:")
                        #if _store_to_db:
                        #    store_db(_udi, part_number, line_id, station_id, SM, db_session_maker)
                        if _store_to_file:
                            store_file(None, part_number, line_id, station_id, SM, fp_pattern=self.measurements_filepath)
                        print("Done.")
                        self.response_queue.put({"result": "passed", "udi": f"{_udi}\nSCAN NEXT UDI" })  # update UI (green)
                        self.welding_for_process_validation = False  # need to reset validation welding after finished all positions
                        _udi = None  # finished
                    case SPSStates.SET_PROGRAM_ON_MACHINE:
                        self.response_queue.put({"position": SM.sequence_pos, "program": SM.next_program_no, "program_name": ""})  # update UI
                    case SPSStates.SHOW_PROGRAM_STEP:
                        self.response_queue.put({"position": SM.sequence_pos, "program": SM.program_no, "program_name": SM.program_name})  # update UI
                        # Note: could also be used to store the parameter set to database

                    # execute the state-machine
                    #SM.do_one_loop()

                # check for incomming commands
                if not self.command_queue.empty():
                    answer = None
                    cmd = self.command_queue.get()
                    if cmd is None:
                        # Poison pill means shutdown
                        print(f"{proc_name}: Exiting")
                        if _udi:
                            # inform the DSP that the process has been aborted
                            _dsp.ts_send_result_for_testrun("aborted", _start_datetime, perf_counter() - _execution_start, _udi, None)
                        if SM:
                            SM.close()
                            SM = None
                        self.command_queue.task_done()
                        break  # terminate this loop -> end task and show termination message
                    if not SM.is_ready_for_commands():
                        continue
                    print(f"{proc_name}: {cmd}")
                    if "udi_scanned" in cmd:
                        # check if we are NOT in the middle of a sequence or at start position:
                        if (_udi is None) or (SM.sequence_pos == 0) or self.scan_udi_force_restart:
                            # forward the UDI to the UI
                            _verify_udi = cmd["udi_scanned"]
                            if "CELL" in _verify_udi:  # this is double check as the scans are qualified in the scan process right now
                                _udi = _verify_udi
                                self.welding_for_process_validation = False  # VALIDATION is stopped on any UDI scan
                                self.response_queue.put({"validation_welding": False})  # clear UI
                                self.response_queue.put({"udi_scanned": _udi})
                                ok, _response = _dsp.send_udi_upfront(_udi)
                                if ok:
                                    # need to reset the sequence
                                    answer = "OK"
                                else:
                                    # udi is not accepted and we are at a situation to allow a restart -> clear _udi
                                    _udi = None
                                    self.response_queue.put({"udi_not_confirmed": "MES rejects UDI"})
                                    print(f"Response from MES: {_response}")
                                    answer = "NOT OK"
                                # let the SM be reconstructed to catch a change in sequence and/or part number
                                SM.close()
                                SM = None
                            else:
                                # false UDI -> popup ?
                                self.response_queue.put({"udi_rejected": _udi})
                                if SM is None:
                                    _udi = None  # the SM was not created, we keep _udi cleared
                                else:
                                    # do NOT modify the _udi as it could be a scrap scan after a good one
                                    pass
                                answer = "NOT OK"
                        else:
                            # we are in the middle of a sequence -> do not accept a UDI scan
                            answer = "NOT OK"
                    if "move_counter" in cmd:
                        if self.enable_udi_scan:
                            if _udi:
                                SM.set_state(SM.move_seqence_step(int(cmd["move_counter"])))
                            answer = "OK"
                        else:
                            # no UDI control
                            SM._debug_trigger_ = True
                            SM.set_state(SM.move_seqence_step(int(cmd["move_counter"])))
                            answer = "OK"
                    if "reset_counter" in cmd:
                        #SM.reset_seqence()
                        SM.close()
                        SM = None  # let the SM be reconstructed to catch a change in sequence and/or part number
                        answer = "OK"
                    if "validation_welding" in cmd:
                        self.welding_for_process_validation = cmd["validation_welding"]
                        self.response_queue.put(cmd) # forward to UI
                        answer = "OK"
                    if "verification_force_weld" in cmd:
                        _forced_result = cmd["verification_force_weld"]
                        if _udi:
                            SM.dev.verification_support_force_weld(_forced_result)
                        answer = "OK"

                    self.command_queue.task_done()
                    if not answer:
                        answer = f"NOT OK: UNKNOWN MESSAGE"
                        print(answer)
                    self.response_queue.put(answer)
        except DSPInterfaceError as e:
            _log.error(str(e))
            self.response_queue.put({"udi_not_confirmed": str(e).replace(",","\n").replace(":","\n")})

        print(f"Process {self.name} has termiated.")
        return


#--------------------------------------------------------------------------------------------------
# *** SCANNER ***
#
class ProcessScanner(mp.Process):

    def __init__(self, sps_queue: mp.Queue, ui_queue: mp.Queue) -> None:
        mp.Process.__init__(self)
        global DEBUG, SIMULATE_UDI_SCAN
        self._log = getLogger(__name__, DEBUG)
        self.sps_queue = sps_queue
        self.ui_queue = ui_queue
        self.simulate_scan = SIMULATE_UDI_SCAN

    def run(self) -> None:
        """
        This is the process context in which we run the scanner.
        Create all relevant objects from here!
        """

        proc_name = self.name
        _cfg, _dsp = _create_interfaces()
        resources = _cfg.get_resource_strings_for_socket(0) # get list of resources
        resource_str = resources[1]  # pick 2nd resource (need to be the scanner!)
        scanner = None
        _retry_timeout = 1
        if not self.simulate_scan:
            while True:
                _udi = None
                try:
                    if not scanner:
                        scanner = create_barcode_scanner(resource_str)
                    _udi = scanner.request(None, timeout=None).strip()
                    _retry_timeout = 1
                except TimeoutError:
                    pass  # this is ok to keep the loop running
                except Exception as ex:
                    # this is a real failure to stop this process
                    print(f"Cannot connect scanner {resource_str}: {ex}")
                    print(f"Trying to reconnect scanner.")
                    scanner = None
                    sleep(_retry_timeout)  # give a bit until reconnect
                    _retry_timeout = min(2*_retry_timeout, 30)  # fibonacci
                    #print(f"{proc_name}:End")
                    #return
                if _udi:
                    # add a precheck if the UDI is a correct one before we send to the SPS
                    # as this is a separate process, the workload is removed from SPS
                    res, raw = decode_rrc_udi_label(_udi, pcba_and_cell_udi_tuple=False)
                    if "CELL" in res:
                        msg = {"udi_scanned": _udi}
                        #self.ui_queue.put(msg)  # this goes to the UI process
                        self.sps_queue.put(msg)   # this goes to the SPS process
                    else:
                        # we got a scrap UDI
                        print(f"Wrong UDI scanned {_udi}. UDI is being rejected.")
                        # we can try to inject a UI update which is accompanied with a sound,
                        # but this costs SPS process time in the UI update task...
                        self.ui_queue.put({"udi_rejected": _udi})
        else:
            # ********** Simulation Profile *************
            #while True:
            sleep(5.0)
            _udi = "1CELL" + get_random_digits_string(12)
            self.sps_queue.put({"udi_scanned": _udi})
            sleep(3.0)
                # add some steps
            #    for n in range(6):
            #        sleep(1.0)
            #        self.sps_queue.put({"move_counter": 1})

#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # need to initialize logger on load

    print("=== POOR MAN's SPS ===")
    print(modbus_version)

    #_default_yaml_filepath_ = Path(__file__).parent / "aws_readings"
    _default_yaml_filepath_ = Path(__file__).parent / "../.." / "logs" / "aws_readings"
    _product_list = ["RRC2020B", "RRC2040B", "RRC2054S", "RRC2040-2S", "RRC2054-2S", "SPINEL"]

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    parser.add_argument("--product", choices=_product_list, action="store", default=None, help="Set a product for simulated DSP interface.")
    parser.add_argument("--store", action="store_true", help="Enable read and store of measurements. If development (no UDI), data is store to YAML files.")
    parser.add_argument("--filepath", action="store", default=_default_yaml_filepath_, help="Path and filename prefix for file stored measurements")
    parser.add_argument("--simulate_scan", action="store_true", help="Set a product for simulated UDI scan interface.")
    parser.add_argument("--block_scan_udi", action="store_false", help="To block scan UDI in the middle of a sequence. If false scanning UDI at any time resets sequence to start.")
    parser.add_argument("--verification", action="store_true", help="To support verification of SPS by providing buttons to force a PASS or FAIL weld.")


    args = parser.parse_args()

    VERIFICATION_SUPPORT = 1 if args.verification else 0
    PRODUCTION_MODE = not args.development
    ENABLE_UDI_SCAN = (PRODUCTION_MODE or args.simulate_scan) and not VERIFICATION_SUPPORT
    SIMULATE_UDI_SCAN = args.simulate_scan
    SIMULATED_DSP_PRODUCT = args.product
    STORE_MEASUREMENTS = args.filepath if args.store else None
    SCAN_UDI_FORCE_RESTART = not args.block_scan_udi


    p = None
    w = None
    s = None
    try:
        # Establish communication queues
        q_cmd = mp.JoinableQueue()
        q_res = mp.Queue()
        # start sub-process for SPS
        p = ProcessSPS(q_cmd, q_res)
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, q_res)
        if ENABLE_UDI_SCAN:
            # start sub-process for scanner
            s = ProcessScanner(q_cmd, q_res)
            s.start()
        p.start()
        w.run_mainloop()
    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        if s and s.is_alive():
            s.terminate()
            s.join(timeout=0.5)  # short process ...
        if p and p.is_alive():
            # Add a poison pill for SPS process
            q_cmd.put(None)
            # Wait for SPS process to finish smoothly
            q_cmd.join()

# END OF FILE