"""
UDI scan dialog for use with Teststand.

May not use Multiprocessing as it does not work well with Teststand!

Need Python 3.10

"""

from cProfile import label
from typing import Callable
import asyncio
import concurrent.futures
import itertools
import queue
import sys
import threading
import time
import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.messagebox import showinfo, showerror, showwarning
from collections.abc import Iterator
from typing import Optional, Tuple
from pathlib import Path
from serial import Serial
from rrc.barcode_scanner import create_barcode_scanner, create_barcode_scanner_with_timeout, decode_rrc_udi_label, decode_rrc_product_serial_label

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0   # set to 0 for production

from rrc.custom_logging import getLogger

# --------------------------------------------------------------------------- #

# Global reference to loop allows access from different environments.
aio_loop: Optional[asyncio.AbstractEventLoop] = None
tk_q: queue.Queue = None
ok_button = None

class UDIScanCtrlItem:
    var: tk.StringVar      # tkinter variable to hold the scanned UDI
    name: str              # title to show for that UDI
    validate: Callable   # None or function that checks UDI to accept
    scanned_udi: str       # None or the scan

    def __init__(self, name: str | None, decode: Callable, validate: Callable | None) -> None:
        self.var = None
        self.name = name
        self.decode = decode
        self.validate = validate
        self.records = None
        self.scanned_udi = None

udi_to_scan = [UDIScanCtrlItem(None, None, None)]
allow_manual_edit: bool = False

#--------------------------------------------------------------------------------------------------

def validate_rrc_udi(records: dict, v_str: str) -> str:
    if v_str in records:  # check if the correct UDI type is decoded
         # return the UDI string reconstructed and stripped from any unreadables
        original = f"{records[v_str]['plant']}{v_str}{records[v_str]['serial_number']}"
        return original
    return None

def validate_rrc_product_serial(records: dict, v_str: str) -> str:
    if all(e in records for e in ["serial_number", "part_name"]):
        return records["serial_number"]    # return the UDI
    return None

#--------------------------------------------------------------------------------------------------

# async def aio_blocking_communication(task_id: int, tk_q: queue.Queue, resource_string: str) -> None:
#     """ Asynchronously block the thread and put a work package into Tkinter's work queue.

#     This is a producer for Tkinter's work queue. It will run in the same thread as the asyncio loop. The statement
#     `await asyncio.sleep(block)` can be replaced with any awaitable blocking code.

#     Args:
#         task_id: Sequentially issued tkinter task number.
#         tk_q: tkinter's work queue.
#         block: block time

#     Returns:
#         Nothing. The work package is returned via the threadsafe tk_q.
#     """

#     _log = getLogger(__name__, DEBUG)
#     dev = create_barcode_scanner(resource_string)
#     while True:
#         _response = await dev.request_async(None)
#         #_response = await dev.request(None)
#         if _response:
#             _log.info(_response)
#         else:
#             continue

#         # Put the work package into the tkinter's work queue.
#         while True:
#             try:
#                 # Asyncio can't wait for the thread blocking `put` method…
#                 tk_q.put_nowait(_response)
#             except queue.Full:
#                 # Give control back to asyncio's loop.
#                 await asyncio.sleep(0)
#             else:
#                 # The work package has been placed in the queue so we're done.
#                 break
#         #break

    # ends by force only


def aio_exception_handler(mainframe: ttk.Frame, future: concurrent.futures.Future, first_call: bool = True) -> None:
    """ Exception handler for future coroutine callbacks.

    This non-coroutine function uses tkinter's event loop to wait for the future to finish.
    It runs in the Main Thread.

    Args:
        mainframe: The after method of this object is used to poll this function.
        future: The future running the future coroutine callback.
        first_call: If True will cause an opening line to be printed on stdout.
    """

    poll_interval = 100  # milliseconds
    try:
        # Python will not raise exceptions during future execution until `future.result` is called. A zero timeout is
        # required to avoid blocking the thread.
        future.result(0)

    # If the future hasn't completed, reschedule this function on tkinter's event loop.
    except concurrent.futures.TimeoutError:
        mainframe._id_after["aio_exception_handler"] = mainframe.after(poll_interval, lambda: aio_exception_handler(mainframe, future, first_call=False))

    # Handle an expected error.
    except IOError as exc:
        _log = getLogger(__name__, DEBUG)
        _log.warning(f'aio_exception_handler: {exc!r} was handled correctly. ')
        pass

    else:
        #safeprint(f'aio_exception_handler ending. {block=}s')
        pass

