"""
Library to support creation and printing of data matrix codes
to (label)printers without 3rd party tools like bartender.

All print is done by the use of PNG graphics files.

It works only on WINDOWS as we use win32XXXX modules for print output.

Need to install 'pylibdtmx'


"""

from pylibdmtx.pylibdmtx import encode, decode
from PIL import Image, ImageWin, ImageDraw
from pathlib import Path
import win32print
import win32ui
import win32con
import win32gui

from rrc.eth2serial import Eth2SerialDevice, Eth2SerialSimulationDevice, tcp_send_and_receive_from_server
from rrc.serialport import SerialComportDevice



#--------------------------------------------------------------------------------------------------


def get_available_printer_names() -> list:
    printer_names = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    #flags = win32print.PRINTER_ENUM_NAME
    printers = win32print.EnumPrinters(flags)
    for printer in printers:
        # # variant 1:
        # ph = win32print.OpenPrinter(printer[2])
        # p_info = win32print.GetPrinter(ph, 2)
        # win32print.ClosePrinter(ph)
        # printer_name = p_info["pPrinterName"]
        # printer_names.append(p_info)
        # variant 2
        #print(printer)  # debug
        printer_name = printer[2]
        printer_names.append(printer_name)
        #print(f"printer_name}")
    return printer_names


#--------------------------------------------------------------------------------------------------


def print_available_printer_names() -> None:
    [ print(f"{i}: {p}") for i,p in enumerate(get_available_printer_names()) ]


#--------------------------------------------------------------------------------------------------


def print_pdf_to_printer(printer_name: str, pdf_path: str | Path) -> None:
    printer_handle = win32print.OpenPrinter(printer_name)
    try:
        pdf_path = Path(pdf_path)
        default_printer_info = win32print.GetPrinter(printer_handle, 2)
        printer_info = default_printer_info.copy()
        printer_info['pDevMode'].DriverData = b'RAW'
        pdf_file = open(pdf_path, 'rb')
        #printer = win32ui.CreatePrinterDC(printer_name)
        printer = win32ui.CreateDC()
        printer.CreatePrinterDC(printer_name)
        printer.StartDoc(str(pdf_path.absolute()))
        printer.StartPage()
        pdf_data = pdf_file.read()
        printer.Write(pdf_data)
        printer.EndPage()
        printer.EndDoc()
    except Exception as e:
        print("Exception occurred: ", e)
    finally:
        win32print.ClosePrinter(printer_handle)
        pdf_file.close()


def print_docx_to_printer(printer_name: str, docx_path: str | Path) -> None:
    printer_handle = win32print.OpenPrinter(printer_name)
    try:
        docx_path = Path(docx_path)
        default_printer_info = win32print.GetPrinter(printer_handle, 2)
        printer_info = default_printer_info.copy()
        printer_info['pDevMode'].DriverData = b'RAW'
        docx_file = open(docx_path, 'rb')
        printer = win32ui.CreateDC()
        printer.CreatePrinterDC(printer_name)
        #printer = win32ui.CreatePrinterDC(printer_name)
        printer.StartDoc(str(docx_path.absolute()))
        printer.StartPage()
        docx_data = docx_file.read()
        printer.Write(docx_data)
        printer.EndPage()
        printer.EndDoc()
    except Exception as e:
        print("Exception occurred: ", e)
    finally:
        win32print.ClosePrinter(printer_handle)
        docx_file.close()



#--------------------------------------------------------------------------------------------------


