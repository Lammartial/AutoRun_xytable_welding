""" tkinter_demo.py

Created with Python 3.10
"""

import asyncio
import concurrent.futures
import functools
import itertools
import queue
import sys
import threading
import time
import tkinter as tk
import tkinter.ttk as ttk
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Optional, Type, Tuple
from pathlib import Path

from rrc.eth2serial.base_async import tcp_send_and_receive_from_server

DEBUG = 0   # set to 0 for production

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
import logging

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")

# --------------------------------------------------------------------------- #

# Global reference to loop allows access from different environments.
aio_loop: Optional[asyncio.AbstractEventLoop] = None
tk_q: queue.Queue = None
UDI: str = None
ok_button = None
var_udi = None

async def aio_blocker(task_id: int, tk_q: queue.Queue, resource_string: str) -> None:
    """ Asynchronously block the thread and put a 'Hello World' work package into Tkinter's work queue.

    This is a producer for Tkinter's work queue. It will run in the same thread as the asyncio loop. The statement
    `await asyncio.sleep(block)` can be replaced with any awaitable blocking code.

    Args:
        task_id: Sequentially issued tkinter task number.
        tk_q: tkinter's work queue.
        block: block time

    Returns:
        Nothing. The work package is returned via the threadsafe tk_q.
    """
    #safeprint(f'aio_blocker starting. {resource_string}s.')
    #await asyncio.sleep(block)
    while True:
        _response = await tcp_send_and_receive_from_server(resource_string, None, timeout=3.0, limit = 30)
        if _response:
            _wp = f"RESPONSE={_response}"
            #safeprint(_wp)
            _log.info(_wp)
            work_package = _wp
        else:
            #safeprint(f"NO RESPONSE!")
            #work_package = f"Task #{task_id}: NO RESPONSE!"
            continue

        # Exceptions for testing handlers. Uncomment these to see what happens when exceptions are raised.
        # raise IOError('Just testing an expected error.')
        # raise ValueError('Just testing an unexpected error.')

        #work_package = f"Task #{task_id} {block}s: 'Hello Asynchronous World'."

        # Put the work package into the tkinter's work queue.
        while True:
            try:
                # Asyncio can't wait for the thread blocking `put` method…
                tk_q.put_nowait(work_package)

            except queue.Full:
                # Give control back to asyncio's loop.
                await asyncio.sleep(0)
            else:
                # The work package has been placed in the queue so we're done.
                break
        break

    # ends by force only
    #safeprint(f'aio_blocker ending.')


def aio_exception_handler(mainframe: ttk.Frame, future: concurrent.futures.Future, block: float,
                          first_call: bool = True) -> None:
    """ Exception handler for future coroutine callbacks.

    This non-coroutine function uses tkinter's event loop to wait for the future to finish.
    It runs in the Main Thread.

    Args:
        mainframe: The after method of this object is used to poll this function.
        future: The future running the future coroutine callback.
        block: The block time parameter used to identify which future coroutine callback is being reported.
        first_call: If True will cause an opening line to be printed on stdout.
    """
    #if first_call:
    #    safeprint(f'aio_exception_handler starting. {block=}s')
    poll_interval = 100  # milliseconds
    try:
        # Python will not raise exceptions during future execution until `future.result` is called. A zero timeout is
        # required to avoid blocking the thread.
        future.result(0)

    # If the future hasn't completed, reschedule this function on tkinter's event loop.
    except concurrent.futures.TimeoutError:
        #mainframe._id_after["aio_exception_handler"] = mainframe.after(poll_interval, functools.partial(aio_exception_handler, mainframe, future, block,
        #                                                 first_call=False))
        mainframe._id_after["aio_exception_handler"] = mainframe.after(poll_interval, lambda: aio_exception_handler(mainframe, future, block, first_call=False))

    # Handle an expected error.
    except IOError as exc:
        #safeprint(f'aio_exception_handler: {exc!r} was handled correctly. ')
        _log.warning(f'aio_exception_handler: {exc!r} was handled correctly. ')
        pass

    else:
        #safeprint(f'aio_exception_handler ending. {block=}s')
        pass