default_dialog_label_text = None
default_dialog_label_color = None

def tk_callback_consumer(tk_q: queue.Queue, mainframe: ttk.Frame, row_itr: Iterator):
    """ Display queued messages in the Tkinter window.

    This is the consumer for Tkinter's work queue. It runs in the Main Thread. After starting, it runs
    continuously until the GUI is closed by the user.
    """

    global root, label_dialog, var_label_dialog, default_dialog_label_text, default_dialog_label_color

    _log = getLogger(__name__, DEBUG)
    # Poll continuously while queue has work needing processing.
    poll_interval = 0
    _stop = False
    work_package = None
    try:
        # Tkinter can't wait for the thread blocking `get` method…
        work_package = tk_q.get_nowait()
    except queue.Empty:
        # …so be prepared for an empty queue and slow the polling rate.
        poll_interval = 40
    else:
        # Process a work package.
        if work_package:
            global udi_to_scan

            if "scan" in work_package:
                # validate UDI
                #print("SCAN:", work_package["scan"])  # DEBUG
                _valid_udi = False
                for item in udi_to_scan:
                    if item.decode is not None:
                        item.records, _ = item.decode(work_package["scan"])
                    if item.validate is not None:
                        # execute the validation function which should return either the UDI or serial number
                        _s = item.validate(item.records, item.name)
                        if _s:
                            item.var.set(_s)   # set the UDI or serial number
                            _valid_udi = True  # avoid pop-up
                if not _valid_udi:
                    # here we can add an error pop-up !
                    #showerror("Wrong UDI code type!", f"{item.records}")
                    label_dialog.config(background="orange", foreground=default_dialog_label_color[1])
                    var_label_dialog.set(f" Wrong UDI code type! \n {item.records} \n {default_dialog_label_text}")
                    _log.warning(f"Wrong UDI code type {item.records}")
                else:
                    # UDI was valid
                    # clean up the color
                    label_dialog.config(background=default_dialog_label_color[0], foreground=default_dialog_label_color[1])
                    var_label_dialog.set(default_dialog_label_text)
                    root.update()
                    # check if we are complete:
                    _stop = all([(item.var.get() not in [None, ""]) for item in udi_to_scan])
            elif "error" in work_package:
                if work_package["error"] == "could not connect":
                    # to change the whole background we need to change the style:
                    #s = ttk.Style()
                    #s.configure('TFrame', background="red")
                    label_dialog.config(background=default_dialog_label_color[0], foreground="red")
                    var_label_dialog.set(" PLEASE CONNECT SCANNER! ")
                    root.update()
                elif work_package["error"] == "not responding":
                    label_dialog.config(background=default_dialog_label_color[0], foreground="orange")
                    var_label_dialog.set(" SCANNER NOT RESPONDING! ")
                    root.update()
                else:
                    showerror("Scanner error!", f"{work_package['error']}")
                    _log.warning(f"Scanner error {work_package['error']}")
            elif "info" in work_package:
                if work_package["info"] == "scanner connected":
                    # clean up the color
                    label_dialog.config(background=default_dialog_label_color[0], foreground=default_dialog_label_color[1])
                    var_label_dialog.set(default_dialog_label_text)
                    root.update()
            else:
                # may not happen !
                pass
    finally:
        if _stop:
            #mainframe.master.withdraw()
            #mainframe.master.destroy()
            global ok_button, block_accept_udi
            block_accept_udi = False
            ok_button.invoke()
            # do NOT reschedule after()

        # Have tkinter call this function again after the poll interval.
        mainframe._id_after["tk_callback_consumer"] = mainframe.after(poll_interval, lambda: tk_callback_consumer(tk_q, mainframe, row_itr))


