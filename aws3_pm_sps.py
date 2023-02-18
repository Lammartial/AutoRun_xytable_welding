from typing import List
from enum import Enum
import multiprocessing
import itertools
import tkinter as tk
import tkinter.ttk as ttk
from time import sleep, perf_counter
from pathlib import Path

from rrc.modbus.aws3 import AWS3Modbus
# import SQL managing modules
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from rrc.dbcon.connection import get_protocol_db_connector

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0   # set to 0 for production

from rrc.custom_logging import getLogger

# --------------------------------------------------------------------------- #

class WindowUI(object):

    def __init__(self, command_queue: multiprocessing.JoinableQueue, response_queue: multiprocessing.Queue, title: str = "POOR MAN'S SPS"):
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        self.q_res = response_queue
        row_itr = itertools.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()
        self.var_label_counter = tk.StringVar(self.root, "-1")
        self.var_label_program = tk.StringVar(self.root, "-1")
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
        # Set a minsize for the window, and place it in the middle
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        _w = 280  # width set manually
        _h = self.root.winfo_screenheight() #480  # height set manually
        #_x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        _x = int(self.root.winfo_screenwidth() - _w)
        _y = int((self.root.winfo_screenheight() / 2) - (_h / 2))
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")
        # self.root.columnconfigure(0, weight=10)
        # self.root.columnconfigure(1, weight=1)
        # self.root.columnconfigure(2, weight=1)
        #
        # setup widgets
        #
        self.mainframe = ttk.Frame(self.root, pad=(15,15,15,15), takefocus=True)
        self.mainframe.pack(fill=tk.BOTH)
        #self.mainframe.grid(row=0, column=0, sticky=tk.EW)
        #self.root.grid_columnconfigure(0,weight=1)
        #self.root.grid_rowconfigure(0,weight=1)
        # Create a Frame for input widgets
        # self.mainframe.grid(
        #     row=0, column=0, columnspan=2, #rowspan=3, #padx=10, pady=(30, 10),
        #     sticky=tk.NSEW
        # )

        # Label
        _row = next(row_itr)
        label0 = ttk.Label(
            self.mainframe,
            text="SEQUENCE POS",
            justify="center",
            font=("-size", 10, "-weight", "bold")
        )
        label0.grid(row=_row, column=0, columnspan=2, ipadx=10, ipady=10)
        label00 = ttk.Label(
            self.mainframe,
            textvariable=self.var_label_counter,
            justify="center",
            font=("-size", 10, "-weight", "bold"),
        )
        label00.grid(row=_row, column=1, ipadx=10, ipady=10)

        label1 = ttk.Label(
            self.mainframe,
            text="PROGRAM",
            justify="center",
            font=("-size", 18, "-weight", "bold"),
        )
        label1.grid(row=next(row_itr), column=0, columnspan=2, ipadx=10, ipady=10)
        label2 = ttk.Label(
            self.mainframe,
            textvariable=self.var_label_program,
            justify="center",
            font=("-size", 32, "-weight", "bold"),
        )
        label2.grid(row=next(row_itr), column=0, columnspan=2, ipadx=10, ipady=10)
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
        reset_seq_button.focus_set()


    def process_command_queue(self):
        if not self.q_res.empty():
            a = self.q_res.get()
            #print("UI:", a)
            if a and "counter" in a:
                self.var_label_counter.set(a["counter"])
                self.root.update()
            if a and "program" in a:
                self.var_label_program.set(a["program"])
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
    WAIT_READY_TO_INIT = 0
    INIT = 1
    WAIT_READY_TO_SYNC_ON_MACHINE_COUNTER = 2
    SYNC_ON_MACHINE_COUNTER = 3
    SHOW_PROGRAM_STEP = 4
    FETCH_NEXT_PROGRAM = 5
    WAIT_READY_TO_SET_PROGRAM = 6
    SET_PROGRAM_ON_MACHINE = 7


