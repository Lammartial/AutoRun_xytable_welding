from typing import Tuple
from datetime import datetime, timedelta
from pathlib import Path
import ctypes
import queue
import threading
import asyncio
import tkinter as tk     # platform independent GUI
from tkinter.messagebox import showerror
from tkinter import ttk  # more modern TKinter with widget support

#import eth2uart.wsocket_scanner as wsocket # communication with the ETH-to-UART bridge
from rrc.barcode_scanner import DEBUG as wsocket_DEBUG, tcp_send_and_receive_from_server # communication with the ETH-to-UART bridge

DEBUG = 0   # set to 0 for production

app = None  # holds the GUI object running tkinter in main task and
            # socket service in separate thread using asyncio inside
entered_udi: str = None

#--------------------------------------------------------------------------------------------------
def udi_cancel():
    global app, entered_udi

    entered_udi = None  # signal not to continue testing
    app.close()
    #root.destroy()
    #root.quit()

def udi_accept(udi: str):
    global app, entered_udi

    entered_udi = udi.strip()
    if DEBUG:
        print("ACCEPT:", udi)
    #root.destroy()
    #root.quit()
    app.close()

#--------------------------------------------------------------------------------------------------
class DialogWin(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)

        # Make the app responsive
        for index in [0]:
            self.columnconfigure(index=index, weight=1)
            self.rowconfigure(index=index, weight=1)

        # Create control variables
        #self.var_1 = tk.BooleanVar(value=True)
        # self.var_2 = tk.BooleanVar()
        # self.var_3 = tk.IntVar(value=2)
        # self.var_4 = tk.StringVar(value=self.option_menu_list[1])
        # self.var_5 = tk.DoubleVar(value=75.0)
        self.var_udi = tk.StringVar(value="")

        # Create widgets :)
        self.setup_widgets()

    def setup_widgets(self):

        def _accept_udi(*args, **kwargs):
            if DEBUG:
                print("Arguments:", args, kwargs)
            _udi = self.var_udi.get()
            if _udi != "":
                udi_accept(_udi)
            else:
                if DEBUG:
                    print("Nothing entered as UDI!")

        def _cancel(*args, **kwargs):
            if DEBUG:
                print("Arguments:", args, kwargs)
            udi_cancel()

        # Create a Frame for input widgets
        self.widgets_frame = ttk.Frame(self, padding=(0, 0, 0, 10))
        self.widgets_frame.grid(
            row=0, column=0, padx=10, pady=(30, 10), sticky="nsew", rowspan=3
        )
        self.widgets_frame.columnconfigure(index=0, weight=1)

        # Label
        self.label = ttk.Label(
            self.widgets_frame,
            text="Scan or Enter the UID of Device under Test",
            justify="center",
            font=("-size", 12, "-weight", "bold"),
        )
        self.label.grid(row=0, column=0, pady=10, columnspan=2)

        # Entry
        self.entry = ttk.Entry(
            self.widgets_frame,
            textvariable=self.var_udi,
            font=("-size", 15),
        )
        self.entry.insert(0, "")
        self.entry.bind("<Return>", _accept_udi )
        self.entry.bind("<Key-Escape>", _cancel)
        self.entry.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")
        self.entry.focus()

         # Button
        self.ok_button = ttk.Button(self.widgets_frame, text="Start Test", style="Accent.TButton", command=_accept_udi)
        self.ok_button.bind("<Return>", _accept_udi)
        self.ok_button.bind("<Key-Escape>", _cancel)
        self.ok_button.grid(row=2, column=0, padx=5, pady=10, sticky="nsew")

        # Separator
        self.separator = ttk.Separator(self.widgets_frame)
        self.separator.grid(row=3, column=0, padx=(20, 10), pady=10, sticky="ew")

        # Button
        self.cancel_button = ttk.Button(self.widgets_frame, text="Cancel", command=_cancel)
        self.cancel_button.bind("<Return>", _cancel )
        self.cancel_button.bind("<Key-Escape>", _cancel)
        self.cancel_button.grid(row=4, column=0, padx=5, pady=10, sticky="nsew")

        # # Sizegrip
        # self.sizegrip = ttk.Sizegrip(self)
        # self.sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))

#--------------------------------------------------------------------------------------------------
async def scan_uart_socket(timeout=0.5, message=None, debug_end_time=None):
    """
    Calls the send & receive from socket function. We need this trampoline
    function for the async call, as we do not need the whole App class to be async.

    Args:
        timeout (float, optional): Limits the wait for send/receive time on the socket. Defaults to 0.5.
        message (_type_, optional): If given this message will be sent to the socket before reading. Defaults to None.
        debug_end_time (_type_, optional): Only for DEBUG support to set a response after the end_time. Defaults to None.
    """
    global app

    data = await tcp_send_and_receive_from_server(message, timeout=timeout)  # this timeout is for open and send/receive
    if data:
        app.gui_queue.put({"udi":data})

    # DEBUG / SIMULATION SUPPORT
    if debug_end_time is not None:
        if datetime.now() > debug_end_time:
            _sim_udi = round(datetime.now().timestamp() * 1e+6, 0)
            app.gui_queue.put({"udi":f"SIM{_sim_udi:.0f}"})

