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
import yaml
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter
from winsound import PlaySound, SND_FILENAME

from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.eth2gpio import RemoteGPIO
from rrc.smbus import BusMaster
from rrc.chipsets.bq import ChipsetTexasInstruments
from rrc.chipsets.bq40z50 import BQ40Z50R1, BQ40Z50R2

from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV
from rrc.dsp.interface import DspInterface, DspInterface_SIMULATION, DSPInterfaceError
from rrc.ui.progress_bar import center as center_of_window
from rrc.chipsets.bq_flasher import BQStudioFileFlexFlasher

# multi tasking
import asyncio
from concurrent.futures import Future, TimeoutError
#from pebble import asynchronous, concurrent, sighandler, ProcessFuture, ProcessPool


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
# Note: these IP numbers gets transformed according to the line setting in
#       station_config.yaml using key "PCBA_TEST", socket 0, resource 0
PROGRAMMERS = [
    "172.25.102.7:2101",
    "172.25.102.9:2101",
    "172.25.102.10:2101",
    #"172.21.101.50:2101",
    # ... add more if needed ...
]


# --------------------------------------------------------------------------- #


FIRMWARE_FP = Path(__file__).parent / "../.." / "Battery-PCBA-Test/filestore"  # path of firmware files
PRODUCT_LIST: dict = yaml.safe_load((FIRMWARE_FP / "pcba_programmer_config.yaml").read_text())
PRODUCT_CHOICES = [k for k in PRODUCT_LIST.keys()]  # this is the list of part numbers to select by command line
SIMULATE_PROGRAMMING: bool = False
PRODUCTION_MODE: bool = True
AUTOSTART_PROGRAMMING: bool = False
USE_RECOVERY_FILE: bool = False


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class RawDescriptionArgumentDefaultsHelpFormatter(RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter): pass


#--------------------------------------------------------------------------------------------------


class EmbeddedProgressBar():

    def __init__(self,  q_ui: mp.Queue, socket: int) -> None:
        self.q_ui = q_ui
        self.socket = socket
        self.hidden = 0
        self._value = None
        self._last_sent = 0

    def hide(self) -> None:
        self.hidden = 1

    def show(self) -> None:
        self.hidden = 0

    def set_value_threshold(self, value: float, step_threshold: float = 5/100) -> None:
        if ((value - self._value) > step_threshold) or (value >= self._value) or (value == 0):
            self.set_value(value)

    def set_value(self, value: float) -> None:
        self._value = value
        if ((value - self._last_sent) >= 0.5) or (value >= 100.0):
            self.q_ui.put({
                "progress": value,
                "socket": self.socket,
                #"maximum": maximum,
            })
            self._last_sent = value

    def update(self) -> None:
        pass

    def quit(self) -> None:
        self.hide()

    def close(self) -> None:
        self.hide()

#--------------------------------------------------------------------------------------------------

PG_COLOR_PROCESS = "blue"
PG_COLOR_PASS = "green"
PG_COLOR_FAIL = "red"

class MultiBQStudioFileFlasher(BQStudioFileFlexFlasher):

    def __init__(self, resource_str: str, socket: int, chipset: str = "BQ40Z50R1",  simulate_programming: bool = False) -> None:
        bat = None
        if not simulate_programming:
            # create the interface (we keep it as it is more readable for GPIO than self.battery.bus.i2c.gpio_xxx())
            self.i2c_gw = I2CPort(resource_str)
            smbus = BusMaster(self.i2c_gw, retry_limit=1, verify_rounds=3, pause_us=50)
            if chipset == "BQ40Z50R1":
                bat = BQ40Z50R1(smbus)
        super().__init__(bat,
                         color="black",   # should never been shown as firmware file is missing
                         firmware_file=None,  # we provide the firmware file later together with the progress bar
                         show_progressbar=False)  # we provide a different progress bar
        self.simulate_programming: bool = simulate_programming
        self.socket: int = socket
        # internals
        self._use_threading = False
        self._pcba_connected_counter: int = 0
        self._PCBA_MAX_COUNTER: int = 50
        self._pcba_power: int = 0


    def switch_pcba_power(self, onoff: int | bool) -> bool:
        """Our RRC Flasher with OLIMEX board has a feature to switch the PCBA power ON and OFF.

        Args:
            onoff (int | bool): _description_

        Returns:
            bool: _description_
        """
        _v: int = 0 if onoff else 1  # inverted switching
        if self.i2c_gw.gpio_write_output(32, _v):
            self._pcba_power = int(onoff)
            return True
        else:
            return False


    def set_pcba_connected(self):
        self._pcba_connected_counter = self._PCBA_MAX_COUNTER


    def check_if_pcba_connected(self) -> bool:
        self.switch_pcba_power(1)
        if self.battery.isReady():
            self._pcba_connected_counter += 1
            if self._pcba_connected_counter > self._PCBA_MAX_COUNTER:
                self._pcba_connected_counter = self._PCBA_MAX_COUNTER
        else:
            self._pcba_connected_counter -= 1
            if self._pcba_connected_counter < 0:
                self._pcba_connected_counter = 0
        _is_connected = self._pcba_connected_counter > int(self._PCBA_MAX_COUNTER / 2)
        if not _is_connected:
            self.switch_pcba_power(0)
        return _is_connected


    def set_firmware_file_and_widgets(self, _firmware_file: str | Path, progress_bar: EmbeddedProgressBar) -> None:
        super().set_firmware_file(_firmware_file, show_progressbar=False, color=PG_COLOR_PROCESS)
        self.w_progress_bar: EmbeddedProgressBar = progress_bar
        self._progress = progress_bar  # will be deleted by the underlaying flasher object on finish
        self._use_threading = True


    def process_file(self) -> bool:
        global DEBUG

        ok: bool = False
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
        return ok


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


