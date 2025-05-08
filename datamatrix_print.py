"""
Library to support creation and printing of data matrix codes
to (label)printers without 3rd party tools like bartender.

All print is done by the use of PNG graphics files.

It works only on WINDOWS as we use win32XXXX modules for print output.

Need to install 'pylibdtmx'


"""

import base64
#import math
from io import BytesIO
import mmap
from PIL.ImageFile import ImageFile
from pylibdmtx import pylibdmtx
from qrcode import QRCode
from pystrich.datamatrix import DataMatrixEncoder
from pystrich.qrcode import QRCodeEncoder
from PIL import Image, ImageWin, ImageDraw, ImageOps
from pathlib import Path
import win32print
import win32ui
import win32con
import win32gui

from rrc.eth2serial import Eth2SerialDevice, Eth2SerialSimulationDevice, tcp_send_and_receive_from_server
from rrc.serialport import SerialComportDevice


INCH_TWIPS: int = 1440   # twips - 1440 per inch allows fine res
MM_TWIPS: float = INCH_TWIPS / 25.4  # => 56.6929 per mm but we need float


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
"""
printer_name = "MXP T11"
raw_data = bytes(label_text, "utf-8")

drivers = win32print.EnumPrinterDrivers(None, None, 2)
hPrinter = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(hPrinter, 2)
for driver in drivers:
    if driver["Name"] == printer_info["pDriverName"]:
        printer_driver = driver

raw_type = "XPS_PASS" if printer_driver["Version"] == 4 else "RAW"

try:
    hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
    try:
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, raw_data)
        win32print.EndPagePrinter(hPrinter)
    except Exception as e:
        win32print.EndDocPrinter(hPrinter)
        message.warning(request, f"Error! {e}")

except Exception as e:
    win32print.ClosePrinter(hPrinter)
    message.warning(request, f'Error! {e}')
"""


def pil_to_html_imgdata(img: Image, fmt: str = "PNG") -> str:
    """Convert a PIL image into HTML-displayable data.

    The result is a string ``data:image/FMT;base64,xxxxxxxxx`` which you
    can provide as a "src" parameter to a ``<img/>`` tag.

    Examples

    >>> data = pil_to_html_imgdata(my_pil_img)
    >>> html_data = '<img src="%s"/>' % data

    Args:
        img (Image): A Pillow image object.
        fmt (str, optional): Data (file) format string. Defaults to "PNG".

    Returns:
        str: HTML string of displayable data.
    """

    buffered = BytesIO()
    img.save(buffered, format=fmt)
    img_str = base64.b64encode(buffered.getvalue())
    return f"data:image/{fmt.lower()};charset=utf-8;base64,{img_str.decode()}"


def qr_code(content,
            cellsize: int = 5,
            optimize: int = 20,
            border: int = None,
            border_color: str ="black",
            fill_color: str = "black",
            back_color: str = "white",
            **qr_code_params) -> Image.Image:
    """Return a QR code's image data using PyQRcode library.
    Useful if colored QR code or more options are needed.

    Examples

    >>> data = qr_code('egf45728')
    >>> html_data = '<img src="%s"/>' % data

    Args:
        content (str): Data to be encoded in the QR code.
        ecl (_type_, optional): _description_. Defaults to None.
        cellsize (int, optional): _description_. Defaults to 5.
        optimize (int, optional): Chunk length optimization setting. Defaults to 20.
        border (int, optional): Draws a border around if not None. Defaults to None.
        fill_color (str, optional): Colors to use for QRcode and its background. Defaults to "black".
        back_color (str, optional): Colors to use for QRcode and its background. Defaults to "white".

        **qr_code_params
            Parameters of the ``QRCode`` constructor, such as ``version``,``error_correction``, ``box_size``, ``border``.

    Returns:
        Image.Image | ImageFile: A Pillow image object.
    """

    # qrcode library
    params = dict(box_size=cellsize, border=border if border else 0)
    params.update(qr_code_params)
    qr = QRCode(**params)
    qr.add_data(content, optimize=optimize)
    qri = qr.make_image(fill_color=fill_color, back_color=back_color)
    img = qri.get_image()
    # create a border by PIL library
    if border is None:
        img = img.crop(ImageOps.invert(img).getbbox())
    else:
        img = ImageOps.expand(img, border=border, fill=border_color)
    return img



