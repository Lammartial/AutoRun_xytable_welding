from typing import List, Tuple
from enum import Enum
import tkinter as tk
import tkinter.ttk as ttk
from time import sleep, perf_counter
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from rrc.ui.popup import BatteryPopup

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
DEBUG = 1   # set to 0 for production
from rrc.custom_logging import getLogger, logger_init

#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # need to initialize logger on load

    print("=== Splash Screen ===")

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--closeafter", action="store", default=3.0, type=float, help="Close after x s.")

    args = parser.parse_args()


    splash = BatteryPopup("Teststand is starting up", title="Keep cool ...")

    splash.root.after(int(args.closeafter * 1e+3), lambda: splash.close())
    splash.root.mainloop()

    print("DONE.")

# END OF FILE