"""
Login dialog for use with Teststand.

Need Python 3.10

"""

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
from tkinter.messagebox import showinfo
from collections.abc import Iterator
from typing import Optional, Tuple
from pathlib import Path
from serial import Serial
from rrc.eth2serial import Eth2SerialDevice, tcp_send_and_receive_from_server
from rrc.serialport import SerialComportDevice

# # import SQL managing modules
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from rrc.dbcon import get_mockup_useracess_db_connector

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger

# --------------------------------------------------------------------------- #

# global engine and session generator to share access in the callbacks later
srcEngine, makeSessions = get_mockup_useracess_db_connector()

#--------------------------------------------------------------------------------------------------

def validate_user_id(card_id: str) -> Tuple[bool, dict]:
    global makeSessions

    print(f"CHECK ID {card_id}")
    with makeSessions() as session:
        res = session.execute(sa.text(f"SELECT username,pwd,access FROM `teststand_users` AS mu WHERE card_id='{card_id}'"))
        rows = res.fetchall()
        if len(rows) == 0:
            # not found! -> do not login
            showinfo("WARNING", f"User login not found in database.")
            return False, {}
        user = {
            "username": rows[0][0],
            "pwd": rows[0][1],
            "access": rows[0][2],
        }
        if user["access"] == 0:
            # has no access!
            showinfo("WARNING", f'User {user["username"]} is not allowed to login.')
            return False, user
    return True, user

#--------------------------------------------------------------------------------------------------

class WindowUI(object):

    def __init__(self, title: str = "USER LOGIN", allow_manual_edit: bool = False):
        global DEBUG

        self._log = getLogger(__name__, DEBUG)

        self.USER = None
        self.allow_manual_edit = allow_manual_edit
        row_itr = itertools.count()

        # Create the Tk root and mainframe.
        self.root = tk.Tk()

        self.var_login = tk.StringVar(value="")

        self.root.withdraw()  # hide window
        self.root.title(title)
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "user-icon.ico")
        # Simply set the theme
        self.root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
        self.root.tk.call("set_theme", "light")
        style = ttk.Style()

        # for some reasonm the winfo_width() and _heihgt() do not show correct values here
        #_w = root.winfo_width()
        #_h = root.winfo_height()
        _padall = 8
        #_w = 300  # width set manually
        #_h = self.root.winfo_screenheight() #480  # height set manually
        _w = int(self.root.winfo_screenwidth() * 0.50)
        _h = int(self.root.winfo_screenheight() * 0.50)
        # Set a minsize for the window
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        self.root.minsize(int(_w/2), int(_h/2))
        _x = int((self.root.winfo_screenwidth() - _w) / 2)
        #_x = int(self.root.winfo_screenwidth() - _w - _padall)
        _y = int((self.root.winfo_screenheight() - _h) / 2)
        self.root.geometry(f"{_w}x{_h}+{_x}+{_y}")

        #
        # setup widgets
        #
        self.mainframe = ttk.Frame(self.root, pad=(_padall,_padall,_padall,_padall), takefocus=True)

        #self.mainframe.pack(fill=tk.BOTH)
        # configure the column width equally to center everything nicely

        self.mainframe.grid(row=0, column=0, sticky="NESW")
        #self.mainframe.grid_rowconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(1, weight=1)
        self.mainframe.grid_rowconfigure(0, weight=2)  # headline
        self.mainframe.grid_rowconfigure(1, weight=5)
        self.mainframe.grid_rowconfigure(2, weight=3)
        self.mainframe.grid_rowconfigure(3, weight=10)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Label
        _colspan = 2
        label = ttk.Label(self.mainframe, text="Scan your TAG",
                          justify="center", font=("-size", 12, "-weight", "bold"),
        )
        label.grid(row=next(row_itr), column=0, columnspan=_colspan)

        # Entry
        entry = ttk.Entry(self.mainframe,
            #state=tk.NORMAL if allow_manual_edit else tk.DISABLED,
            textvariable=self.var_login,
            #validate='focusout',
            #validatecommand=(validate_udi_handle, '%W', '%s', '%S'),
            #invalidcommand=(invalidate_udi_hanlde, '%W', '%s', '%S'),
            show="*",  # user cannot read
            #foreground="white", # user cannot read
            font=("-size", 15),
        )
        entry.insert(0, "")
        entry.bind("<Return>", lambda x: self._accept_udi(None) )
        entry.bind("<Key-Escape>", lambda x: self._cancel(None) )
        entry.grid(row=next(row_itr), column=0, columnspan=_colspan, ipady=10) # sticky="ns")


        # Buttons
        style.configure('B1.TButton', foreground="blue", background='#232323')
        style.map('B1.TButton', background=[("active","#ff0000")])
        style.configure('B2.TButton', foreground="red", background='#232323')
        style.map('B2.TButton', background=[("active","#ff0000")])

        # # Ok-Button
        # ok_button = ttk.Button(self.mainframe, text="Login", style="B1.TButton", command=lambda x: _accept_udi(None))
        # ok_button.bind("<Return>", _accept_udi)
        # ok_button.bind("<Key-Escape>", _cancel)
        # ok_button.grid(row=next(row_itr), column=0, columnspan=2, ipadx=100, ipady=50)

        # Separator
        separator = ttk.Separator(self.mainframe)
        separator.grid(row=next(row_itr), column=0, columnspan=2, sticky="ew")

        # Cancel-Button
        cancel_button = ttk.Button(self.mainframe, text="CANCEL", style="B2.TButton", command=lambda: self._cancel(None))
        cancel_button.bind("<Return>", lambda x: self._cancel(None) )
        cancel_button.bind("<Key-Escape>", lambda x: self._cancel(None))
        cancel_button.grid(row=next(row_itr), column=0, columnspan=2, sticky="nesw")


        # schedule queue processing callback
        #self._id_after = self.mainframe.after(0, lambda: self.process_command_queue())

        self.root.update()
        self.root.deiconify()
        self.root.focus_force()  # this is to activate the window again (important after programmatically closed)
        entry.focus_set()

    def _accept_udi(self, parent):
        ok, _user = validate_user_id(self.var_login.get())
        if ok:
            self.USER = _user
            self.root.destroy()
        else:
            self.var_login.set("")  # clear

    def _cancel(self, parent):
        self.USER = None
        self.root.destroy()

    def run_mainloop(self):
        self.root.mainloop()


#--------------------------------------------------------------------------------------------------
def identify_user(allow_manual_edit:bool = False) -> Tuple[bool, str, str]:
    """Login user to TestStand using context IDispatch interface (block of data)

    Args:
        context (dict): TestStand context

    Returns:
        Tuple[bool, str]: return values to a TestStand container that expects two types in this order.
    """

    _log = getLogger(__name__, DEBUG)

    _user = { "username": "", "pwd": "" }
    _login = False
    p = None
    w = None
    s = None
    try:
        w = WindowUI(title="TestStand - Login", allow_manual_edit=allow_manual_edit)
        w.run_mainloop()
        # in w.USER are the user information; if None, nobody is logged in
        if w.USER:
            _user = w.USER
            _login = True
    except KeyboardInterrupt as kx:
        # user stopped process
        pass
    finally:
        pass

    return _login, _user["username"], _user["pwd"]

#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    ## Initialize the logging
    from rrc.custom_logging import logger_init
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    with makeSessions() as session:
        res = session.execute(sa.text("SELECT * FROM `teststand_users` AS mu"))
        print(res.fetchall())

    res = identify_user(allow_manual_edit=True)
    print(res)


# END OF FILE
