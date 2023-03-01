from typing import List, Tuple
from enum import Enum
import multiprocessing as mp
import itertools
import tkinter as tk
import tkinter.ttk as ttk
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from rrc.modbus.aws3 import AWS3Modbus, AWS3Modbus_DUMMY
from rrc.station_config_loader import StationConfiguration, CONF_FILENAME_DEV
from rrc.dsp.interface import DspInterface
# import SQL managing modules
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from rrc.dbcon import get_protocol_db_connector
from rrc.barcode_scanner import create_barcode_scanner, Eth2SerialDevice, SerialComportDevice

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 0   # set to 0 for production
from rrc.custom_logging import getLogger
# --------------------------------------------------------------------------- #

ENABLE_UDI_SCAN = 0  # is being overwritten by argument


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


#--------------------------------------------------------------------------------------------------

class WindowUI(object):

    def __init__(self, command_queue: mp.JoinableQueue, response_queue: mp.Queue, title: str = "POOR MAN'S SPS"):
        global DEBUG, ENABLE_UDI_SCAN

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        self.q_res = response_queue
        row_itr = itertools.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        self.UDI_SCAN_TEXT = "SCAN NEXT UDI"
        self.var_label_counter = tk.StringVar(self.root, "")
        self.var_label_program = tk.StringVar(self.root, "")
        self.var_label_part_number = tk.StringVar(self.root, "")
        self.var_label_sequence = tk.StringVar(self.root, "")
        self.var_label_sequence_revision = tk.StringVar(self.root, "")
        self.var_label_resource_str = tk.StringVar(self.root, "")
        self.var_label_udi = tk.StringVar(self.root, self.UDI_SCAN_TEXT)

        self.root.withdraw()  # hide window
        self.root.title(title)
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "ui" / "robot-icon.ico")
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "ui" / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        style = ttk.Style()
        #style.theme_use("alt")

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
        #self.mainframe = self.root
        self.mainframe = ttk.Frame(self.root, pad=(_padall,_padall,_padall,_padall), takefocus=True)

        #self.mainframe.pack(fill=tk.BOTH)
        # configure the column width equally to center everything nicely

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
        if ENABLE_UDI_SCAN:
            self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center",
                                       font=("-size", 14, "-weight", "bold"), background="blue", foreground="white")
            self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=50, sticky="ew")
        else:
            self.label_udi = ttk.Label(self.mainframe, textvariable=self.var_label_udi, anchor = "center", font=("-size", 12))
            self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5, sticky="ew")
        # if ENABLE_UDI_SCAN:
        #     self.label_udi.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=50, sticky="ew")
        # else:
        #     self.label_udi.grid_forget()

        #_row = next(row_itr)
        label3 = ttk.Label(self.mainframe,text="SEQUENCE POS",justify="center", font=("-size", 10))
        label3.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)
        label4 = ttk.Label(self.mainframe,
                            textvariable=self.var_label_counter,
                            justify="center", font=("-size", 20, "-weight", "bold"))
        label4.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=5)

        label5 = ttk.Label(self.mainframe,text="PROGRAM",justify="center",font=("-size", 18))
        label5.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)
        label6 = ttk.Label(self.mainframe,
            textvariable=self.var_label_program,
            justify="center", font=("-size", 32, "-weight", "bold"))
        label6.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10)

        if not ENABLE_UDI_SCAN:
            # Buttons
            _row = next(row_itr)
            style.configure('B1.TButton', foreground="red", background='#232323')
            style.map('B1.TButton', background=[("active","#ff0000")])
            style.configure('B2.TButton', foreground="green", background='#232323')
            style.map('B2.TButton', background=[("active","#ff0000")])
            #style.configure('TButton', background = 'red', foreground = 'green', width = 20, borderwidth=1, focusthickness=3, focuscolor='none')

            step_back_button = ttk.Button(self.mainframe, text="STEP BACK",  style="B1.TButton",
                command=lambda: self.q_cmd.put({"move_counter": -1}))
            step_back_button.grid(row=_row, column=0, ipady=50, ipadx=20, sticky=tk.NSEW)

            step_forward_button = ttk.Button(self.mainframe, text="STEP FORWARD",  style="B2.TButton",
                command=lambda: self.q_cmd.put({"move_counter": +1}))
            step_forward_button.grid(row=_row, column=1, ipady=50, ipadx=5, sticky=tk.NSEW)

            # separator = ttk.Separator(self.mainframe)
            # separator.grid(row=next(row_itr), column=0, columnspan=2, padx=(20, 10), pady=10, sticky="ew")
            reset_seq_button = ttk.Button(self.mainframe, text="RESET SEQUENCE",
                command=lambda: self.q_cmd.put({"reset_counter": 0}))
            #ok_button.bind("<Return>", _accept_udi)
            #ok_button.bind("<Key-Escape>", _cancel)
            reset_seq_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, sticky=tk.NSEW)
            #ok_button.grid_forget()


        # Some more information labels
        _row = next(row_itr)
        #label_10 = ttk.Label(self.mainframe, textvariable=self.var_label_sequence, font=("-size", 8))
        #label_10.grid(row=_row, column=0,  ipady=10)
        label_10 = ttk.Label(self.mainframe, anchor=tk.CENTER, text="Sequence Rev. ", font=("-size", 8))
        label_10.grid(row=_row, column=0,  ipady=10, sticky="e")
        label_11 = ttk.Label(self.mainframe, anchor=tk.CENTER, textvariable=self.var_label_sequence_revision, font=("-size", 8))
        label_11.grid(row=_row, column=1, ipady=10, sticky="w")

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

        if not ENABLE_UDI_SCAN:
            reset_seq_button.focus_set()


    def process_command_queue(self):
        if not self.q_res.empty():
            a = self.q_res.get()
            #print("UI:", a)
            _do_update = False
            if a:
                if "resource_str" in a:
                    self.var_label_resource_str.set(a["resource_str"])
                    #print("UPDATE RESOURCE")
                    _do_update = True
                if "revision" in a:
                    self.var_label_sequence_revision.set(a["revision"])
                    #print("UPDATE REVISION")
                    _do_update = True
                if "part_number" in a:
                    self.var_label_part_number.set(a["part_number"])
                    #print("UPDATE PART NUMBER")
                    _do_update = True
                if "sequence" in a:
                    self.var_label_sequence.set(a["sequence"])
                    #print("UPDATE SEQUENCE")
                    _do_update = True
                if "counter" in a:
                    _txt = a["counter"]
                    self.var_label_counter.set(_txt if _txt != -1 else "")
                    #print("UPDATE COUNTER")
                    _do_update = True
                if "program" in a:
                    _txt = a["program"]
                    self.var_label_program.set(_txt if _txt != -1 else "")
                    #print("UPDATE PROGRAM")
                    _do_update = True
                if "udi_scanned" in a:
                    self.label_udi.config(background="gray", foreground="black")
                    self.var_label_udi.set(a["udi_scanned"])
                    print("UPDATE UDI")
                    _do_update = True
                if "result" in a:
                    if "pass" in a["result"]:
                        self.label_udi.config(background="green", foreground="black")
                    else:
                        self.label_udi.config(background="red", foreground="black")
                    self.var_label_udi.set(a["udi"])
                    print("RESULT")
                    _do_update = True
                if "reset_udi" in a:
                    self.label_udi.config(background="blue", foreground="white")
                    self.var_label_udi.set(self.UDI_SCAN_TEXT)
                    print("RESET UDI")
                    _do_update = True
            if _do_update:
                self.root.update()
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())


    def run_mainloop(self):
        self.root.mainloop()

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