#--------------------------------------------------------------------------------------------------


def tk_setup_callbacks(mainframe: ttk.Frame, row_itr: Iterator):
    """ Set up 'Hello world' callbacks.

    This runs in the Main Thread.

    Args:
        mainframe: The mainframe of the GUI used for displaying results from the work queue.
        row_itr: A generator of line numbers for displaying items from the work queue.
    """

    global tk_q
    global default_dialog_label_text, default_dialog_label_color

    #_log = getLogger(__name__, DEBUG)
    #_log.debug('tk_callbacks starting')
    task_id_itr = itertools.count(1)

    default_dialog_label_text = var_label_dialog.get()
    default_dialog_label_color = (label_dialog.cget("background"), label_dialog.cget("foreground"))

    # run thread's Queue consumer.
    #tk_q = queue.Queue()
    #_log.debug('tk_callback_consumer starting')
    tk_callback_consumer(tk_q, mainframe, row_itr)  # start consumer task and setup follow-ups

    # # Schedule the asyncio blockers.
    # # This is a concurrent.futures.Future not an asyncio.Future because it isn't threadsafe. Also,
    # # it doesn't have a wait with timeout which we shall need.
    # task_id = next(task_id_itr)
    # # check which communication function we need:
    # # socket communication
    # future = asyncio.run_coroutine_threadsafe(aio_blocking_communication(task_id, tk_q, resource_string), aio_loop)

    # # Can't use Future.add_done_callback here. It doesn't return until the future is done and that would block
    # # tkinter's event loop.
    # aio_exception_handler(mainframe, future)


#--------------------------------------------------------------------------------------------------
block_accept_udi = True
root: tk.Tk = None
mainframe: ttk.Frame = None
label_dialog: ttk.Label = None
ok_button: ttk.Button = None
cancel_button: ttk.Button = None

var_label_dialog: tk.StringVar = None
var_ok_button: tk.StringVar = None
var_cancel_button: tk.StringVar = None
entry_lst = []