class ProgrammingWorker(mp.Process):
    def __init__(self, socket: int, resource_str: str, chipset: str, firmware_file: str | Path, q_ui: mp.Queue, simulate_programming: bool = False) -> None:
        super().__init__()
        self.socket = socket
        self.resource_str = resource_str
        self.chipset = chipset
        self.firmware_file = firmware_file
        self.q_ui = q_ui
        self.simulate_programming = simulate_programming

    def run(self) -> None:
        global DEBUG

        _log = getLogger(__name__, DEBUG)
        try:
            # create a progress fowrwarder
            progress_bar = EmbeddedProgressBar(self.q_ui, self.socket)

            # create flasher
            flasher = MultiBQStudioFileFlasher(
                self.resource_str,
                self.socket,
                chipset=self.chipset,
                simulate_programming=self.simulate_programming,  # this allows to test without programmer
            )
            #tic = perf_counter()
            if flasher.switch_pcba_power(1):
                sleep(0.25)  # let the PCBA powering up itself
            flasher.set_firmware_file_and_widgets(self.firmware_file, progress_bar)
            #toc = perf_counter()
            #_log.info(f"Need {toc - tic:0.4f} seconds")
            _log.info(f"Starting flasher {str(flasher)}:")
            result = flasher.process_file()
            flasher.switch_pcba_power(0)  # always power off the PCBA
        except Exception as error:
            _log.error(f"Process file raised {error}")
            result = False
        finally:
            #flasher.battery.bus.i2c.close()
            pass
        # send result by queue
        self.q_ui.put({
            "result": "pass" if result else "fail",
            "socket": self.socket
        })


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