def test_sps_process(dev: AWS3Modbus, program_sequence: List[int] = [1,2,3,4,5]):
    print(f"Poor man's SPS machine: {dev.machine_name}, at {repr(dev)}")
    while True:
        if dev.is_machine_ready():
            counter_base_ax1 = dev.read_axis_counter(1)
            counter_base_ax2 = dev.read_axis_counter(2)
            lock_base = dev.read_machine_lock_status()
            program_no_base = dev.read_program_no()
            break
    print(f"Base counters:")
    print(f"    Ax1:{counter_base_ax1}\n    Ax2:{counter_base_ax2}")
    print(f"Base program no: {program_no_base}")
    #program_sequence = [1,2,3,4,5,6,7,8,9,10]  # demo
    program_step = 0
    print(f"Program step: {program_step} of {len(program_sequence)}")
    last_counter_ax1 = counter_base_ax1
    last_counter_ax2 = counter_base_ax2
    program_no = program_no_base
    next_program_no = program_sequence[program_step]
    _machine_locked = False
    while True:
        sleep(0.1)  # throttle polling loop
        try:
            if not dev.is_machine_ready():
                continue
            # 1. lock the machine
            #dev.lock_machine_step()
            # 2. get the counters
            counter_ax1 = dev.read_axis_counter(1)
            #counter_ax2 = dev.read_axis_counter(2)
            # 3. check if we have to moved to the  next program step
            diffcount = counter_ax1["counter"] - last_counter_ax1["counter"]
            if diffcount > 0:
                # yes we have finished a cycle -> move to next program step
                dev.lock_machine_step()
                _machine_locked = True
                program_step += 1
                if program_step >= len(program_sequence):
                    program_step = 0
                next_program_no = program_sequence[program_step]
                print(f"Move program step to {program_step} with program no {next_program_no}")
                last_counter_ax1 = counter_ax1
                #last_counter_ax2 = counter_ax2
            # 4. chek if the correct program step is set
            program_no = dev.read_program_no()
            if next_program_no != program_no:
                print(f"Set Program No: {next_program_no}")
                dev.write_program_no(next_program_no)
            else:
                #print(f"PROG NO {program_no} == NEXT NO {next_program_no}")
                #sleep(0.1)  # throttle polling loop
                pass
        except AssertionError as ex:
            print("Got Error:", ex)
        except Exception as ex:
            raise
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            if _machine_locked:
                dev.unlock_machine_step()