class SPSStateMachine(object):

    def __init__(self, dev: AWS3Modbus | str, program_sequence: List[int] = [1]) -> None:
        self.state: SPSStates = SPSStates.INIT
        self.program_sequence = program_sequence
        self.counter_base_ax1 = None
        self.program_no_base = -1
        self.sequence_pos = -1
        self.next_program_no = -1
        self.last_counter_ax1 = -1
        self._machine_locked = None
        self._throttle_pause = 0.055
        if isinstance(dev, str):
            self.dev = AWS3Modbus(dev)
        else:
            self.dev = dev
        print(f"Poor man's SPS machine: {self.dev.machine_name}, at {repr(self.dev)}")

    def run_loop(self):
        while True:
            self.do_one_loop()

    def set_state(self, new_state: SPSStates) -> None:
        self.state = new_state

    def _offset_sequence(self, offset: int) -> None:
        self.sequence_pos = (self.sequence_pos + offset) % len(self.program_sequence)

    def move_seqence_step(self, step: int) -> None:
        self._offset_sequence(step)
        self.next_program_no = self.program_sequence[self.sequence_pos]
        self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)

    def reset_seqence(self) -> None:
        self.sequence_pos = 0
        self.next_program_no = self.program_sequence[self.sequence_pos]
        self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)

    def do_one_loop(self):
        try:
            match self.state:
                case SPSStates.WAIT_READY_TO_INIT:
                    if self._machine_locked:
                        self.dev.unlock_machine_step()
                        self._machine_locked = False
                    if self.dev.is_machine_ready():
                        self.set_state(SPSStates.INIT)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.INIT:
                    self.counter_base_ax1 = self.dev.read_axis_counter(1)
                    self._machine_locked = self.dev.read_machine_lock_status()
                    self.program_no_base = self.dev.read_program_no()
                    print(f"Base counters: Ax1={self.counter_base_ax1}")
                    print(f"Base program no: {self.program_no_base}")
                    self.sequence_pos = 0
                    self.last_counter_ax1 = self.counter_base_ax1
                    self.program_no = self.program_no_base
                    self.next_program_no = self.program_sequence[self.sequence_pos]
                    self.set_state(SPSStates.SHOW_PROGRAM_STEP)

                case SPSStates.SHOW_PROGRAM_STEP:
                    print(f"Program step: {self.sequence_pos} of {len(self.program_sequence)}")
                    print(f"Program set {self.program_no}")
                    self.set_state(SPSStates.SYNC_ON_MACHINE_COUNTER)

                case SPSStates.WAIT_READY_TO_SYNC_ON_MACHINE_COUNTER:
                    if self.dev.is_machine_ready():
                        self.set_state(SPSStates.SYNC_ON_MACHINE_COUNTER)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.SYNC_ON_MACHINE_COUNTER:
                    self.counter_ax1 = self.dev.read_axis_counter(1)
                    #  check if we have to moved to the  next program step
                    diffcount = self.counter_ax1["counter"] - self.last_counter_ax1["counter"]
                    if diffcount > 0:
                        self.set_state(SPSStates.FETCH_NEXT_PROGRAM)
                    else:
                        self.set_state(SPSStates.WAIT_READY_TO_SYNC_ON_MACHINE_COUNTER)
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.FETCH_NEXT_PROGRAM:
                    # yes we have finished a cycle -> move to next program step
                    self._machine_locked = True
                    self._offset_sequence(+1)
                    # self.sequence_pos += 1
                    # if self.sequence_pos >= len(self.program_sequence):
                    #     self.sequence_pos = 0
                    self.next_program_no = self.program_sequence[self.sequence_pos]
                    print(f"Move program step to {self.sequence_pos} with program no {self.next_program_no}")
                    self.last_counter_ax1 = self.counter_ax1
                    self.set_state(SPSStates.WAIT_READY_TO_SET_PROGRAM)

                case SPSStates.WAIT_READY_TO_SET_PROGRAM:
                    if self.dev.is_machine_ready():
                        self.set_state(SPSStates.SET_PROGRAM_ON_MACHINE)
                    else:
                        sleep(self._throttle_pause)  # throttle polling

                case SPSStates.SET_PROGRAM_ON_MACHINE:
                    self.dev.lock_machine_step()
                    self._machine_locked = True
                    # check if the correct program step is set
                    self.program_no = self.dev.read_program_no()
                    if self.next_program_no != self.program_no:
                        print(f"Set program {self.next_program_no} on machine.")
                        self.dev.write_program_no(self.next_program_no)
                        self.program_no = self.dev.read_program_no()
                        # ??? check ???
                    else:
                        print(f"Program {self.program_no} already set.")
                    self.dev.unlock_machine_step()
                    self._machine_locked = False
                    self.set_state(SPSStates.WAIT_READY_TO_SYNC_ON_MACHINE_COUNTER)

                case other:
                    self.set_state(SPSStates.WAIT_READY_TO_INIT)

        except AssertionError as ex:
            print("Got ERROR to ignore: ", ex)
        except Exception as ex:
            #raise
            pass  # swallow
        finally:
            # make sure that the welding machine will be unlocked in any failure cases
            if self._machine_locked:
                self.dev.unlock_machine_step()
            # do not change the state here


