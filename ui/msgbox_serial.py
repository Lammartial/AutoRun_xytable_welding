from typing import List, Tuple, Callable
from enum import Enum
import random
import string
import multiprocessing as mp
import itertools
import tkinter as tk
import tkinter.ttk as ttk
from hashlib import md5
from base64 import b64decode, b64encode
from time import sleep, perf_counter
from pathlib import Path
from datetime import timezone, datetime
from rrc.barcode_scanner import create_barcode_scanner, decode_rrc_product_serial_label, decode_rrc_udi_label


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init
# --------------------------------------------------------------------------- #

SIMULATE_SCAN = 1

q_cmd: mp.Queue

class SerialNoScanCtrlItem:
    var: tk.StringVar      # tkinter variable to hold the scanned UDI
    name: str              # title to show for that UDI
    validate: Callable   # None or function that checks UDI to accept
    scanned_udi: str       # None or the scan

    def __init__(self, name: str | None, validate: Callable | None) -> None:
        self.var=None
        self.name=name
        self.validate=validate
        self.scanned_udi=None

serialno_to_scan = [SerialNoScanCtrlItem(None, None)]
allow_manual_edit: bool = False
block_accept: bool = True
ok_button = None

#--------------------------------------------------------------------------------------------------

def validate_udi_by_rrc_udi_decoder(udi: str, v_str: str) -> bool:
    """Verify the UDI with our UDI decoder just using the correct sorting key here."""
    result, _ = decode_rrc_udi_label(udi)
    if v_str in result:  # check if the correct UDI type is decoded
        return True
    return False


def validate_all(udi: str, v_str: str) -> bool:
    return True

#--------------------------------------------------------------------------------------------------