#--------------------------------------------------------------------------------------------------
class SPSStates(Enum):
    START = 0
    START_LOCKED = 1
    INIT = 2
    SYNC_ON_MACHINE_COUNTER = 3
    SHOW_PROGRAM_STEP = 4
    FETCH_NEXT_PROGRAM = 5
    WAIT_READY_TO_SET_PROGRAM = 6
    SET_PROGRAM_ON_MACHINE = 7
    LOCK_MACHINE = 8
    SHOW_RESULT = 9
    STOP = 10


class SPSStateMachine(object):

    def __init__(self, dev: AWS3Modbus | str, program_sequence: List[int] = [1],
                sequence_rotation: bool = False, start_locked: bool = False) -> None:
        self.state: SPSStates = SPSStates.START_LOCKED if start_locked else SPSStates.START
        self.program_sequence = program_sequence
        self.sequence_pos = 0
        self.sequence_rotation = sequence_rotation
        self.is_sequence_done = False
        self.program_no = -1
        self.next_program_no = -1
        self.counter_base_ax1 = None
        self.counter_ax1 = None
        self.last_counter_ax1 = -1
        self._machine_locked = None
        self._throttle_pause = 0.055
        if isinstance(dev, str):
            # try:
            #     self.dev = AWS3Modbus(dev)
            # except Exception as ex:
            #     print(ex)
            print("Using dummy AWS3 Modbus driver for test purposes.")
            self.dev = AWS3Modbus_DUMMY(dev)  # this starts a simulation to support testing
        else:
            self.dev = dev
        print(f"Poor man's SPS machine: {self.dev.machine_name}, at {repr(self.dev)}")


    def __str__(self) -> str:
        return f"State Machine for SPS on modbus {repr(self.dev)} with sequence {self.program_sequence}"

    def __repr__(self) -> str:
        return f"SPSStateMachine({repr(self.dev)}, {self.program_sequence})"

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

    def run_loop(self):
        while True:
            self.do_one_loop()

    def set_state(self, new_state: SPSStates) -> None:
        self.state = new_state

    def _offset_sequence(self, offset: int) -> None:
        self.sequence_pos = (self.sequence_pos + offset) % len(self.program_sequence)

    def move_seqence_step(self, step: int) -> bool:
        if self.sequence_pos + step >= len(self.program_sequence):
            self.is_sequence_done = True
        else:
            self.is_sequence_done = False
        if self.sequence_rotation or (self.is_sequence_done == False):
            self._offset_sequence(step)
            self.next_program_no = self.program_sequence[self.sequence_pos]
            print(f"Move program step to {self.sequence_pos} with program no {self.next_program_no}")
            self.last_counter_ax1 = self.counter_ax1
            self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
            return True
        else:
            # sequence is done, do not proceed by wrap around
            self.set_state(SPSStates.LOCK_MACHINE)
            return False

    def reset_seqence(self) -> None:
        self.sequence_pos = 0
        self.is_sequence_done = False
        self.next_program_no = self.program_sequence[self.sequence_pos]
        self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)

    def lock_machine(self) -> None:
        if self._machine_locked:
            self.dev.lock_machine_step()
            self._machine_locked = True
        #self.set_state(SPSStates.LOCK_MACHINE)

    def unlock_machine(self) -> None:
        if self._machine_locked:
            self.dev.unlock_machine_step()
            self._machine_locked = False
        #self.set_state(SPSStates.START)

    def do_one_loop(self):
        try:
            match self.state:

                case SPSStates.START:
                    self.unlock_machine()
                    if self.dev.is_machine_ready():
                        self.set_state(SPSStates.INIT)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.START_LOCKED:
                    if self.dev.is_machine_ready():
                        self.lock_machine()
                        self.set_state(SPSStates.INIT)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.INIT:
                    self.counter_base_ax1 = self.dev.read_axis_counter(1)
                    self._machine_locked = self.dev.read_machine_lock_status()
                    self.program_no = self.dev.read_program_no()
                    self.counter_ax1 = self.counter_base_ax1
                    self.last_counter_ax1 = self.counter_ax1
                    print(f"Counters at init: Ax1={self.counter_ax1}")
                    print(f"Program no at init: {self.program_no}")
                    self.next_program_no = self.program_sequence[self.sequence_pos]
                    print(f"Next program on sequence on {self.sequence_pos}: {self.next_program_no}")
                    if self.next_program_no != self.program_no:
                        self.program_no = self.next_program_no  # to avoid blitting a -1 on UI
                        self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)
                    else:
                        self.set_state(SPSStates.SHOW_PROGRAM_STEP)

                case SPSStates.SHOW_PROGRAM_STEP:
                    print(f"Program step: {self.sequence_pos} of {len(self.program_sequence)}")
                    print(f"Program set {self.program_no}")
                    self.set_state(SPSStates.SYNC_ON_MACHINE_COUNTER)

                case SPSStates.SYNC_ON_MACHINE_COUNTER:
                    if self._machine_locked or self.dev.is_machine_ready():
                        self.counter_ax1 = self.dev.read_axis_counter(1)
                        #  check if we have to moved to the  next program step
                        diffcount = self.counter_ax1["counter"] - self.last_counter_ax1["counter"]
                        if diffcount > 0:
                            self.last_counter_ax1 = self.counter_ax1
                            self.set_state(SPSStates.FETCH_NEXT_PROGRAM)
                        else:
                            sleep(self._throttle_pause)  # throttle polling
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.FETCH_NEXT_PROGRAM:
                    # yes we have finished a cycle -> move to next program step
                    self.move_seqence_step(+1)  # the next state is being set in this function

                case SPSStates.WAIT_READY_TO_SET_PROGRAM:
                    if self._machine_locked or self.dev.is_machine_ready():
                        self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.SET_PROGRAM_ON_MACHINE:
                    self.lock_machine()
                    # check if the correct program step is set
                    self.program_no = self.dev.read_program_no()
                    if self.next_program_no != self.program_no:
                        print(f"Set program {self.next_program_no} on machine.")
                        self.dev.write_program_no(self.next_program_no)
                        self.program_no = self.dev.read_program_no()
                        # ??? check ???
                    else:
                        print(f"Program {self.program_no} already set.")
                    self.unlock_machine()
                    self.set_state(SPSStates.SHOW_PROGRAM_STEP)

                case SPSStates.LOCK_MACHINE:
                    if self.dev.is_machine_ready():
                        self.lock_machine()
                        #
                        # wait for being lock-released from OUTSIDE
                        # by switching state to SPSStates.START again
                        #
                        self.set_state(SPSStates.SHOW_RESULT)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.SHOW_RESULT:
                    print(f"Result: ???")
                    self.set_state(SPSStates.STOP)

                    #
                    # need to be switched back to START from outside
                    #
                    pass

                case other:
                    self.set_state(SPSStates.START)

        except AssertionError as ex:
            print("Got ERROR to ignore: ", ex)
            self.unlock_machine()
            pass  # swallow
        except Exception as ex:
            self.unlock_machine()
            pass  # swallow
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            #if self._machine_locked and (self.state != SPSStates.STOP):
               #self.dev.unlock_machine_step()
            #if (self.state != SPSStates.STOP):
            #   self.unlock_machine()
            # do not change the state here
            pass


