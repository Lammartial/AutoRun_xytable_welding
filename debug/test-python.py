from typing import Tuple
import pyvisa as visa
import time

def hallo_welt(wieviel: int, uhr: int) -> int:
    r = wieviel * uhr
    return r

def hallo_welt2(wieviel: int, uhr: int) -> Tuple[int]:
    r = wieviel * uhr
    return (r,)


def daq970A_display_on_off(state: bool):
    return state

def daq970A_display_on():
    #ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    return True

# END OF FILE