class WindowUI(object):
    """ Run tkinter.

    This runs in the Main Thread.
    """

    def __init__(self, command_queue: mp.Queue,
                 title: str = "ENTER SERIAL NUMBER", test_socket: int = -1, 
                 allow_manual_edit: bool = False) -> None:

        global serialno_to_scan, ok_button

        self._log = getLogger(__name__, DEBUG)
        self.q_cmd = command_queue
        row_itr = itertools.count()    
      
        # Create the Tk root and mainframe.
        self.root = tk.Tk()


        def _accept_udi(parent):
            global serialno_to_scan, block_accept
            if block_accept: return
            for item in serialno_to_scan:
                item.scanned_udi = item.var.get()  # transfer from each tkinter widget into the result space
            self.root.destroy()

        def _cancel(parent):
            global serialno_to_scan
            for item in serialno_to_scan:
                item.scanned_udi = None
            self.root.destroy()

        #---for test only---

        def validate_entry(entry, action: str, index: str, current: str, change: str, trigger: str) -> bool:
            global block_accept
            #print(f"{entry},{action},{index},{current},{change},{trigger}")
            if trigger in ["key", "focusout"]:
                _s = current
                if action == "0":
                    index = int(index)
                    _s = current[:index] + current[index+len(change):]
                if action == "1":
                    index = int(index)
                    _s = current[:index] + change + current[index:]
                #print(_s)
                if len(_s)<4:
                    block_accept = True
                else:
                    block_accept = False
            if trigger == "focusout":
                if block_accept:
                    return False
                else:
                    return True
            return True

        # def on_invalid_entry(wname, newstr, oldstr):
        #     global block_accept_udi
        #     #print(f"{wname},{newstr},{oldstr}")
        #     #entry = self.root.nametowidget(wname)
        #     #entry.delete(0, tk.END)
        #     block_accept_udi = True
        #     return

        #-------------------

        self.root.withdraw()  # hide window
        self.root.title(title)
        self.root.iconbitmap(Path(__file__).resolve().parent / "scan-icon.ico")
        self.root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        #style.theme_use("alt")

        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        # Set a minsize for the window, and place it in the middle
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        _w = 375  # width set manually
        _h = 485  # height set manually
        if test_socket < 0:
            _x = int((self.root.winfo_screenwidth() / 2) - (_w / 2))
            _y = int((self.root.winfo_screenheight() / 2) - (_h / 2))
            self.root.geometry(f"+{_x}+{_y}")
        else:
            _x = 250 + test_socket * (_w + 100)
            _y = 100
            self.root.geometry(f"+{_x}+{_y}")
        #
        # create the Widgets and keep them inside our object
        #
        _padall = 15      
        self.mainframe = ttk.Frame(self.root, pad=(_padall,_padall,_padall,_padall), takefocus=True)
       
        # Create a Frame for input widgets
        #self.mainframe.grid(row=0, column=0, sticky="NESW")
        self.mainframe.grid(
            row=0, column=0, padx=10, pady=(30, 10),
            sticky="NSEW", rowspan=3
        )
        #self.mainframe.columnconfigure(index=0, weight=1)        
        self.mainframe.grid_columnconfigure(0, weight=1)
        #self.mainframe.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        #self.root.grid_columnconfigure(0, weight=1)

        # sticky − What to do if the cell is larger than widget.
        #          By default, with sticky='', widget is centered in its cell.
        #          sticky may be the string concatenation of zero or more of N, E, S, W, NE, NW, SE, and SW
        #          compass directions indicating the sides and corners of the cell to which widget sticks.

        # Label
        label = ttk.Label(
            self.mainframe,
            text="Scan or Enter the Serial Number of Device under Test",
            justify="center", font=("-size", 12, "-weight", "bold"),
        )
        label.grid(row=next(row_itr), column=0, columnspan=2 , pady=10)

        # Entry
        entry_lst = []
        for item in serialno_to_scan:
            # Create control variables
            item.var = tk.StringVar(value="")
            _row = next(row_itr)
            _col = 0
            _label = None
            if item.name:
                _label = ttk.Label(self.mainframe, text=item.name)
                _label.grid(row=_row, column=_col, padx=5, pady=(0, 10), sticky="ew")
                _col += 1
            entry = ttk.Entry(
                self.mainframe,
                state=tk.NORMAL if allow_manual_edit else tk.DISABLED,
                textvariable=item.var,
                font=("-size", 15),
            )     
            entry.configure(validate="all",
                validatecommand=(self.root.register(validate_entry), "%W", "%d", "%i", "%s", "%S", "%V"),
                #invalidcommand=(self.root.register(on_invalid_entry), '%W', '%s', '%S'),
            )
            entry.insert(0, "")
            entry.bind("<Return>", _accept_udi )
            entry.bind("<Key-Escape>", _cancel)
            entry.grid(row=_row, column=_col, padx=5, pady=(0, 10), sticky="ew")
            entry_lst.append((_label, entry))

        # Button - need hidden to close the window programmatically
        ok_button = ttk.Button(self.mainframe, text="Start Test", style="Accent.TButton", command=lambda: _accept_udi(None))
        ok_button.bind("<Return>", _accept_udi)
        ok_button.bind("<Key-Escape>", _cancel)
        ok_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, padx=5, pady=10, sticky="nsew")
        ok_button.grid_forget()

        # Separator
        separator = ttk.Separator(self.mainframe)
        separator.grid(row=next(row_itr), column=0, columnspan=2, padx=(20, 10), pady=10, sticky="ew")

        # Button
        cancel_button = ttk.Button(self.mainframe, text="Cancel", command=lambda: _cancel(None))
        cancel_button.bind("<Return>", _cancel )
        cancel_button.bind("<Key-Escape>", _cancel)
        cancel_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, padx=5, pady=10, sticky="nsew")
             
        # schedule queue processing callback
        self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)

        if allow_manual_edit:
            entry_lst[0][1].focus_set()   # now set the focus to the first dialog element
        else:
            cancel_button.focus_set()
     
    
    def process_command_queue(self):
        global serialno_to_scan
      
        if not self.q_cmd.empty():
            a = self.q_cmd.get()
            #print("UI:", a)
            _do_update = False
            if a:               
                if "part_number" in a:
                    #self.var_label_part_number.set(a["part_number"])
                    print("UI:UPDATE PART NUMBER")
                    _do_update = True               
                if "serial_number" in a:
                    if a["serial_number"] is None:
                        #self.label_udi.config(background="gray", foreground="black")
                        #self.var_label_udi.set("PLEASE SCAN UDI")
                        print("UI:RESET SERIAL")
                    else:
                        # check which dialog gets the serial
                        #self.label_udi.config(background="blue", foreground="white")
                        #self.var_label_udi.set(a["udi"])
                        # validate UDI
                        _valid_sn = False
                        _sn = a["serial_number"]
                        for item in serialno_to_scan:
                            if item.validate is not None:
                                if item.validate(_sn, item.name):  # execute the validation function
                                    item.var.set(_sn)   # set the UDI
                                    _valid_sn = True    # avoid pop-up
                        if not _valid_sn:
                            #showinfo("Window", f"Wrong UDI code type {_udi}")
                            _log.warning(f"Wrong Serial code type {_sn}")
                        else:
                            # check if we are complete:
                            _stop = all([(item.var.get() not in [None, ""]) for item in serialno_to_scan])
                            if _stop:
                                #mainframe.master.withdraw()
                                #mainframe.master.destroy()
                                global ok_button, block_accept
                                block_accept = False
                                ok_button.invoke()
                                # do NOT reschedule after()
                                return
                    _do_update = True
                if "part_name" in a:
                    #self.label_udi.config(background="lightblue", foreground="black")
                    #self.var_label_udi.set(a["udi_scanned"])
                    print("UI:UPDATE PART NAME")
                    _do_update = True
                if "date_code" in a:
                    #self.label_udi.config(background="orange", foreground="black")
                    #self.var_label_udi.set("UDI REJECTED")
                    print("UI:DATE CODE")
                    _do_update = True
                    pass                    
            if _do_update:
                self.root.update()
        self._id_after = self.mainframe.after(50, lambda: self.process_command_queue())


    def run_mainloop(self):
        self.root.mainloop()