#
# When there is a need for more parallel tasks, we can put them into a fire and forget more
# but they need to have a strong reference to protect against GC
#
# Example:
# background_tasks = set()
# async def run_in_background(some_coroutine):
#     # Create "fire and forget" task
#     task = asyncio.create_task(some_coroutine(param=i))
#     # Add task to the set. This creates a strong reference.
#     background_tasks.add(task)
#     # To prevent keeping references to finished tasks forever,
#     # make each task remove its own reference from the set after
#     # completion:
#     task.add_done_callback(background_tasks.discard)
#
#--------------------------------------------------------------------------------------------------
class App(threading.Thread):
    """
    This application class combines the GUI task with a background service task that is connected to
    a socket for UDI input.
    After creation simply run the start_gui() function of this class which starts both tasks and waits
    for completion.

    The result is being put into the global "entered_udi" by using the glibal callbacks udi_accept() or
    udi_cyncel().

    Args:
        threading (Thread): Base class to have the background task available under full control.
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0)  # this hides the root window until we have arranged all the wigets
        self.root.title("ENTER UID")
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "app-icon.ico")
        # if only PNG or JPG available we need to convert:
        #photo = tk.PhotoImage(file="app-icon.png")
        #self.root.wm_iconphoto(False, photo)
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        # create the Widgets and keep them inside our App object
        self.dialog = DialogWin(self.root)
        self.dialog.pack(fill="both", expand=True)
        # Set a minsize for the window, and place it in the middle
        self.root.update()
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        x_cordinate = int((self.root.winfo_screenwidth() / 2) - (self.root.winfo_width() / 2))
        y_cordinate = int((self.root.winfo_screenheight() / 2) - (self.root.winfo_height() / 2))
        self.root.geometry("+{}+{}".format(x_cordinate, y_cordinate-20))
        self.root.attributes('-alpha', 1.0)  # now make the main window visible again
        self.root.protocol("WM_DELETE_WINDOW", self.callback)
        self.gui_queue = queue.Queue()
        threading.Thread.__init__(self)
        self.name = "DAHINTER"
        # to stop the Background task use either this signal:
        self._stop_event = threading.Event()
        # or the function self.raise_exception()

    def get_id(self):
        """Needed to terminate this thread by SystemExit exception.

        Returns:
            int: thread id
        """
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        """
        Robust termination function for this thread using asynchronous SystemExit
        exception on thread.

        Raises:
            failure: SystemExit exception to terminate the thread
        """
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print("Exception raise failure")

    def stop(self):
        self._stop_event.set()
        if DEBUG:
            print("THREAD STOP FLAG SET.")

    def stopped(self):
        return self._stop_event.is_set()

    def close(self):
        self.stop()             # signal to the thread
        #self.raise_exception()  # hardly stop the thread
        #self.root.quit()        # soft stop (leaves stale app when used with Teststand)
        self.root.destroy()     # hard stop
        self.join()             # wait until the background service thread has ended

    def callback(self):
        """called from window manager close/quit function (cross right upper corner)."""
        if DEBUG:
            print("CALLBACK TO CLOSE.")
        #self.raise_exception()
        udi_cancel()


    def run(self):
        """Runs the background task in parallel to the GUI in the main task."""
        global DEBUG

        try:
            if DEBUG:
                end_time = datetime.now() + timedelta(seconds=10) # DEBUG / Simulation
                msg = "GIB MIR BYTES, SCANNER!" # DEBUG
            else:
                end_time = None
                msg=None
            # this is the background task function
            while not self.stopped():
                asyncio.run(scan_uart_socket(
                    timeout=0.5,
                    message=msg,              # DEBUG
                    debug_end_time=end_time,  # DEBUG
                    ))
            if DEBUG:
                print(f"Thread {self.name} signalled gracefully by stop flag.")
        except SystemExit as ex:
            if DEBUG:
                print(f"Thread {self.name} terminated hardly by exception.")
        except asyncio.exceptions.TimeoutError:
            ermsg = "Cannot connect to TCP server."
            if DEBUG:
                print(ermsg)
            app.gui_queue.put({"error": ermsg})
        finally:
            if DEBUG:
                print(f"Thread {self.name} ended.")


    def periodic_gui_update(self):
        """
        Using a simple timed GUI task every 0.1s to check the incoming message queue.
        This way we can automatically accept UDI by remote UART.
        When an udi dict is received, we propagate it to the UI variable and trigger
        the accept funtcion to close the GUI and return to Teststand.
        """

        # we are using the Queue to get data from background task
        try:
            fn = self.gui_queue.get_nowait()
            if fn:
                if DEBUG:
                    print(fn)
                if isinstance(fn, dict):
                    if "udi" in fn:
                        _udi = fn["udi"]
                        self.dialog.var_udi.set(_udi)
                        udi_accept(_udi)  # auto accept!
                    if "error" in fn:
                        showerror("Error", fn["error"])
                        udi_cancel()  # stop application!
        except queue.Empty:
            pass
        finally:
            pass
        #if DEBUG:
        #    print("Restart GUI update.")
        self.root.after(100, self.periodic_gui_update)


    def start_gui(self):
        """
        Starts a parallel task for UART service and runs the GUI in this
        (main) task and blocks until the GUI has been closed.
        """

        self.start()          # start background service thread
        self.root.after(10, self.periodic_gui_update)
        self.root.mainloop()  # GUI loop


#--------------------------------------------------------------------------------------------------
def identify_uut(context) -> Tuple[bool, str]:
    """Entry function for TestStand.

    Args:
        context (dict): TestStand context - unused right now

    Returns:
        Tuple[bool, str]: return values to a TestStand container that expects two types in this order.
    """
    global app, entered_udi

    entered_udi = None  # reset here
    app = App()
    app.start_gui()  # this runs Window Dialog in separate task and blocks until GUI is closed
    if entered_udi is not None:
        return (True, entered_udi)
    else:
        return (False, "")

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    DEBUG = 0  # increase verbosity
    wsocket_DEBUG = DEBUG # to see more infos
    continue_testing, udi = identify_uut({})
    print(f"FINALIZED {entered_udi}. Continue testing: {continue_testing}, udi={udi}")

# END OF FILE