def tk_callback_consumer(tk_q: queue.Queue, mainframe: ttk.Frame, row_itr: Iterator):
    """ Display queued 'Hello world' messages in the Tkinter window.

    This is the consumer for Tkinter's work queue. It runs in the Main Thread. After starting, it runs
    continuously until the GUI is closed by the user.
    """
    # Poll continuously while queue has work needing processing.
    poll_interval = 0
    _stop = False
    try:
        # Tkinter can't wait for the thread blocking `get` method…
        work_package = tk_q.get_nowait()

    except queue.Empty:
        # …so be prepared for an empty queue and slow the polling rate.
        poll_interval = 40

    else:
        # Process a work package.
        #label = ttk.Label(mainframe, text=work_package)
        #label.grid(column=0, row=(next(row_itr)), sticky='w', padx=10)
        if "RESPONSE" in work_package:
            global var_udi
            _udi = work_package.split("=")[1]
            var_udi.set(_udi)
            _stop = True
    finally:
        if _stop:
            #mainframe.master.withdraw()
            #mainframe.master.destroy()
            global ok_button
            ok_button.invoke()
            # do NOT reschedule after()
        #else:
        # Have tkinter call this function again after the poll interval.
        #mainframe._id_after["tk_callback_consumer"] = mainframe.after(poll_interval, functools.partial(tk_callback_consumer, tk_q, mainframe, row_itr))
        mainframe._id_after["tk_callback_consumer"] = mainframe.after(poll_interval, lambda: tk_callback_consumer(tk_q, mainframe, row_itr))


def tk_callbacks(mainframe: ttk.Frame, row_itr: Iterator, resource_string: str):
    """ Set up 'Hello world' callbacks.

    This runs in the Main Thread.

    Args:
        mainframe: The mainframe of the GUI used for displaying results from the work queue.
        row_itr: A generator of line numbers for displaying items from the work queue.
    """

    global tk_q

    #safeprint('tk_callbacks starting')
    _log.debug('tk_callbacks starting')
    task_id_itr = itertools.count(1)

    # Create the job queue and start its consumer.
    tk_q = queue.Queue()
    #safeprint('tk_callback_consumer starting')
    _log.debug('tk_callback_consumer starting')
    tk_callback_consumer(tk_q, mainframe, row_itr)

    # Schedule the asyncio blocker.
    for block in range(0, 1):
        # This is a concurrent.futures.Future not an asyncio.Future because it isn't threadsafe. Also,
        # it doesn't have a wait with timeout which we shall need.
        task_id = next(task_id_itr)
        future = asyncio.run_coroutine_threadsafe(aio_blocker(task_id, tk_q, resource_string), aio_loop)

        # Can't use Future.add_done_callback here. It doesn't return until the future is done and that would block
        # tkinter's event loop.
        aio_exception_handler(mainframe, future, block)

    #safeprint('tk_callbacks ending - All blocking callbacks have been scheduled.\n')


#--------------------------------------------------------------------------------------------------