def tk_main(title: str = "ENTER UID", test_socket: int = -1):
    """ Run tkinter.

    This runs in the Main Thread.
    """

    global udi_to_scan, allow_manual_edit, ok_button #, block_accept_udi
    global root, mainframe, ok_button, cancel_button, label_dialog
    global var_label_dialog, var_ok_button, var_cancel_button
    global entry_lst

    _log = getLogger(__name__, DEBUG)
    _log.debug('tk_main starting\n')
    row_itr = itertools.count()

    # Create the Tk root and mainframe.
    root = tk.Tk()


    def _accept_udi(parent):
        global udi_to_scan, block_accept_udi
        if block_accept_udi: return
        for item in udi_to_scan:
            item.scanned_udi = item.var.get()  # transfer from each tkinter widget into the result space
        root.destroy()

    def _cancel(parent):
        global udi_to_scan
        for item in udi_to_scan:
            item.scanned_udi = None
        root.destroy()


    #---for test only---


    def validate_entry(entry, action: str, index: str, current: str, change: str, trigger: str) -> bool:
        global block_accept_udi

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
                block_accept_udi = True
            else:
                block_accept_udi = False
        if trigger == "focusout":
            if block_accept_udi:
                return False
            else:
                return True
        return True

    # def on_invalid_entry(wname, newstr, oldstr):
    #     global block_accept_udi
    #     #print(f"{wname},{newstr},{oldstr}")
    #     #entry = root.nametowidget(wname)
    #     #entry.delete(0, tk.END)
    #     block_accept_udi = True
    #     return

    #-------------------

    root.withdraw()  # hide window
    #root.attributes('-alpha', 0)  # this hides the root window until we have arranged all the wigets
    root.title(title)
    # set App icon
    # if we have an ICO file we can simply use this:
    root.iconbitmap(Path(__file__).resolve().parent / "scan-icon.ico")
    # Simply set the theme
    root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
    root.tk.call("set_theme", "light")
    # create the Widgets and keep them inside our App object

    mainframe = ttk.Frame(root, padding="15 15 15 15", takefocus=True)
    #mainframe.grid(column=0, row=0)

    # Make the app responsive
    #for index in [0]:
    #    mainframe.columnconfigure(index=index, weight=1)
    #    mainframe.rowconfigure(index=index, weight=1)

    # Create a Frame for input widgets
    mainframe.grid(
        row=0, column=0, padx=10, pady=(30, 10),
        sticky="nsew", rowspan=3
    )
    mainframe.columnconfigure(index=0, weight=1)

    # sticky − What to do if the cell is larger than widget.
    #          By default, with sticky='', widget is centered in its cell.
    #          sticky may be the string concatenation of zero or more of N, E, S, W, NE, NW, SE, and SW
    #          compass directions indicating the sides and corners of the cell to which widget sticks.


    # Label
    var_label_dialog = tk.StringVar(root, "Scan or Enter the UDI of Device under Test")
    label_dialog = ttk.Label(
        mainframe,
        textvariable=var_label_dialog,
        #text="Scan or Enter the UDI of Device under Test",
        justify="center",
        font=("-size", 12, "-weight", "bold"),
    )
    label_dialog.grid(row=next(row_itr), column=0, columnspan=2 , pady=10)

    # Entry
    entry_lst = []
    for item in udi_to_scan:
        # Create control variables
        item.var = tk.StringVar(value="")
        _row = next(row_itr)
        _col = 0
        _label = None
        if item.name:
            _label = ttk.Label(mainframe, text=item.name)
            _label.grid(row=_row, column=_col, padx=5, pady=(0, 10), sticky="ew")
            _col += 1
        entry = ttk.Entry(
            mainframe,
            state=tk.NORMAL if allow_manual_edit else tk.DISABLED,
            textvariable=item.var,
            font=("-size", 15),
        )
         # valid percent substitutions (from the Tk entry man page)
        # note: you only have to register the ones you need; this
        # example registers them all for illustrative purposes
        #
        # %d = Type of action (1=insert, 0=delete, -1 for others)
        # %i = index of char string to be inserted/deleted, or -1
        # %P = value of the entry if the edit is allowed
        # %s = value of entry prior to editing
        # %S = the text string being inserted or deleted, if any
        # %v = the type of validation that is currently set
        # %V = the type of validation that triggered the callback
        #      (key, focusin, focusout, forced)
        # %W = the tk name of the widget
        # #validate_udi_handle = root.register(validate_entry)
        # #invalidate_udi_hanlde = root.register(invalidate_entry)
        entry.configure(validate="all",
            validatecommand=(root.register(validate_entry), "%W", "%d", "%i", "%s", "%S", "%V"),
            #invalidcommand=(root.register(on_invalid_entry), '%W', '%s', '%S'),
        )
        entry.insert(0, "")
        entry.bind("<Return>", _accept_udi )
        entry.bind("<Key-Escape>", _cancel)
        entry.grid(row=_row, column=_col, padx=5, pady=(0, 10), sticky="ew")
        entry_lst.append((_label, entry))

    # Button
    var_ok_button = tk.StringVar(root, "Start Test")
    ok_button = ttk.Button(mainframe, textvariable=var_ok_button, style="Accent.TButton", command=lambda: _accept_udi(None))
    ok_button.bind("<Return>", _accept_udi)
    ok_button.bind("<Key-Escape>", _cancel)
    ok_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, padx=5, pady=10, sticky="nsew")
    ok_button.grid_forget()

    # Separator
    separator = ttk.Separator(mainframe)
    separator.grid(row=next(row_itr), column=0, columnspan=2, padx=(20, 10), pady=10, sticky="ew")

    # Button
    var_cancel_button = tk.StringVar(root, "Cancel")
    cancel_button = ttk.Button(mainframe, textvariable=var_cancel_button, command=lambda: _cancel(None))
    cancel_button.bind("<Return>", _cancel )
    cancel_button.bind("<Key-Escape>", _cancel)
    cancel_button.grid(row=next(row_itr), column=0, columnspan=2, ipady=50, padx=5, pady=10, sticky="nsew")

    # # Sizegrip
    # sizegrip = ttk.Sizegrip(self)
    # sizegrip.grid(row=100, column=100, padx=(0, 5), pady=(0, 5))


    # # Add a close button
    # button = ttk.Button(mainframe, text='Shutdown', command=root.destroy)
    # button.grid(column=0, row=next(row_itr), sticky='w')

    ## Add an information widget.
    #label = ttk.Label(mainframe, text=f'\nWelcome to hello_world*4.py.\n')
    #label.grid(column=0, row=next(row_itr), sticky='w')

    # Schedule the 'Hello World' callbacks
    mainframe._id_after = {}
    #mainframe._id_after["tk_callbacks"] = mainframe.after(0, functools.partial(tk_callbacks, mainframe, row_itr, resource_string))
    mainframe._id_after["tk_callbacks"] = mainframe.after(0, lambda: tk_setup_callbacks(mainframe, row_itr))


    # Set a minsize for the window, and place it in the middle
    #root.update()
    root.minsize(root.winfo_width(), root.winfo_height())
    # for some reasonm the winfo_width() and _heihgt() do not show correct values here
    #_w = root.winfo_width()
    #_h = root.winfo_height()
    _w = 375  # width set manually
    _h = 485  # height set manually
    if test_socket < 0:
        _x = int((root.winfo_screenwidth() / 2) - (_w / 2))
        _y = int((root.winfo_screenheight() / 2) - (_h / 2))
        #root.geometry(f"+{_x-50}+{_y-180}")
        root.geometry(f"+{_x}+{_y}")
    else:
        _x = 250 + test_socket * (_w + 100)
        _y = 100
        root.geometry(f"+{_x}+{_y}")
    #root.attributes('-alpha', 1.0)  # now make the main window visible again

    root.update()
    root.deiconify()
    #print (root.winfo_geometry())

    #root.focus_force()  # this is to activate the window again (important after programmatically closed)

    if allow_manual_edit:
        entry_lst[0][1].focus_set()   # now set the focus to the first dialog element
        #ok_button.focus_set()
    else:
        cancel_button.focus_set()

    # # The asyncio loop must start before the tkinter event loop.
    # while not aio_loop:
    #     time.sleep(0)

    root.mainloop()

    # kill the potentially active schedules for 2 after() callbacks
    for k,v in mainframe._id_after.items():
        mainframe.after_cancel(v)

    _log.debug('tk_callback_consumer ending')
    _log.debug('tk_main ending')
    for item in udi_to_scan:
        _log.debug(f"UDI({item.name})={item.scanned_udi}")