def datamatrix(content, cellsize: int = 5, border: int = None, border_color: str = "black") -> Image.Image | ImageFile:

    """Return a datamatrix's image data.

    Examples

    >>> data = datamatrix('EGF')
    >>> html_data = '<img src="%s"/>' % data

    Args:
        content (_type_): Data to be encoded in the datamatrix.
        cellsize (int, optional): Size of the codematrix. Defaults to 5.
        border (bool, optional): If None, there will be no border or margin to the datamatrix image. Defaults to None.

    Returns:
        Image.Image | ImageFile: A Pillow image object.
    """

    # # pystrich library:
    # encoder = DataMatrixEncoder(content)
    # img_data = encoder.get_imagedata(cellsize=cellsize)
    # #img_data = encoder.get_imagedata()
    # img = Image.open(BytesIO(img_data))

    # pylibdmtx library:
    encoded = pylibdmtx.encode(content)
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)

    if border is None:
        img = img.crop(ImageOps.invert(img).getbbox())
    else:
        img = ImageOps.expand(img, border=border, fill=border_color)
    return img


#--------------------------------------------------------------------------------------------------

def gdc_scale_position_and_size(dc, x: float, y: float, width: float, height: float) -> tuple:
    """Calculates position and dimension tuple to paint an image into GDC.
    Assumes CM is being defined.

    Origin is top left, thus Y value is converted into negative number as well
    as height, if they are not provided negative already.

    Args:
        dc (PyCDC): Python device context
        x (float): Horizontal position offset in mm
        y (float): Vertical position offset in mm
        width (float): Width of the image in mm
        height (float): Height of the image in mm

    Returns:
        tuple: (x1, y1, x2, y2) to be passed into GDC.Draw() function
    """
    global MM_TWIPS

    DPI_y = dc.GetDeviceCaps(win32con.LOGPIXELSY)
    DPI_x = dc.GetDeviceCaps(win32con.LOGPIXELSX)
    ofs_y = dc.GetDeviceCaps(win32con.PHYSICALOFFSETY)
    ofs_x = dc.GetDeviceCaps(win32con.PHYSICALOFFSETX)
    x1 = (abs(x) + ofs_x) * MM_TWIPS
    y1 = (-abs(y) + ofs_y) * MM_TWIPS
    x2 = x1 + (abs(width) * MM_TWIPS)
    y2 = y1 - (abs(height) * MM_TWIPS)  # neg needed
    return round(x1),round(y1),round(x2),round(y2)


#--------------------------------------------------------------------------------------------------


def calc_fontsize(dc, PointSize: float) -> int:
    """Assumes MM_TWIPS mapping mode.

    Args:
        dc (PyCDC): Python device context
        PointSize (float): Font size in points, e.g. 12 or 10.5

    Returns:
        int: Fontsize in device DPI assuming that point means size in 72 DPI
    """

    DPI_y = dc.GetDeviceCaps(win32con.LOGPIXELSY)
    return int(-(PointSize * DPI_y) / 72)  # where is 72 taken from ?


#--------------------------------------------------------------------------------------------------


def draw_img(dc, img: Image, x: float, y: float, w: float = None, h: float = None) -> None:
    """Draws an image into Windows device context.

    Args:
        dc (PyCDC): Python device context
        img (Image): _description_
        x (float): _description_
        y (float): _description_
        w (float, optional): _description_. Defaults to None.
        h (float, optional): _description_. Defaults to None.
    """

    dib = ImageWin.Dib(img)
    _w, _h = dib.size
    dib.draw(dc.GetHandleOutput(),
             gdc_scale_position_and_size(dc,  x,  y,
                                         _w if w is None else w,
                                         _h if h is None else h))