class WindowUI(object):

    def __init__(self, command_queue: mp.Queue, selected_product: str, title: str = "PCBA PROGRAMMING"):
        global DEBUG, PROGRAMMERS, PRODUCT_LIST, USE_RECOVERY_FILE
        global PG_COLOR_PROCESS, PG_COLOR_PASS, PG_COLOR_FAIL

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        row_itr = itertools.count()

        self.SELECTED_PRODUCT: str = selected_product
        self.PRODUCT_NAME: str = PRODUCT_LIST[selected_product]["name"]
        self.PRODUCT_CHIPSET: str = PRODUCT_LIST[selected_product]["chipset"]
        self.PRODUCT_FIRMWARE_FILE: str = PRODUCT_LIST[selected_product]["recovery_firmware_file"] if USE_RECOVERY_FILE else PRODUCT_LIST[selected_product]["firmware_file"]

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        self.var_label_product = tk.StringVar(self.root, f'{selected_product} ({self.PRODUCT_NAME})')
        self.var_label_firmware_file = tk.StringVar(self.root, self.PRODUCT_FIRMWARE_FILE)
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
        self.pg_bars = []
        #self.pg_bars: List[EmbeddedProgressBar] = []
        #self.flasher: List[MultiBQStudioFileFlasher] = []
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
                command=lambda slot=index, res=resource_str: self.q_cmd.put({
                    "start": slot, "resource": res,
                    "fw": self.PRODUCT_FIRMWARE_FILE,
                    "chipset": self.PRODUCT_CHIPSET,
                    })
            )
            btn.grid(row=_row, column=1, ipady=0, sticky=tk.NSEW)
            self.buttons.append(btn)

            pg_bar = ttk.Progressbar(self.mainframe,
                orient=tk.HORIZONTAL, mode="determinate", maximum=100, value=0,
                style=("PROCESS.ColorProgress.Horizontal.TProgressbar")
            )
            pg_bar.grid(row=_row, column=2, sticky=tk.NSEW, ipady=15,)
            # create a wrapper class instance of the progress bar, which can be passed to flasher
            #self.pg_bars.append(EmbeddedProgressBar(pg_bar, self.root))
            self.pg_bars.append(pg_bar)


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
                # flasher = MultiBQStudioFileFlasher(
                #     resource_str,
                #     index,
                #     chipset=PRODUCT_LIST[selected_product]["chipset"],
                #     simulate_programming=SIMULATE_PROGRAMMING,  # this allows to test without programmer
                # )
                # self.flasher.append(flasher)
                btn["state"] = "normal"
                if not SIMULATE_PROGRAMMING:
                    self._log.info(f"Flasher OK at socket #{index} ({resource_str}).")
                else:
                    self._log.info(f"Simulate Flasher at socket #{index}.")
            except Exception as ex:
                # flasher not available
                self._log.info(f"Flasher NOT FOUND at socket #{index} ({resource_str}).")
                btn.configure(style="UNAVAILABLE.TButton")

        # schedule queue processing callback
        #self.executor = ThreadPool()

        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())
        #self._id_after = self.mainframe.after(1000, lambda: self.sim_programming())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)

        #reset_seq_button.focus_set()


    # @concurrent.thread
    # def task_programming(self, sock: int) -> Tuple[bool, int, Any]:
    #     try:
    #         _log.info("Starting flasher %s:" % str(self.flasher[sock]))
    #         result = self.flasher[sock].process_file()
    #     except Exception as error:
    #         _log.error("Process file raised %s" % error)
    #         result = False
    #     return result, sock, self

    #------------------------------------------------------------------------------

    def process_command_queue(self):
        global FIRMWARE_FP, AUTOSTART_PROGRAMMING, SIMULATE_PROGRAMMING

        if not self.q_cmd.empty():
            a = self.q_cmd.get()
            _do_update = False
            _play_soundfile = None
            if a:
                if "start" in a:
                    #self._log.info(f"got START")  # DEBUG
                    sock = int(a["start"])
                    resource_str = str(a["resource"])
                    fw = str(a["fw"])
                    chipset = str(a["chipset"])
                    # check if the flasher is not yet active
                    if (sock not in self.futures) or (self.futures[sock] is None):
                        # # prepare the flasher
                        # self.flasher[sock].set_pcba_connected()
                        # self.flasher[sock].set_firmware_file_and_widgets(FIRMWARE_FP / fw, self.pg_bars[sock])
                        # activate the task to program with the flasher
                        #_future: Future = self.task_programming(sock)
                        #_future.add_done_callback(task_done)
                        _future = ProgrammingWorker(sock, resource_str, chipset, FIRMWARE_FP / fw, self.q_cmd, simulate_programming=SIMULATE_PROGRAMMING)
                        _future.start()
                        self.futures[sock] = _future
                        # update ui
                        p: ttk.Progressbar = self.pg_bars[sock]
                        p.config(value=0)
                        p.configure(style="PROCESS.ColorProgress.Horizontal.TProgressbar")
                        self.var_label_count[sock].set(self.var_label_count[sock].get()+1)
                        self.var_button_text[sock].set("...")
                        self.buttons[sock]["state"] = "disabled"
                        v = self.var_label_count[sock]
                        v.set(v.get() + 1)
                        self._log.info(f"Socket #{sock}: Start programming {fw}")
                    else:
                        self._log.info(f"Socket #{sock}: Ignore start.")
                    _do_update = True
                elif "progress" in a:
                    value = float(a["progress"])
                    sock = int(a["socket"])
                    #maximum = float(a["maximum"])
                    progress: ttk.Progressbar = self.pg_bars[sock]
                    progress.config(value=value)
                    #progress.config(value=value, maximum=maximum)
                    _do_update = True
                elif "result" in a:
                    result = a["result"]
                    sock = int(a["socket"])
                    progress: ttk.Progressbar = self.pg_bars[sock]
                    if "pass" in  result:
                        self.var_label_count_pass[sock].set(self.var_label_count_pass[sock].get()+1)
                        progress.configure(style="PASS.ColorProgress.Horizontal.TProgressbar")
                    else:
                        # failed!
                        progress.configure(style="FAIL.ColorProgress.Horizontal.TProgressbar")
                        self.var_label_count_fail[sock].set(self.var_label_count_fail[sock].get()+1)
                        maximum = progress.cget("maximum")
                        value = progress.cget("value")
                        if (value is None) or (value < (maximum * 0.03)):
                            progress.config(value=maximum * 0.03, maximum=maximum)  # progress a bit to show the color
                    # signal that we are ready
                    # button
                    self.var_button_text[sock].set("START")
                    self.buttons[sock]["state"] = "normal"
                    self.futures[sock] = None  # clear to signal availability for mother task


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


    def run_mainloop(self) -> None:
        self.root.mainloop()