#--------------------------------------------------------------------------------------------------
# *** SPS ***
#
class ProcessSPS(mp.Process):

    def __init__(self, command_queue: mp.JoinableQueue, response_queue: mp.Queue) -> None:
        mp.Process.__init__(self)
        global DEBUG, ENABLE_UDI_SCAN
        self._log = getLogger(__name__, DEBUG)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.enable_udi_scan = ENABLE_UDI_SCAN

    def collect_parameters(self) -> Tuple[List[int], str, str, str]:
        """ Read configuration from DSP + DB connection

        Note: this is called from process context,
              do NOT call it from anywhere else except you want to test this function only!

        Raises:
            Exception: _description_
        """
        # 1. we need the station config
        try:
            cfg = StationConfiguration("CELL_WELDING") #, filename=CONF_FILENAME_DEV)
        except FileNotFoundError:
            # comfort for testing
            cfg = StationConfiguration("CELL_WELDING", filename=CONF_FILENAME_DEV)
        _, _station_id, _dsp_api_base_url, _line_id, _ = cfg.get_station_configuration()
        # 2. with station config we can request the part number from DSP
        print("Fetching part number from DSP...")
        dsp = DspInterface(_dsp_api_base_url, None)
        _dsp_info = dsp.get_parameter_for_testrun("CELL_WELDING", _station_id, _line_id, "0")
        _part_number = _dsp_info["part_number"]
        # 3. with station config we can get the IP resource for the welder MODBUS
        _resources = cfg.get_resource_strings_for_socket(0)
        _controller_resource_str = _resources[0]
        print(f"PART NUMBER: {_part_number}")
        # 4. we need the program sequence of the AWS welder for the given part number
        print("Requesting database for sequence...")
        srcEngine, SSession = get_protocol_db_connector()
        session = SSession()
        #_part_number = "412031-16"  # RRC2020B
        #_part_number = "412036-16"  # RRC2040B
        response = session.execute(sa.text(
                f"SELECT revision,program_sequence,parameter FROM `spsconfig` AS sc WHERE sc.part_number='{_part_number}' ORDER BY revision DESC"
                ))
        rows = response.fetchall()
        session.close_all()
        if len(rows) == 0:
            # not found! -> do not proceed
            raise Exception("No Data in Database found, cannot proceed!")
        print(f"Got record: {rows[0]}")
        return [int(i) for i in rows[0][1].split(",")], str(rows[0][0]), _controller_resource_str, _part_number


    def run(self) -> None:
        """
        This is the process context in which we run the SPS.
        Create all relevant objects from here!
        """

        SM = None
        proc_name = self.name
        n = 0
        _udi = None
        while True:
            if not SM:
                # need to create a new State Machine to work with
                # get configuration from DSP + DB connection
                program_sequence, sequence_revision, resource_str, part_number = self.collect_parameters()
                print("Create new SPS state machine")
                SM = SPSStateMachine(resource_str, program_sequence,
                                     sequence_rotation=(False if self.enable_udi_scan else True),
                                     start_locked=(True if self.enable_udi_scan else False))
                # let the UI show the correct data
                self.response_queue.put({
                    # global infos
                    "resource_str": SM.dev.get_identification_str(),  # only to inform user about the connected welder
                    "part_number": part_number,
                    "sequence": program_sequence,
                    "revision": sequence_revision,
                    # infos about the current sequence
                    "counter": SM.sequence_pos,
                    "program": SM.next_program_no,
                    "udi": _udi,
                })
            if not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd is None:
                    # Poison pill means shutdown
                    print(f"{proc_name}: Exiting")
                    if SM: SM.dev.unlock_machine_step()  # make sure the Welder is unlocked
                    self.command_queue.task_done()
                    break
                print(f"{proc_name}: {cmd}")
                if "udi_scanned" in cmd:
                    # forward the UDI to the UI
                    _udi = cmd["udi_scanned"]
                    self.response_queue.put({"udi_scanned": _udi})
                    # need to reset the sequence
                    SM.close()
                    SM = None  # let the SM be reconstructed to catch a change in sequence and/or part number
                    answer = "OK"
                if "move_counter" in cmd:
                    if ENABLE_UDI_SCAN:
                        if _udi:
                            SM.move_seqence_step(int(cmd["move_counter"]))
                        answer = "OK"
                    else:
                        # no UDI control
                        SM.move_seqence_step(int(cmd["move_counter"]))
                        answer = "OK"
                if "reset_counter" in cmd:
                    #SM.reset_seqence()
                    SM.close()
                    SM = None  # let the SM be reconstructed to catch a change in sequence and/or part number
                    answer = "OK"
                self.command_queue.task_done()
                self.response_queue.put(answer)
            else:
                SM.do_one_loop()
                if SM.state == SPSStates.SHOW_RESULT:
                    # finished
                    self.response_queue.put({"result": "pass", "udi": _udi})
                    _udi = None
                    #SM.close()
                    #SM = None  # let the SM be reconstructed to catch a change in sequence and/or part number
                if SM.state == SPSStates.SET_PROGRAM_ON_MACHINE:
                    self.response_queue.put({"counter": SM.sequence_pos, "program": SM.next_program_no})
                if SM.state == SPSStates.SHOW_PROGRAM_STEP:
                    self.response_queue.put({"counter": SM.sequence_pos, "program": SM.program_no})
        return