def tk_main(resource_string: str, title: str = "ENTER UID"):
    """ Run tkinter.

    This runs in the Main Thread.
    """
    global UDI, var_udi, ok_button

    #safeprint('tk_main starting\n')
    _log.debug('tk_main starting\n')
    row_itr = itertools.count()

    # Create the Tk root and mainframe.
    root = tk.Tk()

     # Create control variables
    var_udi = tk.StringVar(value="")

    def _accept_udi(parent):
        global UDI, var_udi
        UDI = var_udi.get()
        root.destroy()

    def _cancel(parent):
        global UDI
        UDI = None
        root.destroy()

    root.withdraw()  # hide window
    #root.attributes('-alpha', 0)  # this hides the root window until we have arranged all the wigets
    root.title(title)
    # set App icon
    # if we have an ICO file we can simply use this:
    root.iconbitmap(Path(__file__).resolve().parent / "app-icon.ico")
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

    # Label
    label = ttk.Label(
        mainframe,
        text="Scan or Enter the UID of Device under Test",
        justify="center",
        font=("-size", 12, "-weight", "bold"),
    )
    label.grid(row=next(row_itr), column=0, pady=10, columnspan=2)

    # Entry
    entry = ttk.Entry(
        mainframe,
        textvariable=var_udi,
        font=("-size", 15),
    )
    entry.insert(0, "")
    entry.bind("<Return>", _accept_udi )
    entry.bind("<Key-Escape>", _cancel)
    entry.grid(row=next(row_itr), column=0, padx=5, pady=(0, 10), sticky="ew")


    # Button
    ok_button = ttk.Button(mainframe, text="Start Test", style="Accent.TButton", command=lambda: _accept_udi(None))
    ok_button.bind("<Return>", _accept_udi)
    ok_button.bind("<Key-Escape>", _cancel)
    ok_button.grid(row=next(row_itr), column=0, padx=5, pady=10, sticky="nsew")

    # Separator
    separator = ttk.Separator(mainframe)
    separator.grid(row=next(row_itr), column=0, padx=(20, 10), pady=10, sticky="ew")

    # Button
    cancel_button = ttk.Button(mainframe, text="Cancel", command=lambda: _cancel(None))
    cancel_button.bind("<Return>", _cancel )
    cancel_button.bind("<Key-Escape>", _cancel)
    cancel_button.grid(row=next(row_itr), column=0, padx=5, pady=10, sticky="nsew")

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
    mainframe._id_after["tk_callbacks"] = mainframe.after(0, lambda: tk_callbacks(mainframe, row_itr, resource_string))


    # Set a minsize for the window, and place it in the middle
    #root.update()
    root.minsize(root.winfo_width(), root.winfo_height())
    x_cordinate = int((root.winfo_screenwidth() / 2) - (root.winfo_width() / 2))
    y_cordinate = int((root.winfo_screenheight() / 2) - (root.winfo_height() / 2))
    root.geometry("+{}+{}".format(x_cordinate, y_cordinate-20))
    #root.attributes('-alpha', 1.0)  # now make the main window visible again

    root.update()
    root.deiconify()

    root.focus_force()  # this is to activate the window again (important after programmatically closed)
    entry.focus_set()   # now set the focus to the dialog element

    # The asyncio loop must start before the tkinter event loop.
    while not aio_loop:
        time.sleep(0)

    root.mainloop()


    # kill the potentially active schedules for 2 after() callbacks
    for k,v in mainframe._id_after.items():
        mainframe.after_cancel(v)

    #safeprint(' ', timestamp=False)
    #safeprint('tk_callback_consumer ending')
    #safeprint('tk_main ending')
    _log.debug('tk_callback_consumer ending')
    _log.debug('tk_main ending')
    _log.debug(f"UDI={UDI}")


async def manage_aio_loop(aio_initiate_shutdown: threading.Event):
    """ Run the asyncio loop.

    This provides an always available asyncio service for tkinter to make any number of simultaneous blocking IO
    calls. 'Any number' includes zero.

    This runs in Asyncio's thread and in asyncio's loop.
    """
    #safeprint('manage_aio_loop starting')

    # Communicate the asyncio loop status to tkinter via a global variable.
    global aio_loop
    aio_loop = asyncio.get_running_loop()

    # If there are no awaitables left in the queue asyncio will close.
    # The usual wait command — Event.wait() — would block the current thread and the asyncio loop.
    while not aio_initiate_shutdown.is_set():
        await asyncio.sleep(0)

    #safeprint('manage_aio_loop ending')


def aio_main(aio_initiate_shutdown: threading.Event):
    """ Start the asyncio loop.

    This non-coroutine function runs in Asyncio's thread.
    """
    #safeprint('aio_main starting')
    asyncio.run(manage_aio_loop(aio_initiate_shutdown))
    #safeprint('aio_main ending')


