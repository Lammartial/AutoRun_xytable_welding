from pathlib import Path
import time
import tkinter as tk
import tkinter.ttk as ttk


def disable_event():
   pass

class ProgressWindow:

    def __init__(self) -> None:
        self.hidden = None
        # create root tkinter window to hold progress bar
        self.root = tk.Tk()

        #mainframe = ttk.Frame(root, padding="15 15 15 15")
        #mainframe.pack(fill="both")

        # Disable the Close Window Control Icon
        self.root.protocol("WM_DELETE_WINDOW", disable_event)

        #self.root.withdraw()  # hide window
        self.hide()

        #self.root.attributes('-alpha', 0)  # this hides the root window until we have arranged all the wigets
        self.root.title("Programming")
        # set App icon
        # if we have an ICO file we can simply use this:
        self.root.iconbitmap(Path(__file__).resolve().parent / "app-icon.ico")
        # Simply set the theme
        #self.root.tk.call("source", Path(__file__).resolve().parent / "theme_sv.tcl")
        #self.root.tk.call("set_theme", "light")

        style = ttk.Style()
        style.element_create("color.pbar", "from", "clam")
        style.layout("ColorProgress.Horizontal.TProgressbar",
                            [('Horizontal.Progressbar.trough',
                            {'sticky': 'nswe',
                            'children': [('Horizontal.Progressbar.color.pbar',
                                {'side': 'left', 'sticky': 'ns'})]})])
        style.configure("ColorProgress.Horizontal.TProgressbar", background="blue")

        # create the Widgets and keep them inside our App object
        #self.root.minsize(100, 50)
        x_size = int(self.root.winfo_screenwidth() * 0.60)
        y_size = int(self.root.winfo_screenheight() * 0.2)
        self.root.geometry(f"{x_size}x{y_size}")
        #Define the geometry for the window or frame
        #self.root.attributes('-alpha', 1.0)  # now make the main window visible again
        self.root.columnconfigure(0, weight=1)
        # create progress bar
        self.progress = ttk.Progressbar(self.root,
                    orient=tk.HORIZONTAL,mode="determinate", maximum=100, value=0,
                    length=x_size,
                    style='ColorProgress.Horizontal.TProgressbar')
        #progress.grid(row=0, column=1, padx=(10, 10), pady=(10, 10), sticky="ew")
        # pack progress bar into root
        self.progress.pack(fill=tk.BOTH, expand=1)

        # to step progress bar up
        #progress.config(mode="determinate", length=1000, maximum=100, value=0)

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


#--------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    win = ProgressWindow()
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

# END OF FILE

