from pathlib import Path
import time
import tkinter
from tkinter import ttk

ROOT = tkinter.Tk()
ROOT.withdraw()  # hide window
style = ttk.Style()
#print(style.theme_names())
style.theme_use("winnative")

def disable_event():
   pass

# Disable the Close Window Control Icon
ROOT.protocol("WM_DELETE_WINDOW", disable_event)
# set App icon
ROOT.iconbitmap(Path(__file__).resolve().parent / "chip-icon.ico")



def center(win: tkinter.Tk):
    """
    centers a tkinter window
    :param win: the main window or Toplevel window to center
    """
    width = win.winfo_width()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = width + 2 * frm_width
    height = win.winfo_height()
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = height + titlebar_height + frm_width
    x = win.winfo_screenwidth() // 2 - win_width // 2
    y = win.winfo_screenheight() // 2 - win_height // 2
    win.geometry(f"{width}x{height}+{x}+{y}")


class ProgressWindow:

    def __init__(self, title: str = "Programming Flash", color: str = None) -> None:
        global ROOT

        self.root = ROOT
        self.hidden = None
        if color and color == "":
            color = None  # TestStand cannot transfer "None"
        if color:
            global style
            style.configure("ColorProgress.Horizontal.TProgressbar", background=color)
        self.root.title(title)
        # create the Widgets and keep them inside our App object
        x_size = int(self.root.winfo_screenwidth() * 0.60)
        y_size = int(self.root.winfo_screenheight() * 0.1)
        x = int((self.root.winfo_screenwidth() - x_size) / 2)
        y = int((self.root.winfo_screenheight() - y_size) / 2)
        self.root.geometry(f"{x_size}x{y_size}+{x}+{y}")
        # define the geometry for the window or frame
        self.root.columnconfigure(0, weight=1)
        # create progress bar
        self.progress = ttk.Progressbar(self.root,
                    orient=tkinter.HORIZONTAL, mode="determinate", maximum=100, value=0,
                    style="ColorProgress.Horizontal.TProgressbar" if color else None)
        # pack progress bar into root
        self.progress.pack(fill=tkinter.BOTH, expand=1)
        # leave window hidden


    def hide(self):
        self.root.withdraw()  # hide window
        self.hidden = True

    def show(self):
        self.root.update()
        self.root.deiconify()
        self.hidden = False

    def set_value(self, value: float):
        self.progress.config(value=value)
        self.root.update()

    def update(self):
        self.root.update()

    def quit(self):
        self.root.quit()
        for widget in self.root.winfo_children():
            widget.destroy()


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    _title = "PROGRAM"
    colors = [None, "darkblue", "red"]
    for z in range(2):
        win = ProgressWindow(title=_title + f" {z}", color=colors[z])
        i = 0
        mx = 10
        win.show()
        LOOP_ACTIVE = True
        while LOOP_ACTIVE:
            print(i)
            win.set_value(10*i)
            time.sleep(0.4)
            i = i + 1
            if (i > mx):
                win.quit()
                LOOP_ACTIVE = False
            else:
                pass

        win.hide()
        win.quit()

# END OF FILE