#--------------------------------------------------------------------------------------------------


def create_interfaces(simulation: None | str = None) -> Tuple[StationConfiguration, DspInterface]:
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
        cfg = StationConfiguration("PCBA_TEST")
    except FileNotFoundError:
        # comfort for testing: using the development configuration
        cfg = StationConfiguration("PCBA_TEST", filename=CONF_FILENAME_DEV)
        _log.info(f"USING DEVELOPMENT CONFIGURATION {CONF_FILENAME_DEV}")
    _, __, _dsp_api_base_url, _, _ = cfg.get_station_configuration()
    # 2. we can create the DSP interface
    if simulation:
        _log.info(f"Use simulation for DSP interface configured {simulation}")
        dsp = DspInterface_SIMULATION(simulation, None)
    else:
        dsp = DspInterface(_dsp_api_base_url, None)
    return cfg, dsp


#--------------------------------------------------------------------------------------------------


def collect_parameters(cfg: StationConfiguration, dsp: DspInterface) -> Tuple[str, str, str]:
    """ Read configuration from DSP

    Note: this is called from process context,
          do NOT call it from anywhere else except you want to test this function only!

    """

    # 1. we need the station config
    _, _station_id, _dsp_api_base_url, _line_id, _ = cfg.get_station_configuration()
    # 2. with station config we can request the part number from DSP
    print("Fetching part number from DSP...")
    _dsp_info = dsp.get_parameter_for_testrun("PCBA_TEST", _station_id, _line_id, "0")
    #_dsp_info = dsp.get_parameter_for_welding(_station_id, _line_id)
    _part_number = _dsp_info["part_number"]
    _sequence_revision = _dsp_info["test_program_id"]
    print(f"PART NUMBER: {_part_number}")
    return _part_number, _line_id, _station_id


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

    parser = ArgumentParser(description="""
                The PCBA programming tool can be used in-line using the line configuration or
                override the product to be programmed by optional parameter. It uses a built-in configuration dictionary
                which defines the filenames for regular firmware and recovery firmware.
                """, formatter_class=RawDescriptionArgumentDefaultsHelpFormatter)
    parser.add_argument("--product", choices=PRODUCT_CHOICES, action="store", default=None, help="Set a product for firmware file selection. If None given, the line DSP is requested for this parameter.")
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    parser.add_argument("--filepath", action="store", default=FIRMWARE_FP, help="Path and filename prefix for firmware files")
    parser.add_argument("--simulate", action="store_true", help="Programming is simulated.")
    parser.add_argument("--recovery", action="store_true", help="Programming uses recovery file instead which can solve a PCBA stuck in bootloader.")
    args = parser.parse_args()

    SIMULATE_PROGRAMMING = args.simulate
    FIRMWARE_FP = args.filepath
    PRODUCTION_MODE = not args.development
    USE_RECOVERY_FILE = args.recovery

    # get the configuration from DSP if we do not have a product by command line
    # also the IP addresses gets adjusted accoring to the configuration file if
    # no part_number was given. Otherwise we assume development use.
    if args.product:
        part_number = args.product
    else:
        cfg, dsp, = create_interfaces(args.simulate)
        _pn, line_id, station_id = collect_parameters(cfg, dsp)
        part_number = _pn.split("-")[0]
        _res_pattern = cfg.get_resource_strings_for_socket(0)[0]  # so we get the correct IP tuple
        PROGRAMMERS = [f"{'.'.join(_res_pattern.split('.')[:3])}.{n.split('.')[-1]}" for n in PROGRAMMERS]

    w = None
    try:
        # Establish communication queues
        #q_cmd = mp.JoinableQueue()
        q_cmd = mp.Queue()
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, part_number)
        w.run_mainloop()

    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        pass
        #if s and s.is_alive():
        #    s.terminate()
        #    s.join(timeout=0.5)  # short process ...
        # if p and p.is_alive():
        #     # Add a poison pill for SPS process
        #     q_cmd.put(None)
        #     # Wait for SPS process to finish smoothly
        #     q_cmd.join()

# END OF FILE