def print_datamatrix_label_0(content: str, printer_name: str = "DEFAULT") -> bool:

    #
    # STEP 1: create a datamatrix bitmap file on drive
    #
    doc_name = "dmtx.png"
    encoded = encode(content.encode("utf8"))
    img = Image.frombytes("RGB", (encoded.width, encoded.height), encoded.pixels)

    file_name = None
    # _fp = Path(doc_name)
    # img.save(_fp)
    # file_name = str(_fp.absolute())

    #
    # STEP 2: load bitmap into printer device context of Windows to print
    #

    #
    # Constants for GetDeviceCaps
    #
    #
    # HORZRES / VERTRES = printable area
    #
    HORZRES = 8
    VERTRES = 10
    #
    # LOGPIXELS = dots per inch
    #
    LOGPIXELSX = 88
    LOGPIXELSY = 90
    #
    # PHYSICALWIDTH/HEIGHT = total area
    #
    PHYSICALWIDTH = 110
    PHYSICALHEIGHT = 111
    #
    # PHYSICALOFFSETX/Y = left / top margin
    #
    PHYSICALOFFSETX = 112
    PHYSICALOFFSETY = 113


    if printer_name.upper() == "DEFAULT":
        printer_name = win32print.GetDefaultPrinter()

    #printer_handle = win32print.OpenPrinter(printer_name)
    #print(win32print.GetPrinter(printer_handle, 2))
    #win32print.CloasePrinter(printer_handle)

    #
    # You can only write a Device-independent bitmap
    #  directly to a Windows device context; therefore
    #  we need (for ease) to use the Python Imaging
    #  Library to manipulate the image.
    #
    # Create a device context from a named printer
    #  and assess the printable size of the paper.
    #
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    printable_area = hDC.GetDeviceCaps(HORZRES), hDC.GetDeviceCaps(VERTRES)
    printer_size = hDC.GetDeviceCaps(PHYSICALWIDTH), hDC.GetDeviceCaps(PHYSICALHEIGHT)
    printer_margins = hDC.GetDeviceCaps(PHYSICALOFFSETX), hDC.GetDeviceCaps(PHYSICALOFFSETY)

    #
    # Open the image, rotate it if it's wider than
    #  it is high, and work out how much to multiply
    #  each pixel by to get it as big as possible on
    #  the page without distorting.
    #
    if file_name is not None:
        img = Image.open(file_name)
    if img.size[0] > img.size[1]:
        img = img.rotate (90)

    ratios = [1.0 * printable_area[0] / img.size[0], 1.0 * printable_area[1] / img.size[1]]
    scale = min(ratios)

    #
    # Start the print job, and draw the bitmap to
    #  the printer device at the scaled size.
    #
    hDC.StartDoc(doc_name)
    hDC.StartPage()

    dib = ImageWin.Dib(img)
    scaled_width, scaled_height = [int(scale * i) for i in img.size]
    x1 = int((printer_size[0] - scaled_width) / 2)
    y1 = int((printer_size[1] - scaled_height) / 2)
    x2 = x1 + scaled_width
    y2 = y1 + scaled_height
    dib.draw(hDC.GetHandleOutput(), (x1, y1, x2, y2))

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


#--------------------------------------------------------------------------------------------------

