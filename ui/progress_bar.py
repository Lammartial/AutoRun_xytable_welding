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

        # # create root tkinter window to hold progress bar
        # self.root = tkinter.Tk()
        # self.hide()

        # # Simply set the theme
        # #self.root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
        # #self.root.tk.call("set_theme", "light")

        # style = ttk.Style()
        # #print(style.theme_names())
        # style.theme_use('winnative')

        # #style = ttk.Style()
        # #print(style.theme_names())
        # #style.theme_use('winnative')
        # #try:
        # #    style.element_create("color.pbar", "from", "winnative")
        # #except Exception as ex:
        # #    print(ex)
        # #    pass
        # #style.layout("ColorProgress.Horizontal.TProgressbar",
        # #                    [('Horizontal.Progressbar.trough',
        # #                    {'sticky': 'nswe',
        # #                    'children': [('Horizontal.Progressbar.color.pbar', {'side': 'left', 'sticky': 'ns'})]})])

        if color and color == "":
            color = None  # TestStand cannot transfer "None"
        if color:
            global style
            style.configure("ColorProgress.Horizontal.TProgressbar", background=color)


        #mainframe = ttk.Frame(root, padding="15 15 15 15")
        #mainframe.pack(fill="both")

        #self.root.attributes('-alpha', 0)  # this hides the root window until we have arranged all the wigets
        self.root.title(title)

        # create the Widgets and keep them inside our App object
        # #self.root.minsize(100, 50)
        x_size = int(self.root.winfo_screenwidth() * 0.60)
        y_size = int(self.root.winfo_screenheight() * 0.1)
        x = int((self.root.winfo_screenwidth() - x_size) / 2)
        y = int((self.root.winfo_screenheight() - y_size) / 2)
        self.root.geometry(f"{x_size}x{y_size}+{x}+{y}")
        #center(self.root)
        #Define the geometry for the window or frame
        #self.root.attributes('-alpha', 1.0)  # now make the main window visible again
        self.root.columnconfigure(0, weight=1)
        # create progress bar
        self.progress = ttk.Progressbar(self.root,
                    orient=tkinter.HORIZONTAL, mode="determinate", maximum=100, value=0,
                    style="ColorProgress.Horizontal.TProgressbar" if color else None)
        # pack progress bar into root
        self.progress.pack(fill=tkinter.BOTH, expand=1)
        print("STYLE:", self.progress["style"])
        #
        # leave window hidden
        #

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
            #progress.step(10)
            #progress.value = 100
            win.set_value(10*i)
            #win.update()
            time.sleep(0.4)
            i = i + 1
            if (i > mx):
                win.quit()
                LOOP_ACTIVE = False
            else:
                #value_progress = i
                pass

        win.hide()
        win.quit()

# END OF FILE