#--------------------------------------------------------------------------------------------------
# *** SCANNER ***
#
class ProcessScanner(mp.Process):

    def __init__(self, sps_queue: mp.Queue, ui_queue: mp.Queue) -> None:
        mp.Process.__init__(self)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.sps_queue = sps_queue
        self.ui_queue = ui_queue

    def collect_parameters(self) -> str:
        """ Read configuration for scanner resource.

        Note: this is called from process context,
              do NOT call it from anywhere else except you want to test this function only!

        """
        try:
            cfg = StationConfiguration("CELL_WELDING") #, filename=CONF_FILENAME_DEV)
        except FileNotFoundError:
            # comfort for test & development
            cfg = StationConfiguration("CELL_WELDING", filename=CONF_FILENAME_DEV)
        welder, scanner = cfg.get_resource_strings_for_socket(0)
        return scanner

    def run(self) -> None:
        """
        This is the process context in which we run the scanner.
        Create all relevant objects from here!
        """
        proc_name = self.name
        resource_str = self.collect_parameters()
        scanner = create_barcode_scanner(resource_str)

        while True:
            _udi = None
            # try:
            #     _udi = scanner.request(None, timeout=10.0)
            # except TimeoutError:
            #     pass  # this is ok to keep the loop running
            # except Exception as ex:
            #     # this is a real failure to stop this process
            #     print(f"Cannot connect scanner {resource_str}: {ex}")
            #     print(f"{proc_name}:End")
            #     return
            # if _udi:
            #     msg = {"udi_scanned": _udi}
            #     #self.ui_queue.put(msg)  # this goes to the UI process
            #     self.sps_queue.put(msg)   # this goes to the SPS process

            # ********** Simulationsprofil *************
            sleep(5.0)
            _udi = "1CELL" + get_random_digits_string(12)
            self.sps_queue.put({"udi_scanned": _udi})
            for n in range(19):
                sleep(0.5)
                self.sps_queue.put({"move_counter": 1})
            # *******************************************

        return


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    ## Initialize the logging
    from rrc.custom_logging import logger_init
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--development", action="store_true", help="Activate development mode.")
    args = parser.parse_args()

    ENABLE_UDI_SCAN = 0 if args.development else 1

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
        if ENABLE_UDI_SCAN or not ENABLE_UDI_SCAN:
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