#--------------------------------------------------------------------------------------------------


def draw_text_at(dc, text: str, x: float, y: float, width: float = None, height: float = None, font_size: float = None, align: int = win32con.DT_LEFT) -> float:
    global MM_TWIPS

    _x = int(x * MM_TWIPS)
    #_sy = math.copysign(y)
    #_sy = int(y/abs(y)) if x != 0 else 1
    _sy = -1 if y < 0 else 1
    _y = -int(abs(y) * MM_TWIPS)
    if font_size:
        if width:
            _x1 = _x + int(abs(width) * MM_TWIPS)
        else:
            _x1 = len(text) * font_size
        _y1 = _y + font_size
    else:
        _x1 = _x + int(abs(width) * MM_TWIPS)
        _y1 = _y - int(abs(height) * MM_TWIPS)
    _height = dc.DrawText(text, (_x, _y, _x1, _y1), align)
    return _sy * abs(_height) / MM_TWIPS  # -> mm, keeping the sign of INPUT y


#--------------------------------------------------------------------------------------------------

def draw_box_at(dc, x: float, y: float, w: float, h: float) -> None:
    global MM_TWIPS

    _x = x * MM_TWIPS
    _y = -abs(y) * MM_TWIPS
    _w = w * MM_TWIPS
    _h = -abs(h) * MM_TWIPS
    dc.MoveTo((int(_x), int(_y)))
    dc.LineTo((int(_x + _w), int(_y)))
    dc.LineTo((int(_x + _w), int(_y + _h)))
    dc.LineTo((int(_x), int(_y + _h)))
    dc.LineTo((int(_x), int(_y)))


#--------------------------------------------------------------------------------------------------


