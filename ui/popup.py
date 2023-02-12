from pathlib import Path
from tkinter import Tk, StringVar
from tkinter import ttk


class BatteryPopup:

    def __init__(self, message: str, title: str = "Check for Battery presence", textcolor: str = "darkblue", 
                 fontsize: int = 18, width: int = 375, height: int = 275, 
                 show: bool = True, test_socket: int = -1) -> None:
        ROOT = Tk()
        ROOT.withdraw()  # hide window
        self.hidden = True
        style = ttk.Style()
        #print(style.theme_names())
        style.theme_use("winnative")

        def disable_event():
            pass

        # Disable the Close Window Control Icon
        ROOT.protocol("WM_DELETE_WINDOW", disable_event)
        # set App icon
        ROOT.iconbitmap(Path(__file__).resolve().parent / "battery-icon.ico")
        
        self.root = ROOT
        
        #self.popup = tkinter.Toplevel(self.root)
        #self.popup.wm_title("!")
        #self.popup.tkraise(self.root)  
        self.root.title(title)
        # create the Widgets and keep them inside our App object
        x_size = int(width)
        y_size = int(height)
        if int(test_socket) < 0:
            _x = int((self.root.winfo_screenwidth() / 2) - (x_size / 2))
            _y = int((self.root.winfo_screenheight() / 2) - (y_size / 2))
        else:
            _x = 250 + int(test_socket) * (x_size + 20)
            _y = 100        
        self.root.geometry(f"{x_size}x{y_size}+{_x}+{_y}")
        # define the geometry for the window or frame
        self.root.columnconfigure(0, weight=1)
        # create progress bar
        self.var = StringVar(value=message)
        self.popup = ttk.Label(self.root, textvariable=self.var, anchor="center", font=("Arial", int(fontsize)), foreground=textcolor)
        # pack progress bar into root
        self.popup.pack(fill="both", expand=1)
        # leave window hidden
        if show:
            self.show()

    def hide(self):
        self.root.withdraw()  # hide window
        self.hidden = True

    def show(self):
        self.root.update()
        self.root.deiconify()
        self.root.update()
        self.hidden = False

    # Note: for TestStand access its better to have get/set functions intead of property/setter
    def get_text(self) -> str:
        return self.var.get()
        
    def set_text(self, value: str):
        self.var.set(value)
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
    from time import sleep
    colors = [None, "darkblue", "red"]
    win = BatteryPopup("FLUUUUP", textcolor="darkblue", test_socket=0)
    win.show()
    sleep(5)
    win.set_text("NEW TEXT\nNEW BATTERY\nINSERTED")
    sleep(5)
    win.close()
    #win.root.mainloop()

# END OF FILE