#--------------------------------------------------------------------------------------------------


def io_thread_run(aio_initiate_shutdown: threading.Event, q_to_tk: queue.Queue, scanner_resource_str: str):
    """Separat thread which starts the scanner handling."""

    scanner = None
    while not aio_initiate_shutdown.is_set():
        try:
            if not scanner:
                # create the scanner device which also could trigger an exception
                scanner = create_barcode_scanner_with_timeout(scanner_resource_str, timeout=1.5)
                q_to_tk.put_nowait({
                    "info": "scanner connected"
                })
            response = scanner.request(None, timeout=0.1, encoding="utf-8")  # blocking, sync call - timeout keeps it handy
            if response:
                # send response to TK inter
                #print("RAW:", response)
                q_to_tk.put_nowait({
                    "scan": response
                })
        except TimeoutError as ex:
            if (not scanner) and (not aio_initiate_shutdown.is_set()):
                # could not connect to scanner - inform user
                q_to_tk.put_nowait({
                    "error": "could not connect"
                    })
                #showerror("User action required", f"Scanner {scanner_resource_str} not found")
            else:
                # # scanner not responding
                # q_to_tk.put_nowait({
                #     "error": "not responding"
                #     })
                pass  # ignore Timeout
        finally:
            pass
    if scanner:
        scanner.close_connection(force=True)

#--------------------------------------------------------------------------------------------------

