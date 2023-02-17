import multiprocessing
import itertools
import tkinter as tk
import tkinter.ttk as ttk
from time import sleep, perf_counter
from pathlib import Path

from rrc.modbus.aws3 import AWS3Modbus

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
        self.var_label = tk.StringVar(self.root, "-1")
        self.root.withdraw()  # hide window
        self.root.title(title)
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "ui" / "robot-icon.ico")
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "ui" / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        # Set a minsize for the window, and place it in the middle
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        _w = 375  # width set manually
        _h = 485  # height set manually
        _x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
        _y = int((self.root.winfo_screenheight() / 2) - (_h / 2))
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")
        # self.root.columnconfigure(0, weight=10)
        # self.root.columnconfigure(1, weight=1)
        # self.root.columnconfigure(2, weight=1)
        #
        # setup widgets
        #
        self.mainframe = ttk.Frame(self.root, padding="15 15 15 15", takefocus=True)
        # Create a Frame for input widgets
        self.mainframe.grid(
            row=0, column=0, columnspan=2, #rowspan=3, #padx=10, pady=(30, 10),
            sticky=tk.NSEW
        )

        # Make the app responsive
        #self.mainframe.columnconfigure(index=0, weight=1)
        # sticky − What to do if the cell is larger than widget.
        #          By default, with sticky='', widget is centered in its cell.
        #          sticky may be the string concatenation of zero or more of N, E, S, W, NE, NW, SE, and SW
        #          compass directions indicating the sides and corners of the cell to which widget sticks.
        # Label
        label1 = ttk.Label(
            self.mainframe,
            text="NEXT PROGRAM",
            justify="center",
            font=("-size", 12, "-weight", "bold"),
        )
        label1.grid(row=next(row_itr), column=0, sticky=tk.NSEW)
        label2 = ttk.Label(
            self.mainframe,
            textvariable=self.var_label,
            justify="center",
            font=("-size", 28, "-weight", "bold"),
        )
        label2.grid(row=next(row_itr), column=0)
        # Buttons
        step_back_button = ttk.Button(self.mainframe, text="ONE STEP BACK",  style="Accent.TButton",
            command=lambda: self.q_cmd.put({"move_counter": -1}))
        #cancel_button.bind("<Return>", _cancel )
        #cancel_button.bind("<Key-Escape>", _cancel)
        step_back_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, sticky=tk.NSEW)
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
        step_back_button.focus_set()


    def process_command_queue(self):
        if not self.q_res.empty():
            a = self.q_res.get()
            print(a)
            if a and "counter" in a:
                self.var_label.set(a["counter"])
                self.root.update()
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())


    def run_mainloop(self):
        self.root.mainloop()

#--------------------------------------------------------------------------------------------------

class ProcessSPS(multiprocessing.Process):

    def __init__(self, command_queue: multiprocessing.JoinableQueue, response_queue: multiprocessing.Queue):
        multiprocessing.Process.__init__(self)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.command_queue = command_queue
        self.response_queue = response_queue

    def run(self):
        proc_name = self.name
        n = 0
        toc = perf_counter()
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
                    n = n + int(cmd["move_counter"])
                if "reset_counter" in cmd:
                    n = int(cmd["reset_counter"])

                answer = "Hallejulia"
                self.command_queue.task_done()
                self.response_queue.put(answer)
            else:
                tic = perf_counter()
                if tic - toc > 1.0:
                    toc = perf_counter()
                    print("Chhhhr....")
                    self.response_queue.put({"counter": n})
                    n += 1
        return


if __name__ == '__main__':
    ## Initialize the logging
    from rrc.custom_logging import logger_init
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # Establish communication queues
    q_cmd = multiprocessing.JoinableQueue()
    q_res = multiprocessing.Queue()
    # start sub-process for SPS
    p = ProcessSPS(q_cmd, q_res)
    # start UI in this process waiting for user input
    w = WindowUI(q_cmd, q_res)
    p.start()
    w.run_mainloop()
    # Add a poison pill for SPS process
    q_cmd.put(None)
    # Wait for SPS process to finish
    q_cmd.join()

# END OF FILE