"""
As long as the DEBUG Python by click from TestStand does not work we need this module as workaround.
It provides the process ID of the called python kernel.
"""

import os
import ctypes

def show_pid_for_debug():
    """This function shows the current TestStand's process ID to allow connection by VSCode for debugging."""
    ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)

# END OF FILE