#--------------------------------------------------------------------------------------------------
# *** SCANNER ***
#

def get_random_letter_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    numbers = string.digits
    return "".join(random.choice(letters) for i in range(length))

def get_random_digits_string(length):
    # choose from all digits
    numbers = string.digits
    return "".join(random.choice(numbers) for i in range(length))


class ProcessScanner(mp.Process):

    def __init__(self, resource_string: str, ui_queue: mp.Queue) -> None:
        mp.Process.__init__(self)  # super() init does not work here!
        global DEBUG, SIMULATE_SCAN
        self._log = getLogger(__name__, DEBUG)
        self.resource_string = resource_string
        self.ui_queue = ui_queue
        self.simulate_scan = SIMULATE_SCAN

    def run(self) -> None:
        """
        This is the process context in which we run the scanner.
        Create all relevant objects from here!
        """
        proc_name = self.name
        resource_str = self.resource_string
        print("HELLO FROM SCANNER") 
        if not self.simulate_scan:
            scanner = create_barcode_scanner(resource_str)
            while True:
                _records = None
                try:
                    _raw = scanner.request(None, timeout=None, encoding="utf-8")
                    _records = decode_rrc_product_serial_label(_raw)
                except TimeoutError:
                    pass  # this is ok to keep the loop running
                except Exception as ex:
                    # this is a real failure to stop this process
                    print(f"Cannot connect scanner {resource_str}: {ex}")
                    print(f"{proc_name}:End")
                    return
                if _records:
                    msg = {"udi_scanned": _records}
                    self.ui_queue.put(_records)  # this goes to the UI process
        else:
            # ********** Simulation Profile *************
            #while True:
            sleep(5.0)
            _records = {
                "serial_number": "1CELL" + get_random_digits_string(12)
            }
            print("PUT SCAN")
            self.ui_queue.put(_records)
            sleep(3.0)


#--------------------------------------------------------------------------------------------------

def scan_serial_label(resource_string: str, title: str = "ENTER SERIAL", test_socket: int = -1):
    w = None
    s = None
    try:
        # Establish communication queues
        q_cmd = mp.Queue()
        # start sub-process for SPS
        # start UI in this process waiting for user input
        w = WindowUI(q_cmd, allow_manual_edit=True)
        # start sub-process for scanner
        s = ProcessScanner(resource_string, q_cmd)
        s.start()
        w.run_mainloop()
    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        if s and s.is_alive():
            s.terminate()
            s.join(timeout=0.5)  # short process ...

#--------------------------------------------------------------------------------------------------

def identify_uut(test_socket: int, requested_serial: list, scanner_resource_str: str, allow_user_edit:bool = False) -> Tuple[bool, str]:
    """Entry function for TestStand using context IDispatch interface (block of data)

    Args:
        context (dict): TestStand context

    Returns:
        Tuple[bool, str]: return values to a TestStand container that expects two types in this order.
    """
    global serialno_to_scan, allow_manual_edit

    _log = getLogger(__name__, DEBUG)
    allow_manual_edit = allow_user_edit
    #allow_manual_edit = True
    # # this is just to demonstrate the parameter passing from TestStand
    # context_id = seq_context.Id
    # executing_sequence_name = seq_context.Sequence.Name
    # executing_step_name = seq_context.Step.Name

    title = "ENTER SERIAL" if int(test_socket) < 0 else f"SOCKET {int(test_socket)}: ENTER SERIAL"

    _scanner = scanner_resource_str
    serialno_to_scan = [
        SerialNoScanCtrlItem(item, validate_all) for item in requested_serial
    ]
    scan_serial_label(_scanner, title=title, test_socket=int(test_socket))
    res = tuple()
    for item in serialno_to_scan:
        _log.debug(f"UDI({item.name})={item.scanned_udi}")
        res += (item.scanned_udi,)
    if all(res):
        # all elements not None -> no conversion
        return (True,) + res
    else:
        # convert None to "" to avoid exception
        return (False,) + tuple([s if s else "" for s in res])


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    logger_init(filename_base=None)
    _log = getLogger(__name__, DEBUG)

    # need to initialize logger on load
    #scan_serial_label("COM7:9600,8N1")
    res = identify_uut(-1, [""], "COM7:9600,8N1")
    print(res)


# END OF FILE