from pathlib import Path
import time
import tkinter
from tkinter import ttk


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

    def __init__(self, title: str = "Programming Flash", color: str = None,
                 fontsize: int = 18, width: int = 800, height: int = 100,
                 test_socket: int = -1) -> None:

        def disable_event():
            pass

        ROOT = tkinter.Tk()
        ROOT.withdraw()  # hide window
        style = ttk.Style()
        #print(style.theme_names())
        style.theme_use("winnative")
        
        # Disable the Close Window Control Icon
        ROOT.protocol("WM_DELETE_WINDOW", disable_event)
        # set App icon
        ROOT.iconbitmap(Path(__file__).resolve().parent / "chip-icon.ico")
        
        self.root = ROOT
        self.hidden = None
        if color and color == "":
            color = None  # TestStand cannot transfer "None"
        if color:
            #global style
            style.configure("ColorProgress.Horizontal.TProgressbar", background=color)
        test_socket = int(test_socket)     
        # define the geometry for the window or frame
        #x_size = int(self.root.winfo_screenwidth() * 0.60)
        #y_size = int(self.root.winfo_screenheight() * 0.1)
        #x = int((self.root.winfo_screenwidth() - x_size) / 2)
        #y = int((self.root.winfo_screenheight() - y_size) / 2)
        #self.root.geometry(f"{x_size}x{y_size}+{x}+{y}")
        x_size = int(width)
        y_size = int(height)
        if test_socket < 0:
            self.root.title(title)
            _x = int((self.root.winfo_screenwidth() / 2) - (x_size / 2))
            _y = int((self.root.winfo_screenheight() / 2) - (y_size / 2))
        else:
            self.root.title(f"SOCKET {test_socket}: {title}")
            _x = int((self.root.winfo_screenwidth() / 2) - (x_size / 2))
            _y = 500 + test_socket * (y_size + 50)
        self.root.geometry(f"{x_size}x{y_size}+{_x}+{_y}")        
        self.root.columnconfigure(0, weight=1)
        # create progress bar
        self.progress = ttk.Progressbar(self.root,
                    orient=tkinter.HORIZONTAL, mode="determinate", maximum=100, value=0,
                    style=("ColorProgress.Horizontal.TProgressbar" if color else None))
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

    def close(self):
        self.root.destroy()
        
#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    _title = "PROGRAM"
    colors = [None, "darkblue", "red"]
    for z in range(3):
        win = ProgressWindow(title=_title + f" {z}", color=colors[z], test_socket=0)
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

        #win.hide()
        #win.quit()
        win.close()

# END OF FILE

