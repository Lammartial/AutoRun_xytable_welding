"""
PCBA Programming Dialog for up to 8 channels programming at the same time.
"""
from cProfile import label
from typing import Dict, List, Any, Tuple
from enum import Enum
import multiprocessing as mp
import itertools
import tkinter as tk
import tkinter.ttk as ttk
import json
from fastapi import background
import yaml
from hashlib import md5
from base64 import b64decode, b64encode
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import timezone, datetime
from winsound import PlaySound, SND_FILENAME

from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets.bq import ChipsetTexasInstruments
from rrc.chipsets.bq40z50 import BQ40Z50R1, BQ40Z50R2

from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV
from rrc.ui.progress_bar import center as center_of_window
from rrc.chipsets.bq_flasher import BQStudioFileFlasher

# import SQL managing modules
from sqlalchemy import text
from sqlalchemy.orm import Session
from rrc.dbcon import get_protocol_db_connector

# multi tasking
import asyncio
from concurrent.futures import Future
from pebble import asynchronous, concurrent, sighandler


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init

logger_init(filename_base=None)
_log = getLogger(__name__, DEBUG)

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

# define the programmer's resource strings including ports
# each line is reflected to a line in the dialog
PROGRAMMERS = [
    "172.25.101.7:2101",
    "172.25.101.8:2101",
    "172.25.101.9:2101",
    # ... add more if needed ...
]

# --------------------------------------------------------------------------- #

# define our products and the correct flash filename
PRODUCT_LIST = {
    "411828": {
        "name": "RRC2020B_PCBA",
        "chipset": "BQ40Z50R1",
        "firmware_file": "SCD_3412031-04_A_Rubin-B_RRC2020B.bq.fs",
        "checksum": None,
    },
    "411829": {
        "name": "RRC2040B_PCBA",
        "chipset": "BQ40Z50R1",
        "firmware_file": "SCD_3412036-02_B_Tansanit-B_RRC2040B.bq.fs",
        "checksum": None,
    },
    "412101": {
        "name": "RRC2040-2S_PCBA",
        "chipset": "BQ40Z50R1",
        "firmware_file": "BQFS_3411842-05_B_Ametrie_RRC2040-2S.bq.fs",
        "checksum": ("61D3", "5366"),   # as hexlify value
    },
}

# --------------------------------------------------------------------------------------------------

FIRMWARE_FP = Path(__file__).parent / "../.." / "Battery-PCBA-Test/filestore"  # path of firmware files
PRODUCT_CHOICES = [k for k in PRODUCT_LIST.keys()]  # this is the list of part numbers to select by command line
SIMULATE_PROGRAMMING: bool = False
PRODUCTION_MODE: bool = True
AUTOSTART_PROGRAMMING: bool = False

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class EmbeddedProgressBar():

    def __init__(self, ref_pg: ttk.Progressbar, root: tk.Tk) -> None:
        self.root = root
        self.progress = ref_pg
        self.hidden = 0
        self._value = None

    def hide(self) -> None:
        #self.root.withdraw()  # hide window
        self.hidden = 1
        pass

    def show(self) -> None:
        # if self.hidden > 0:
        #     self.root.deiconify()
        #     self.hidden -= 1
        self.root.update()
        #self.progress.update()
        pass

    def set_value_threshold(self, value: float, step_threshold: float = 5/100) -> None:
        if ((value - self._value) > step_threshold) or (value >= self._value) or (value == 0):
            self._value = value
            self.progress.config(value=value)
            self.update()


    def set_value(self, value: float) -> None:
        self._value = value
        self.progress.config(value=value)
        self.update()


    def update(self) -> None:
        self.root.update()
        self.root.update_idletasks()
        #self.update()
        pass

    def quit(self) -> None:
        #self.root.quit()
        #for widget in self.root.winfo_children():
        #    widget.destroy()
        self.hide()
        pass

    def close(self) -> None:
        #self.root.destroy()
        self.hide()
        pass

#--------------------------------------------------------------------------------------------------

PG_COLOR_PROCESS = "blue"
PG_COLOR_PASS = "green"
PG_COLOR_FAIL = "red"