def main(resource_str: str, title: str = "ENTER UDI"):
    """Set up working environments for asyncio and tkinter.

    This runs in the Main Thread.
    """
    #safeprint('main starting')

    # Start the permanent asyncio loop in a new thread.
    # aio_shutdown is signalled between threads. `asyncio.Event()` is not threadsafe.
    aio_initiate_shutdown = threading.Event()
    aio_thread = threading.Thread(target=aio_main, args=(aio_initiate_shutdown,), name="Asyncio's Thread")
    aio_thread.start()

    tk_main(resource_str, title)

    # Close the asyncio permanent loop and join the thread in which it runs.
    aio_initiate_shutdown.set()
    aio_thread.join()

    #safeprint('main ending')


@dataclass
class SafePrinter(AbstractContextManager):
    _time_0 = time.perf_counter()
    _print_q = queue.Queue()
    _print_thread: threading.Thread | None = None

    def __enter__(self):
        """ Run the safeprint consumer method in a print thread.

        Returns:
            Thw safeprint producer method. (a.k.a. the runtime context)
        """
        self._print_thread = threading.Thread(target=self._safeprint_consumer, name='Print Thread')
        self._print_thread.start()
        return self._safeprint

    def __exit__(self, __exc_type: Type[BaseException] | None, __exc_value: BaseException | None,
                 __traceback: TracebackType | None) -> bool | None:
        """ Close the print and join the print thread.

        Args:
            None or the exception raised during the execution of the safeprint producer method.
            __exc_type:
            __exc_value:
            __traceback:

        Returns:
            False to indicate that any exception raised in self._safeprint has not been handled.
        """
        self._print_q.put(None)
        self._print_thread.join()
        return False

    def _safeprint(self, msg: str, *, timestamp: bool = True, reset: bool = False):
        """Put a string into the print queue.

        'None' is a special msg. It is not printed but will close the queue and this context manager.

        The exclusive thread and a threadsafe print queue ensure race free printing.
        This is the producer in the print queue's producer/consumer pattern.
        It runs in the same thread as the calling function

        Args:
            msg: The message to be printed.
            timestamp: Print a timestamp (Default = True).
            reset: Reset the time to zero (Default = False).
        """
        if reset:
            self._time_0 = time.perf_counter()
        if timestamp:
            self._print_q.put(f'{self._timestamp()} --- {msg}')
        else:
            self._print_q.put(msg)

    def _safeprint_consumer(self):
        """Get strings from the print queue and print them on stdout.

        The print statement is not threadsafe, so it must run in its own thread.
        This is the consumer in the print queue's producer/consumer pattern.
        """
        print(f'{self._timestamp()}: The SafePrinter is open for output.')
        while True:
            msg = self._print_q.get()

            # Exit function when any producer function places 'None'.
            if msg is not None:
                print(msg)
            else:
                break
        print(f'{self._timestamp()}: The SafePrinter has closed.')

    def _timestamp(self) -> str:
        """Create a timestamp with useful status information.

        This is a support function for the print queue producers. It runs in the same thread as the calling function
        so the returned data does not cross between threads.

        Returns:
            timestamp
        """
        secs = time.perf_counter() - self._time_0
        try:
            asyncio.get_running_loop()
        except RuntimeError as exc:
            if exc.args[0] == 'no running event loop':
                loop_text = 'without a loop'
            else:
                raise
        else:
            loop_text = 'with a loop'
        return f'{secs:.3f}s In {threading.current_thread().name} of {threading.active_count()} {loop_text}'


#--------------------------------------------------------------------------------------------------
def identify_uut(context) -> Tuple[bool, str]:
    """Entry function for TestStand.

    Args:
        context (dict): TestStand context

    Returns:
        Tuple[bool, str]: return values to a TestStand container that expects two types in this order.
    """
    global UDI

    #sys.exit(main())
    main(context["scanner"])
    if UDI is not None:
        return (True, UDI)
    else:
        return (False, "")

#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    #with SafePrinter() as safeprint:
    #     #sys.exit(main())
    #     for i in range(0, 2):
    #         main("169.254.36.1:2000")
    for i in range(0,10):
        z = identify_uut({"scanner":"169.254.36.1:2000"})
        print(f"IDX:{i} -> {z}")
# END OF FILE