def print_datamatrix_label(content: str, text: str, printer_name: str = "DEFAULT") -> bool:

    # printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    # PRINTER_DEFAULTS = {"DesiredAccess":win32print.PRINTER_ALL_ACCESS}
    # temprint = printers[3][2]

    # if you just want to use the default printer, you need to retrieve its name.
    if printer_name.upper() == "DEFAULT":
        printer_name = win32print.GetDefaultPrinter()

    # open the printer.
    hprinter = win32print.OpenPrinter(printer_name)
    #hprinter = win32print.OpenPrinter(temprint, PRINTER_DEFAULTS)  # does not work

    # retrieve default settings.
    # Level 	Structure
    # 0	        If the Command parameter is PRINTER_CONTROL_SET_STATUS, pPrinter must contain a DWORD value that specifies the new printer status to set.
    #           For a list of the possible status values, see the Status member of the PRINTER_INFO_2 structure. Note that PRINTER_STATUS_PAUSED and PRINTER_STATUS_PENDING_DELETION are not valid status values to set.
    #           If Level is 0, but the Command parameter is not PRINTER_CONTROL_SET_STATUS, pPrinter must be NULL.
    #
    # 2	        A PRINTER_INFO_2 structure containing detailed information about the printer.
    # 3	        A PRINTER_INFO_3 structure containing the printer's security information.
    # 4	        A PRINTER_INFO_4 structure containing minimal printer information, including the name of the printer, the name of the server, and whether the printer is remote or local.
    # 5	        A PRINTER_INFO_5 structure containing printer information such as printer attributes and time-out settings.
    # 6	        A PRINTER_INFO_6 structure specifying the status value of a printer.
    # 7	        A PRINTER_INFO_7 structure. The dwAction member of this structure indicates whether SetPrinter should publish, unpublish, re-publish, or update the printer's data in the directory service.
    # 8	        A PRINTER_INFO_8 structure specifying the global default printer settings.
    # 9	        A PRINTER_INFO_9 structure specifying the per-user default printer settings.
    #
    level = 2
    properties = win32print.GetPrinter(hprinter, level)
    devmode = properties["pDevMode"]

    # Change the default paper source
    #devmode.DefaultSource = win32con.DMBIN_MANUAL
    devmode.DefaultSource = win32con.DMBIN_AUTO
    devmode.Fields = devmode.Fields | win32con.DM_DEFAULTSOURCE

    #win32con.DM_FORMNAME
    devmode.MediaType = win32con.DMMEDIA_STANDARD
    devmode.DitherType = win32con.DMDITHER_NONE

    # change paper size and orientation
    # constants are available here: win32con.DMPAPERxxxx
    #devmode.PaperSize = win32con.DMPAPER_A5
    devmode.PaperSize = win32con.DMPAPER_A4
    # 1 = portrait, 2 = landscape
    #devmode.Orientation = win32con.DMORIENT_LANDSCAPE
    devmode.Orientation = win32con.DMORIENT_PORTRAIT
    print(devmode.PrintQuality)
    #devmode.PrintQuality = 120  # DPI ?
    # or define custom size for context
    #devmode.PaperWidth = 6000  # x 0.1mm
    #devmode.PaperLength = 300  # x 0.1mm
    #devmode.PaperSize = win32con.DMPAPER_USER
    ##devmode.PaperSize = 0
    #win32print.SetPrinter(handle, level, attributes, 0)  # does not work!

    # Write these changes back to the printer
    win32print.DocumentProperties(None, hprinter, printer_name, devmode, devmode, win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER) # | win32con.DM_IN_PROMPT)  # validate devmode structure
    #win32print.SetPrinter(hprinter, 2, properties, 0)  # does not work due to access rights

    #form_name = "my_silly_label_size"
    # try:
    #     win32print.DeleteForm(hprinter, form_name)
    # except Exception:
    #     pass
    # tForm = ({
    #     'Flags': 2,  # form_user ?
    #     'Name': form_name,
    #     'Size': {
    #         #'cx': 215900,   # x 0.001mm
    #         #'cy': 279400,  # x 0.001mm
    #         'cx': 120000,  # x 0.001mm
    #         'cy':  10000,  # x 0.001mm
    #     },
    #     'ImageableArea': {
    #         'left': 0,
    #         'top': 0,
    #         #'right': 215900,
    #         #'bottom': 279400,
    #         'right': 120000,
    #         'bottom': 10000,
    #     }
    # })
    # try:
    #     win32print.AddForm(hprinter, tForm)
    # except Exception as ex:
    #     win32print.SetForm(hprinter, form_name, tForm)  # use our format
    #win32print.DeleteForm(hprinter, form_name)
    #x = win32print.GetForm(hprinter, form_name)

    # create DC using new settings. First get the integer hDC value.
    # Note that we need the name.
    hdc = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
    # next create a PyCDC from the hDC.
    dc = win32ui.CreateDCFromHandle(hdc)

    # now you can set the map mode, etc. and actually print.

    if 1:  # show device infos
        print("LOGI RES", win32con.HORZRES, win32con.VERTRES, dc.GetDeviceCaps(win32con.HORZRES), dc.GetDeviceCaps(win32con.VERTRES))
        print("LOGI PIXELS (DPI)", win32con.LOGPIXELSX, win32con.LOGPIXELSY, dc.GetDeviceCaps(win32con.LOGPIXELSX), dc.GetDeviceCaps(win32con.LOGPIXELSY))
        print("PHYSICAL W/H", win32con.PHYSICALWIDTH, win32con.PHYSICALHEIGHT, dc.GetDeviceCaps(win32con.PHYSICALWIDTH), dc.GetDeviceCaps(win32con.PHYSICALHEIGHT))
        print("PHYSICAL OFFSETS X/Y", win32con.PHYSICALOFFSETX, win32con.PHYSICALOFFSETY, dc.GetDeviceCaps(win32con.PHYSICALOFFSETX), dc.GetDeviceCaps(win32con.PHYSICALOFFSETY))
    # HORZRES / VERTRES = printable area
    # LOGPIXELS = dots per inch (DPI)
    printable_area = dc.GetDeviceCaps(win32con.HORZRES), dc.GetDeviceCaps(win32con.VERTRES)
    # PHYSICALWIDTH/HEIGHT = total area
    printer_size = dc.GetDeviceCaps(win32con.PHYSICALWIDTH), dc.GetDeviceCaps(win32con.PHYSICALHEIGHT)
    # PHYSICALOFFSETX/Y = left / top margin
    printer_margins = dc.GetDeviceCaps(win32con.PHYSICALOFFSETX), dc.GetDeviceCaps(win32con.PHYSICALOFFSETY)


    img1 = datamatrix(content, border=1)
    dib1 = ImageWin.Dib(img1)
    img2 = qr_code(content, border=1)
    dib2 = ImageWin.Dib(img2)

    # # rotate it if it's wider than it is high
    # if img.size[0] > img.size[1]:
    #     img = img.rotate (90)

    # Start the print job, and draw the bitmap to
    #  the printer device at the scaled size.
    doc_name = "dmtx.png"
    dc.StartDoc(doc_name)
    dc.StartPage()

    dc.SetMapMode(win32con.MM_TWIPS)  # Note: upper left is 0,0 with x increasing to the right and y decreasing (negative) moving down
    #win32con.MM_HIMETRIC
    draw_img(dc, img2,   5, 5, w=30, h=30)
    draw_img(dc, img1, 125, 5, w=30, h=30)

    font1size = calc_fontsize(dc, 32)
    fontdata = {
        "name": "Arial",
        "height": font1size,
        "italic": True,
        "weight": win32con.FW_NORMAL,
    }
    font1 = win32ui.CreateFont(fontdata)
    font2size = calc_fontsize(dc, 48)
    fontdata = {
        "name": "Arial",
        "height": font2size,
        "italic": False,
        "weight": win32con.FW_LIGHT,
    }
    font2 = win32ui.CreateFont(fontdata)

    txt = text.split("\n")
    pixel_scale = font2size
    #bounding_box_start_y = -(int(5 * MM_TWIPS))
    bounding_box_y: float = 5  # would normally need negative sign position, but our function converts it on demand
    dc.SelectObject(font2)
    for idx,line in enumerate(txt):
        print("Text line {:d}: {:s}".format(idx, line))
        bounding_box_y += draw_text_at(dc, line, 40, bounding_box_y, width=120, font_size=font2size)
        #dc.SelectObject(font1)
        #dc.TextOut(12, idx * pixel_scale, line)

    draw_box_at(dc, 0,0, 160, 40)

    dc.EndPage()
    dc.EndDoc()
    dc.DeleteDC()



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
    encoded = pylibdmtx.encode('RRC Zellsorter: Problem solved!'.encode('utf8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    _fp = Path('dmtx.png')
    img.save(_fp)
    print(pylibdmtx.decode(Image.open(_fp)))



#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":

    test_create_simple_label()  # on disk

    printer_name = "Microsoft Print to PDF"
    #printer_name = "\\\\printhost-2k16.rrc\\C-1-58-M6630cidn"

    _content = "00231872347699829949"
    _content = "Schacht #1\nZelltyp ICR18650E28-XX"

    print_datamatrix_label(_content, _content, printer_name=printer_name)  # test buggy QRCode
    # print_datamatrix_label(
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789",
    #     "Zeile 1\rZeile 2", printer_name=printer_name)  # test buggy Datamatrix
    #print_datamatrix_label("TESTLABEL XYZ", "Zeile 1\rZeile 2", printer_name=printer_name)

    RESOURCE_STR = "COM38,9600,8N1"  # manual scanner
    #RESOURCE_STR = "172.21.101.31:2000"  # HOM Line Corepack
    #run_scan_and_print(printer_name, RESOURCE_STR)  # loop blocks until CTRL-C

    #print_docx_to_printer(printer_name, "./Python_Libs/rrc/hallo_welt.docx")

# END OF FILE