class MultiBQStudioFileFlasher(BQStudioFileFlasher):

    def __init__(self, resource_str: str, socket: int, chipset: str = "BQ40Z50R1",  simulate_programming: bool = False) -> None:
        bat = None
        if not simulate_programming:
            # create the interface
            i2cbus = I2CPort(resource_str)
            smbus = BusMaster(i2cbus, retry_limit=1, verify_rounds=3, pause_us=50)
            if chipset == "BQ40Z50R1":
                bat = BQ40Z50R1(smbus)
        super().__init__(bat,
                         color="black",   # should never been shown as firmware file is missing
                         firmware_file=None,  # we provide the firmware file later together with the progress bar
                         show_progressbar=False)  # we provide a different progress bar
        self.simulate_programming: bool = simulate_programming
        self.socket: int = socket
        self.count: int = 0
        self.count_pass: int = 0
        self.count_fail: int = 0
        # internals
        self._pcba_connected_counter: int = 0
        self._PCBA_MAX_COUNTER = 50


    def set_pcba_connected(self):
        self._pcba_connected_counter = self._PCBA_MAX_COUNTER


    def check_if_pcba_connected(self) -> bool:
        
        if self.battery.isReady():
            self._pcba_connected_counter += 1
            if self._pcba_connected_counter > self._PCBA_MAX_COUNTER:
                self._pcba_connected_counter = self._PCBA_MAX_COUNTER
        else:
            self._pcba_connected_counter -= 1
            if self._pcba_connected_counter < 0:
                self._pcba_connected_counter = 0
        return self._pcba_connected_counter > int(self._PCBA_MAX_COUNTER / 2)


    def set_firmware_file_and_widgets(self, _firmware_file: str | Path, progress_bar: EmbeddedProgressBar) -> None:
        super().set_firmware_file(_firmware_file, show_progressbar=False, color=PG_COLOR_PROCESS)
        self.w_progress_bar: EmbeddedProgressBar = progress_bar
        self._progress = progress_bar  # will be deleted by the underlaying flasher object on finish
        self._use_threading = True


    def process_file(self) -> bool:
        global DEBUG

        ok: bool = False
        self.count += 1
        self.w_progress_bar.progress.configure(style="PROCESS.ColorProgress.Horizontal.TProgressbar")
        self._progress = self.w_progress_bar  # has been deleted on every finish
        if self.simulate_programming:
            ok = self.validate_file()
        else:
            try:
                ok = self.program_fw_file()
            except OSError as ex:
                _log = getLogger(__name__, DEBUG)
                _log.error(f"Socket #{self.socket}: {ex}")
                ok = False
                maximum = self.w_progress_bar.progress.cget("maximum")
                value = self.w_progress_bar.progress.cget("value")
                if (value is None) or (value < (maximum * 0.03)):
                    self._print_progress_bar(maximum * 0.03, maximum)  # progress a bit to show the color
        if ok:
            self.count_pass += 1
            self.w_progress_bar.progress.configure(style="PASS.ColorProgress.Horizontal.TProgressbar")
        else:
            self.count_fail += 1
            self.w_progress_bar.progress.configure(style="FAIL.ColorProgress.Horizontal.TProgressbar")
        return ok


#--------------------------------------------------------------------------------------------------


def task_done(future) -> None:
    global DEBUG, AUTOSTART_PROGRAMMING

    _log = getLogger(__name__, DEBUG)
    try:
        result, sock, win = future.result()  # blocks until results are ready
        win.futures[sock] = None
        # update ui
        if result:
            v = win.var_label_count_pass[sock]
        else:
            v = win.var_label_count_fail[sock]
        v.set(v.get() + 1)
        # signal that we are ready
        b = win.var_button_text[sock]
        if AUTOSTART_PROGRAMMING:
            b.set("REMOVE PCBA")
            # wait for PCBA to be removed
            f: MultiBQStudioFileFlasher = win.flasher[sock]
            while f.check_if_pcba_connected():
                pass   # wait
        # button
        b.set("START")
        win.buttons[sock]["state"] = "normal"
    except TimeoutError as error:
        _log.error("Function task_done took longer than %d seconds" % error.args[1])
    except Exception as error:
        _log.error("Function task_done raised %s" % error)



#--------------------------------------------------------------------------------------------------