#--------------------------------------------------------------------------------------------------

class ProcessSPS(multiprocessing.Process):

    def __init__(self, command_queue: multiprocessing.JoinableQueue, response_queue: multiprocessing.Queue,
                       resource_str: str, program_sequence: List[int]) -> None:
        multiprocessing.Process.__init__(self)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.resource_str = resource_str
        self.program_sequence = program_sequence

    def run(self) -> None:
        # get configuration from DSP + DB connection
        srcEngine, SSession = get_protocol_db_connector()
        session = SSession()
        _part_number = "412096-16"
        res = session.execute(sa.text(f"SELECT id,program_sequence,parameter FROM `spsconfig` AS sc WHERE sc.part_number='{_part_number}' ORDER BY id DESC"))
        rows = res.fetchall()
        if len(rows) == 0:
            # not found! -> do not proceed
            raise Exception("No Data in Database found, cannot proceed!")
        self.SM = SPSStateMachine(self.resource_str, self.program_sequence)
        proc_name = self.name
        n = 0
        #toc = perf_counter()
        while True:
            if not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd is None:
                    # Poison pill means shutdown
                    print(f"{proc_name}: Exiting")
                    self.command_queue.task_done()
                    break
                print(f"{proc_name}: {cmd}")
                if "move_counter" in cmd:
                    #n = n + int(cmd["move_counter"])
                    self.SM.move_seqence_step(int(cmd["move_counter"]))
                if "reset_counter" in cmd:
                    #n = int(cmd["reset_counter"])
                    self.SM.reset_seqence()
                answer = "Hallejulia!"
                self.command_queue.task_done()
                self.response_queue.put(answer)
            else:
                self.SM.do_one_loop()
                if self.SM.state == SPSStates.SET_PROGRAM_ON_MACHINE:
                    self.response_queue.put({"counter": self.SM.sequence_pos, "program": self.SM.next_program_no})
                if self.SM.state == SPSStates.SHOW_PROGRAM_STEP:
                    self.response_queue.put({"counter": self.SM.sequence_pos, "program": self.SM.program_no})

                # tic = perf_counter()
                # if tic - toc > 1.0:
                #     toc = perf_counter()
                #     print("Chhhhr....")
                #     self.response_queue.put({"counter": self.SM.program_no})
                #     n += 1
        return


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    ## Initialize the logging
    from rrc.custom_logging import logger_init
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # with AWS3Modbus("tcp:172.21.101.100:502") as dev:
    #     #test_sps_process(dev, program_sequence=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])
    #     #test_sps_process(dev, program_sequence=[1,2,3,4])
    #     test_sps_statemachine(dev, program_sequence=[1,2,3,4])

    p = None
    w = None
    try:
        # Establish communication queues
        q_cmd = multiprocessing.JoinableQueue()
        q_res = multiprocessing.Queue()
        # start sub-process for SPS
        p = ProcessSPS(q_cmd, q_res, "tcp:172.21.101.100:502", [1,2,3,4,5])
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, q_res)
        p.start()
        w.run_mainloop()
    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        if p and p.is_alive():
            # Add a poison pill for SPS process
            q_cmd.put(None)
            # Wait for SPS process to finish
            q_cmd.join()

# END OF FILE