def print_datamatrix_label(content: str, text: str, printer_name: str = "DEFAULT") -> bool:
    # if you just want to use the default printer, you need
    # to retrieve its name.
    if printer_name.upper() == "DEFAULT":
        printer_name = win32print.GetDefaultPrinter()

    # open the printer.
    hprinter = win32print.OpenPrinter(printer_name)

    # retrieve default settings. this code does not work on
    # win95/98, as GetPrinter does not accept two
    devmode = win32print.GetPrinter(hprinter, 2)["pDevMode"]
    # change paper size and orientation
    # constants are available here:
    # http://msdn.microsoft.com/library/default.asp?url=/library/en-us/intl/nls_Paper_Sizes.asp
    # number 10 envelope is 20
    devmode.PaperSize = 20
    # 1 = portrait, 2 = landscape
    devmode.Orientation = 2
    # create DC using new settings. First get the integer hDC value.
    # Note that we need the name.
    hdc = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
    # next create a PyCDC from the hDC.
    dc = win32ui.CreateDCFromHandle(hdc)

    # now you can set the map mode, etc. and actually print.





    # Constants for GetDeviceCaps:
    # HORZRES / VERTRES = printable area
    HORZRES = 8
    VERTRES = 10
    # LOGPIXELS = dots per inch
    LOGPIXELSX = 88
    LOGPIXELSY = 90
    # PHYSICALWIDTH/HEIGHT = total area
    PHYSICALWIDTH = 110
    PHYSICALHEIGHT = 111
    # PHYSICALOFFSETX/Y = left / top margin
    PHYSICALOFFSETX = 112
    PHYSICALOFFSETY = 113
    # get printer context
    # if printer_name.upper() == "DEFAULT":
    #     printer_name = win32print.GetDefaultPrinter()
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    printable_area = hDC.GetDeviceCaps(HORZRES), hDC.GetDeviceCaps(VERTRES)
    printer_size = hDC.GetDeviceCaps(PHYSICALWIDTH), hDC.GetDeviceCaps(PHYSICALHEIGHT)
    printer_margins = hDC.GetDeviceCaps(PHYSICALOFFSETX), hDC.GetDeviceCaps(PHYSICALOFFSETY)
    # create datamatrix code

    encoded = encode(content.encode("utf8"))
    img = Image.frombytes("RGB", (encoded.width, encoded.height), encoded.pixels)
    # rotate it if it's wider than it is high, and work out how much to multiply
    #  each pixel by to get it as big as possible on the page without distorting.
    if img.size[0] > img.size[1]:
        img = img.rotate (90)
    ratios = [1.0 * printable_area[0] / img.size[0], 1.0 * printable_area[1] / img.size[1]]
    scale = min(ratios)
    # Start the print job, and draw the bitmap to
    #  the printer device at the scaled size.
    doc_name = "dmtx.png"
    hDC.StartDoc(doc_name)
    hDC.StartPage()

    dib = ImageWin.Dib(img)
    scaled_width, scaled_height = [int(scale * i) for i in img.size]
    x1 = int((printer_size[0] - scaled_width) / 2)
    y1 = int((printer_size[1] - scaled_height) / 2)
    x2 = x1 + scaled_width
    y2 = y1 + scaled_height

    dib.draw(hDC.GetHandleOutput(), (x1, y1, x2, y2))

    # win32gui.DrawText(
    #     hDC,
    #     "Printed by Python!",
    #     -1,
    #     (0, 0, int(printer_size[0] * 0.9), int(printer_size[1] * 0.9)),
    #     win32con.DT_RIGHT | win32con.DT_BOTTOM | win32con.DT_SINGLELINE,
    # )

    # draw = ImageDraw.Draw(dib)

    txt = text.split("\r")
    pixel_scale = 84
    for idx,line in enumerate(txt):
        print("Text line {:d}: {:s}".format(idx, line))

        # font=win32gui.LOGFONT()
        # font.lfHeight=int(100/1.5)
        # font.lfWidth=(int(font.lfHeight/4))
        # font.lfWeight=150
        # hf=win32gui.CreateFontIndirect(font)
        # win32gui.SelectObject(hDC,hf)
        # win32gui.DrawText(hDC,trialtext,-1,(ulc_x,ulc_y,lrc_x,lrc_y),win32con.DT_LEFT|win32con.DT_TOP)

        # font=win32gui.LOGFONT()
        # font.lfHeight=int(printerheight/20)
        # font.lfWidth=(font.lfHeight/2)
        # font.lfWeight=10
        # hf2=win32gui.CreateFontIndirect(font)
        # win32gui.SelectObject(hDC,hf2)
        # win32gui.DrawText(hDC,PrintText,-1,(ulc_x,ulc_y,lrc_x,lrc_y),win32con.DT_LEFT|win32con.DT_BOTTOM)

        hDC.TextOut(12, idx * pixel_scale, line)
        #draw.text((5, idx*pixel_scale), line)

    # #draw.draw(hDC.GetHandleOutput(), (x1, y1, x2, y2))

    # fontdata = { 'name':'Arial', 'height':15}
    # font = win32ui.CreateFont(fontdata)
    # hDC.SelectObject(font)

    INCH = 1440   # twips - 1440 per inch allows fine res
    fontdata = { 'name':'Arial', 'height':int(25*scale)}
    font = win32ui.CreateFont(fontdata)
    hDC.SelectObject(font)
    #dc = win32ui.CreateDC()
    #dc.CreatePrinterDC(printer_name)
    #dc.StartDoc('My Python Document')
    #dc.StartPage()
    # note: upper left is 0,0 with x increasing to the right,
    #       and y decreasing (negative) moving down
    hDC.SetMapMode(win32con.MM_TWIPS)
    # Centers "TEST" about an inch down on page
    hDC.DrawText('TEST', (0,INCH*-1,INCH*8,INCH*-2), win32con.DT_CENTER )
    #dc.EndPage()
    #dc.EndDoc()
    #del dc
    # for i in range(len(samplePrintText)):
    #     dc.TextOut(0,i, samplePrintText[i])
    #     dc.MoveTo(0, i)
    #     dc.LineTo(0, i)


    # del draw

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()



#--------------------------------------------------------------------------------------------------


def run_scan_and_print(resource_string: str, printer_name: str) -> None:
    """_summary_

    Args:
        resource_string (str): _description_
        printer_name (str): _description_
    """

    if "," in resource_string:
        scanner = SerialComportDevice(resource_string, termination="\r")  # COM port
    else:
        scanner = Eth2SerialDevice(resource_string, termination="\r")   # socket port
    while 1:
        print(f"Please scan label code: ", end=None)
        try:
            content = scanner.request(None, timeout=2.0, encoding=None)
            print(f"got '{content}'")
            print_datamatrix_label(content, printer_name)
        except TimeoutError:
            pass  # just retry



#--------------------------------------------------------------------------------------------------

def test_create_simple_label() -> None:
    encoded = encode('RRC Zellsorter: Problem solved!'.encode('utf8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    _fp = Path('dmtx.png')
    img.save(_fp)
    print(decode(Image.open(_fp)))




#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":

    test_create_simple_label()  # on disk

    printer_name = "Microsoft Print to PDF"
    #printer_name = "\\\\printhost-2k16.rrc\\C-1-58-M6630cidn"
    print_datamatrix_label("TESTLABEL XYZ", "Zeile 1\rZeile 2", printer_name=printer_name)

    RESOURCE_STR = "COM38,9600,8N1"  # manual scanner
    #RESOURCE_STR = "172.21.101.31:2000"  # HOM Line Corepack
    #run_scan_and_print(printer_name, RESOURCE_STR)  # loop blocks until CTRL-C

    #print_docx_to_printer(printer_name, "./Python_Libs/rrc/hallo_welt.docx")

# END OF FILE