class WindowUI(object):

    def __init__(self, command_queue: mp.Queue, selected_product: str, title: str = "PCBA PROGRAMMING"):
        global DEBUG, PROGRAMMERS, PRODUCT_LIST
        global PG_COLOR_PROCESS, PG_COLOR_PASS, PG_COLOR_FAIL

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        row_itr = itertools.count()

        self.selected_product: str = selected_product

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        self.var_label_product = tk.StringVar(self.root, f'{selected_product} ({PRODUCT_LIST[selected_product]["name"]})')
        self.var_label_firmware_file = tk.StringVar(self.root, PRODUCT_LIST[selected_product]["firmware_file"])
        self.var_label_count: List[tk.IntVar] = [tk.IntVar(self.root) for _ in range(len(PROGRAMMERS))]
        self.var_label_count_pass: List[tk.IntVar] = [tk.IntVar(self.root) for _ in range(len(PROGRAMMERS))]
        self.var_label_count_fail: List[tk.IntVar] = [tk.IntVar(self.root) for _ in range(len(PROGRAMMERS))]
        self.var_button_text: List[tk.StringVar] = [tk.StringVar(self.root, "START") for _ in range(len(PROGRAMMERS))]


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
        _w = 1024  # width set manually
        _h = 650  # width set manually
        _w = int(self.root.winfo_screenwidth() * 0.95)
        _h = int(self.root.winfo_screenheight() * 0.80)
        # # Set a minsize for the window
        # self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        self.root.minsize(int(_w/2), int(_h/2))
        _x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        # _x = int(self.root.winfo_screenwidth() - _w - _padall)
        _y = int((self.root.winfo_screenheight() - _h) / 3)
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")

        #
        # setup widgets
        #
        style.configure("MainFrame.TFrame")  # to change the background color dynamically on whole Window
        self.mainframe = ttk.Frame(self.root, pad=(_padall,_padall,_padall,_padall), takefocus=True, style="MainFrame.TFrame")
        #self.mainframe.grid(row=0, column=0, sticky="NESW")
        self.mainframe.pack(fill=tk.BOTH, expand=1)
        #self.mainframe.grid_rowconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(0, weight=2)
        self.mainframe.grid_columnconfigure(1, weight=1)
        self.mainframe.grid_columnconfigure(2, weight=8)
        self.mainframe.grid_columnconfigure(3, weight=1)
        self.mainframe.grid_columnconfigure(4, weight=1)
        self.mainframe.grid_columnconfigure(5, weight=1)
        #self.root.grid_rowconfigure(0, weight=1)
        #self.root.grid_columnconfigure(0, weight=1)


        # Part number and firmware file
        _row = next(row_itr)
        ttk.Label(self.mainframe,
            textvariable=self.var_label_product,
            font=("-size", 16, "-weight", "bold")
        ).grid(row=_row, column=0, columnspan=2, sticky=tk.NSEW)
        ttk.Label(self.mainframe,
            textvariable=self.var_label_firmware_file,
            font=("-size", 10)
        ).grid(row=_row, column=2, sticky=tk.NSEW)
        # headers
        ttk.Label(self.mainframe,
            text="Count",
            justify="center", font=("-size", 10)
        ).grid(row=_row, column=3)
        ttk.Label(self.mainframe,
            text="Pass",
            justify="center", font=("-size", 10)
        ).grid(row=_row, column=4)
        ttk.Label(self.mainframe,
            text="Fail",
            justify="center", font=("-size", 10)
        ).grid(row=_row, column=5)

        # Progress bars
        _colspan = 2

        # create the needed styles
        style.configure("PROCESS.ColorProgress.Horizontal.TProgressbar", background=PG_COLOR_PROCESS)
        style.configure("PASS.ColorProgress.Horizontal.TProgressbar", background=PG_COLOR_PASS)
        style.configure("FAIL.ColorProgress.Horizontal.TProgressbar", background=PG_COLOR_FAIL)
        style.configure("UNAVAILABLE.TButton", foreground="red")

        # create progress bars and flashers
        self.futures = {}
        self.pg_bars: List[EmbeddedProgressBar] = []
        self.flasher: List[MultiBQStudioFileFlasher] = []
        self.buttons: List[ttk.Button] = []

        for index, resource_str in enumerate(PROGRAMMERS):
            _row = next(row_itr)
            ttk.Label(self.mainframe,
                text=f"Slot #{index}",
                justify="center",
                font=("-size", 12, "-weight", "bold")
            ).grid(row=_row, column=0)


            btn = ttk.Button(self.mainframe,
                textvariable=self.var_button_text[index],
                state="disabled",
                command=lambda slot=index: self.q_cmd.put({"start": slot, "fw": PRODUCT_LIST[selected_product]["firmware_file"]})
            )
            btn.grid(row=_row, column=1, ipady=0, sticky=tk.NSEW)
            self.buttons.append(btn)

            pg_bar = ttk.Progressbar(self.mainframe,
                orient=tk.HORIZONTAL, mode="determinate", maximum=100, value=0,
                style=("PROCESS.ColorProgress.Horizontal.TProgressbar")
            )
            pg_bar.grid(row=_row, column=2, sticky=tk.NSEW, ipady=15,)
            # create a wrapper class instance of the progress bar, which can be passed to flasher
            self.pg_bars.append(EmbeddedProgressBar(pg_bar, self.root))

            ttk.Label(self.mainframe, textvariable=self.var_label_count[index], justify="center",
                    font=("-size", 12, "-weight", "bold")
            ).grid(row=_row, column=3)
            ttk.Label(self.mainframe, textvariable=self.var_label_count_pass[index], justify="center",
                    font=("-size", 12, "-weight", "bold")
            ).grid(row=_row, column=4)
            ttk.Label(self.mainframe, textvariable=self.var_label_count_fail[index], justify="center",
                    font=("-size", 12, "-weight", "bold")
            ).grid(row=_row, column=5)

            try:
                # now create also the flasher of that index
                flasher = MultiBQStudioFileFlasher(
                    resource_str,
                    index,
                    chipset=PRODUCT_LIST[selected_product]["chipset"],
                    simulate_programming=SIMULATE_PROGRAMMING,  # this allows to test without programmer
                )
                self.flasher.append(flasher)
                btn["state"] = "normal"
                if not SIMULATE_PROGRAMMING:
                    self._log.info(f"Flasher OK at socket #{index} ({resource_str}).")
                else:
                    self._log.info(f"Simulate Flasher at socket #{index}.")
            except Exception as ex:
                # flasher not available
                self._log.info(f"Flasher NOT FOUND at socket #{index} ({resource_str}).")
                btn.configure(style="UNAVAILABLE.TButton")




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

        # #print("BUTTON-LAYOUT:", style.layout('TButton'))
        # #print("BUTTON-MAP:",    style.map("TButton"))
        # #print("BUTTON-LOOKUP:", style.lookup("TButton", "background", state=['pressed']))
        # if PRODUCTION_MODE:
        #     _row = next(row_itr)
        #     #
        #     # 'alt' style TButton map = {'highlightcolor': [('alternate', 'black')], 'relief': [('pressed', '!disabled', 'sunken'), ('active', '!disabled', 'raised')]}
        #     # NOTE: sv-style cannot change background of button, thus we fall back to "alt"
        #     #
        #     style.configure('ValWelding.TButton', foreground='blue')
        #     style.map('ValWelding.TButton', background=[ ("pressed", "lightblue")])
        #     style.configure('SkipPosition.TButton', background='blue', foreground='white', justify="center")  # "justify" is to center text of button in both lines
        #     style.map('SkipPosition.TButton', background=[("active","!pressed","steel blue"),('pressed', 'lightblue')])

        #     self.validation_welding_button = None
        #     self.skip_position_button = None
        #     self.is_validation_welding_mode = True

        #     self.skip_position_button = ttk.Button(self.mainframe, text="VALIDATION WELDING\nNEXT POSITION",  style="SkipPosition.TButton",
        #         command=lambda: self.q_cmd.put({"move_counter": +1}))
        #     self.skip_position_button.grid(row=_row, column=0, columnspan=2, ipady=50, ipadx=5, sticky=tk.NSEW)
        #     self.skip_position_button.grid_remove()

        #     #print(self.skip_position_button.config())

        #     self.validation_welding_button = ttk.Button(self.mainframe, text="ACTIVATE VALIDATION WELDING",  style="ValWelding.TButton",
        #         command=lambda: self.q_cmd.put({"validation_welding": True}))
        #     self.validation_welding_button.grid(row=_row, column=0, columnspan=2, ipady=50, ipadx=20, sticky=tk.NSEW)

        # else:
        #     # Buttons
        #     _row = next(row_itr)
        #     #
        #     # 'alt' style TButton map = {'highlightcolor': [('alternate', 'black')], 'relief': [('pressed', '!disabled', 'sunken'), ('active', '!disabled', 'raised')]}
        #     #
        #     style.configure('Forward.TButton', foreground="green")  #, borderwidth=4, focusthickness=3,)
        #     style.map('SForward.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
        #     style.configure('SBackward.TButton', foreground="red")
        #     style.map('SBackward.TButton', background=[("active","!pressed","white"), ("pressed", "lightblue")])
        #     style.configure('SReset.TButton', foreground="blue", )
        #     style.map('SReset.TButton', background=[("active","!pressed","white"), ("pressed","lightblue")])

        #     #print("RESET-BUTTON-LAYOUT:", style.layout('SReset.TButton'))
        #     #print("RESET-BUTTON-MAP:",    style.map("SReset.TButton"))
        #     #print("RESET-BUTTON-LOOKUP:", style.lookup("SReset.TButton", "background", state=['pressed']))

        #     step_back_button = ttk.Button(self.mainframe, text="STEP BACK",  style="SBackward.TButton",
        #         command=lambda: self.q_cmd.put({"move_counter": -1}))
        #     step_back_button.grid(row=_row, column=0, ipady=50, ipadx=20, sticky=tk.NSEW)

        #     step_forward_button = ttk.Button(self.mainframe, text="STEP FORWARD",  style="SForward.TButton",
        #         command=lambda: self.q_cmd.put({"move_counter": +1}))
        #     step_forward_button.grid(row=_row, column=1, ipady=50, ipadx=5, sticky=tk.NSEW)

        #     reset_seq_button = ttk.Button(self.mainframe, text="RESET SEQUENCE", style="SReset.TButton",
        #         command=lambda: self.q_cmd.put({"reset_counter": 0}))
        #     reset_seq_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, sticky=tk.NSEW)


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

        # Sizegrip
        #sizegrip = ttk.Sizegrip(self.root)
        #sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))

        ## Add an information widget.
        #label = ttk.Label(mainframe, text=f'\nWelcome to hello_world*4.py.\n')
        #label.grid(column=0, row=next(row_itr), sticky='w')

        # schedule queue processing callback
        #self.executor = ThreadPool()

        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())
        #self._id_after = self.mainframe.after(1000, lambda: self.sim_programming())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)

        #reset_seq_button.focus_set()


    @concurrent.thread
    def task_programming(self, sock: int) -> Tuple[bool, int, Any]:
        try:
            result = self.flasher[sock].process_file()
        except Exception as error:
            _log.error("Process file raised %s" % error)
            result = False
        return result, sock, self


    def process_command_queue(self):
        global FIRMWARE_FP, AUTOSTART_PROGRAMMING

        if not self.q_cmd.empty():
            a = self.q_cmd.get()
            _do_update = False
            _play_soundfile = None
            if a:
                if "start" in a:
                    sock = int(a["start"])
                    fw = str(a["fw"])
                    # check if the flasher is not yet active
                    if (sock not in self.futures) or (self.futures[sock] is None):
                        # prepare the flasher
                        self.flasher[sock].set_pcba_connected()
                        self.flasher[sock].set_firmware_file_and_widgets(FIRMWARE_FP / fw, self.pg_bars[sock])
                        # activate the task to program with the flasher
                        _future: Future = self.task_programming(sock)
                        _future.add_done_callback(task_done)
                        self.futures[sock] = _future
                        # update ui
                        v = self.var_button_text[sock]
                        v.set("...")
                        self.buttons[sock]["state"] = "disabled"
                        v = self.var_label_count[sock]
                        v.set(v.get() + 1)
                        self._log.info(f"Socket #{sock}: Start programming {fw}")
                    else:
                        self._log.info(f"Socket #{sock}: Ignore start.")
                    _do_update = True

                # if "revision" in a:
                #     self.var_label_sequence_revision.set(f'Rev.: {a["revision"]}')
                #     #print("UI:UPDATE REVISION")
                #     _do_update = True
                # if "part_number" in a:
                #     self.var_label_part_number.set(a["part_number"])
                #     #print("UI:UPDATE PART NUMBER")
                #     _do_update = True
                # if "sequence" in a:
                #     self.var_label_sequence.set(a["sequence"])
                #     self.var_label_sequence_length.set(f'Seq. length: {len(a["sequence"])}')
                #     #print("UI:UPDATE SEQUENCE")
                #     _do_update = True
                # if "position" in a:
                #     _txt = a["position"]
                #     # !!!
                #     # WE show Postion 1-based (!ROBERT)
                #     # !!!
                #     self.var_label_position.set((_txt + 1) if _txt != -1 else "")
                #     #print("UI:UPDATE COUNTER")
                #     _do_update = True
                # if "program" in a:
                #     _txt = a["program"]
                #     self.var_label_program.set(_txt if _txt != -1 else "")
                #     #print("UI:UPDATE PROGRAM")
                #     _do_update = True
                # if "udi" in a:
                #     if a["udi"] is None:
                #         self.label_udi.config(background="gray", foreground="black")
                #         self.var_label_udi.set("PLEASE SCAN UDI")
                #         print("UI:RESET UDI")
                #     else:
                #         self.label_udi.config(background="blue", foreground="white")
                #         self.var_label_udi.set(a["udi"])
                #     #self.validation_welding_mode(False)
                #     _do_update = True
                # if "udi_scanned" in a:
                #     self.label_udi.config(background="lightblue", foreground="black")
                #     self.var_label_udi.set(a["udi_scanned"])
                #     print("UI:UPDATE UDI")
                #     _do_update = True
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
                # if "validation_welding" in a:
                #     _vw_enabled = a["validation_welding"]
                #     self.validation_welding_mode(_vw_enabled)
                # if "result" in a:
                #     # result overall
                #     #self.validation_welding_mode(False)
                #     if self.is_validation_welding_mode:
                #         self.validation_done()
                #     #_fgcolor = "black" if "\n" in a["udi"] else "white"
                #     _fgcolor = "black"
                #     if "passed" in a["result"]:
                #         _bgcolor = "green"
                #         if self.is_validation_welding_mode:
                #             _bgcolor = "dark slate gray"
                #     else:
                #         _bgcolor = "red"
                #         if self.is_validation_welding_mode:
                #             _bgcolor = "violet red"
                #     self.label_udi.config(background=_bgcolor, foreground=_fgcolor)
                #         #_play_soundfile = str(Path(__file__).parent / "./sounds/error-buzz")
                #     self.var_label_udi.set(a["udi"])
                #     print("UI:RESULT")
                #     _do_update = True
            if _do_update:
                self.root.update()
            if _play_soundfile:
                PlaySound(_play_soundfile, SND_FILENAME)
        else:
            pass
            if AUTOSTART_PROGRAMMING:
                # no command to execute, we can do presence scanning
                for sock, btn in enumerate(self.buttons):
                    if "normal" in str(btn["state"]):
                        if (sock not in self.futures) or (self.futures[sock] is None):
                            # we can scan for new PCBA
                            f:MultiBQStudioFileFlasher = self.flasher[sock]
                            if f and f.check_if_pcba_connected():
                                # now we can activate the programming from here:
                                btn.invoke()
                                pass
                        else:
                            # flasher is in use - do not touch!
                            pass
                    else:
                        # either still flashing or waiting for PCBA removal
                        pass
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())





    def sim_programming(self) -> None:
        global DEBUG, FIRMWARE_FP, PROGRAMMERS

        fs_file = Path(FIRMWARE_FP) / "SCD_3412031-04_A_Rubin-B_RRC2020B.bq.fs"
        for sock, _ in enumerate(PROGRAMMERS):
            self.flasher[sock].set_firmware_file_and_widgets(fs_file, self.pg_bars[sock])
            _future = self.task_programming(sock)
            _future.add_done_callback(task_done)
            self.futures.append(_future)

        #for sock in range(1):
        #    result = self.futures[sock].result()  # blocks until results are ready


    def run_mainloop(self) -> None:
        self.root.mainloop()


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


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