def main(scanner_resource_str: str, title: str = "ENTER UDI", test_socket: int = -1):
    """Set up working environments for asyncio and tkinter.

    This runs in the Main Thread.
    """

    global tk_q

    tk_q = queue.Queue()  # need to communicate from io_thread to TK main thread

    # Start the permanent asyncio loop in a new thread. This is running the scanner request() polls.
    # aio_shutdown is signalled between threads. `asyncio.Event()` is not threadsafe.
    io_initiate_shutdown = threading.Event()
    io_thread = threading.Thread(target=io_thread_run, args=(io_initiate_shutdown, tk_q, scanner_resource_str), name="Scanner Thread")
    io_thread.start()

    # create TKinter main window and run its eternal working loop
    tk_main(title, test_socket=int(test_socket))

    # Close the IO permanent loop and join the thread in which it runs.
    io_initiate_shutdown.set()
    io_thread.join()


#--------------------------------------------------------------------------------------------------

def identify_uut(test_socket: int, requested_udi: list, scanner_resource_str: str, allow_user_edit:bool = False) -> Tuple[bool, str]:
    """Show dialog to identfy UUTs depending on the given list of requested_udis.

    Args:
        test_socket (int): 0,1 or 2 - Teststand socket: selects the window position.
        requested_udi (list): one ore more text pattern to identify the UDI or a serial number.
                To scan a RRC serial number, give "Serial" as pattern. Otherwise spezify the pattern
                as it is being expected in the UDI code: "CELL" or "PCBA" for the likes of UDIs.
        scanner_resource_str (str): String to identify the resource as either TCP or COM port. E.g.
                "COM3,9600,8N1" for comport, "172.21.101.41:2000" for socket on ipaddress with port.
        allow_user_edit (bool, optional): Allows user to edit the fields. Defaults to False.

    Returns:
        Tuple[bool, str]: _description_
    """
    global udi_to_scan, allow_manual_edit

    _log = getLogger(__name__, DEBUG)
    allow_manual_edit = allow_user_edit
    #allow_manual_edit = True
    # # this is just to demonstrate the parameter passing from TestStand
    # context_id = seq_context.Id
    # executing_sequence_name = seq_context.Sequence.Name
    # executing_step_name = seq_context.Step.Name

    title = "ENTER UDI" if int(test_socket) < 0 else f"SOCKET {int(test_socket)}: ENTER UDI"

    _scanner = scanner_resource_str
    # clear the UDIs to scan from TestStand context:
    # if "SERIAL" is found in requested UDIs, the RRC serial parser is being used
    udi_to_scan = [
        (UDIScanCtrlItem(item, decode_rrc_product_serial_label, validate_rrc_product_serial) if ("SERIAL" in item.upper()) else
        UDIScanCtrlItem(item, decode_rrc_udi_label, validate_rrc_udi)) for item in requested_udi
    ]

    main(_scanner, title=title, test_socket=int(test_socket))

    res = tuple()
    for item in udi_to_scan:
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
    ## Initialize the logging
    from rrc.custom_logging import logger_init
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # # set the required UDIs per global
    # udi_to_scan = [
    #     UDIScanCtrlItem("SERIAL", decode_rrc_product_serial_label, validate_rrc_product_serial),
    #     UDIScanCtrlItem("PCBA", decode_rrc_udi_label, validate_rrc_udi),
    #     UDIScanCtrlItem("CELL", decode_rrc_udi_label, validate_rrc_udi),
    # ]

    RESOURCE_STR = "172.21.101.31:2000"
    #RESOURCE_STR = "COM3,9600,8N1"  # Handheld scanner
    #RESOURCE_STR = "SIMULATION"  # select a timed simulation

    allow_manual_edit = True

    identify_uut(0, ["Serial", "PCBA", "CELL"], RESOURCE_STR, allow_user_edit=False)

    res = tuple()
    for item in udi_to_scan:
        _log.debug(f"UDI({item.name})={item.scanned_udi}")
        res += (item.scanned_udi,)
    if all(res):
        print((True,) + res)
    else:
        print((False,) + res)


# END OF FILE