def _create_interfaces(simulation: None | str = None) -> StationConfiguration:
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
    #if simulation:
    #    _log.info(f"Use simulation for DSP interface configured {simulation}")
    #    dsp = DspInterface_SIMULATION(simulation, None)
    #else:
    #    dsp = DspInterface(_dsp_api_base_url, None)
    return cfg


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # need to initialize logger on load

    print("=== PCBA Programming Dialog ===")

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("product", choices=PRODUCT_CHOICES, action="store", help="Set a product for firmware file selection.")
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    parser.add_argument("--filepath", action="store", default=FIRMWARE_FP, help="Path and filename prefix for firmware files")
    parser.add_argument("--simulate", action="store_true", help="Programming is simulated.")
    args = parser.parse_args()

    SIMULATE_PROGRAMMING = args.simulate
    FIRMWARE_FP = args.filepath
    PRODUCTION_MODE = not args.development
    

    p = None
    w = None
    s = None
    try:
        # Establish communication queues
        #q_cmd = mp.JoinableQueue()
        q_cmd = mp.Queue()
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, args.product)
        w.run_mainloop()

    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        #if s and s.is_alive():
        #    s.terminate()
        #    s.join(timeout=0.5)  # short process ...
        if p and p.is_alive():
            # Add a poison pill for SPS process
            q_cmd.put(None)
            # Wait for SPS process to finish smoothly
            q_cmd.join()

# END OF FILE