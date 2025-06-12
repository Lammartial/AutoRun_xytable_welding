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
from pathlib import Path
from PIL.ImageFile import ImageFile
from PIL import Image, ImageWin, ImageDraw, ImageOps
from pylibdmtx import pylibdmtx
from qrcode import QRCode
from pystrich.code128 import Code128Encoder, Code128Renderer
from pystrich.datamatrix import DataMatrixEncoder
from pystrich.qrcode import QRCodeEncoder
from barcode import get_barcode_class, PROVIDED_BARCODES
from barcode.writer import ImageWriter as barcode_ImageWriter, SVGWriter as barcode_SVGWriter

import win32print
import win32ui
import win32con
import win32gui

from rrc.eth2serial import Eth2SerialDevice, Eth2SerialSimulationDevice, tcp_send_and_receive_from_server
from rrc.serialport import SerialComportDevice


#--------------------------------------------------------------------------------------------------


INCH_TWIPS: int = 1440  # TWIPS - 1440 per inch allows fine res
                        # NOTE:
                        #   20 TWIPS per point (need to scale font)
                        #   72 points per inch
                        # 1440 TWIPS per inch
MM_TWIPS: float = INCH_TWIPS / 25.4  # => 56.6929 per mm but we need float



# NOTE:
# The Zebra ZD220 Printer should be set to this size manually and thermal temperature
# to 24 with original Zebra transfer foil.
#

LABEL_LAYOUT_DEFINITION = {
    # Width x Height in mm
    "76mm_x_51mm": {
        "dimensions": {
            "width": 76,
            "height": 51,
        },
        "textbox": [
                # for each line define a separate entry: (if more lines are used than entries: last entry will be repeated)
                # (x, y, width, height, font) - "None" for y/height means: auto/calculated
                (30,    5, 43, None, "big"),    # line 1
                (30, None, 43, None, "big"),    # line 2
                (30, None, 43, None, "big"),    # line 3
                ( 5, None, 73, None, "std"),    # line 4
                ( 5, None, 73, None, "std"),    # line 5
                ( 5, None, 73, None, "small"),  # line 6
        ],
        "codebox": [
            # for each code define one entry:
            # (x, y, w, h, code_type, border) - x,y,w,h in mm; border 1 or 0
            # Supported code types:
            # 2D: 'mx' | 'matrix' | 'datamatrix' -> Data Matrix Code, anything else -> QR-code
            # Bar: 'codabar', 'code128', 'code39', 'ean', 'ean13', 'ean13-guard', 'ean14', 'ean8', 'ean8-guard', 'gs1',
            #      'gs1_128', 'gtin', 'isbn', 'isbn10', 'isbn13', 'issn', 'itf', 'jan', 'nw-7', 'pzn', 'upc', 'upca'
            (3.0, 4.5, 25, 25, "mx", 0),
        ],
        "fonts": {
            # definition of fonts
            "std": {
                "name": "Arial",
                "size": 32,  # in points, used to calculate height in DPI
                "height": None,  # in DPI, will be calculated if None
                "italic": False,
                "weight": win32con.FW_NORMAL,
            },
            "big": {
                "name": "Arial",
                "size": 48,
                "height": None,
                "italic": False,
                "weight": win32con.FW_NORMAL,
            },
            "small": {
                "name": "Arial",
                "size": 16,
                "height": None,
                "italic": True,
                "weight": win32con.FW_LIGHT,
            },
        },
    },
    #--------------------------------------------
    "160mm_x_40mm": {
         "dimensions": {
            "width": 160,
            "height": 40,
        },
        "textbox": [
                # for each line define a separate entry: (if more lines are used than entries: last entry will be repeated)
                # (x, y, width, height, font) - "None" for y/height means: auto/calculated
                (40, 5, 120, None, "std"),    # first line at y=5, all other lines will be put under each other (auto y calculation)
        ],
        "codebox": [
            # for each code define one entry:
            # (x, y, w, h, code_type, border) - x,y,w,h in mm; border 1 or 0
            # Supported code types:
            # 2D: 'mx' | 'matrix' | 'datamatrix' -> Data Matrix Code, anything else -> QR-code
            # Bar: 'codabar', 'code128', 'code39', 'ean', 'ean13', 'ean13-guard', 'ean14', 'ean8', 'ean8-guard', 'gs1',
            #      'gs1_128', 'gtin', 'isbn', 'isbn10', 'isbn13', 'issn', 'itf', 'jan', 'nw-7', 'pzn', 'upc', 'upca'
            (2.5, 2.5, 25, 25, "mx", 1),  # this is datamatrix
            (125, 2.5, 25, 25, "qr", 1),  # this is QR-code
            #(2.5, 15, 55, 25, "ean", 1),  # this is EAN barcode
            (2.5, 15, 55, 25, "code128", 1),  # this is Code128 barcode
        ],
        "fonts": {
            # definition of fonts
            "std": {
                "name": "Arial",
                "size": 32,  # in points, used to calculate height in DPI
                "height": None,  # in DPI, will be calculated if None
                "italic": True,
                "weight": win32con.FW_NORMAL,
            },
        },
    }


}

#--------------------------------------------------------------------------------------------------


def _calc_font_heights_for_labeldefinition(L, dc = None):
    for k,v in L["fonts"].items():
        if "size" in v:
            L["fonts"][k]["height"] = calc_fontheight_in_dpi(v["size"], dc=dc)
            del L["fonts"][k]["size"]  # size keyword not allowed in further processing
    return L


#--------------------------------------------------------------------------------------------------


def label_size_76mm_x_51mm(dc = None) -> dict:
    """For Labels of size 76mm x 51mm with one datamatrx code

    The Zebra ZD220 Printer should be set to this size manually and thermal temperature
    to 24 with original Zebra transfer foil.

    Args:
        dc (optional, PyCDC): Python device context wrapper

    Returns:
        dict: layout dictionary
    """

    global LABEL_LAYOUT_DEFINITION

    return _calc_font_heights_for_labeldefinition(LABEL_LAYOUT_DEFINITION["76mm_x_51mm"], dc=dc)


#--------------------------------------------------------------------------------------------------


def label_size_160mm_x_40mm(dc = None) -> dict:
    """Layout for Label 160mm x 40mm with one datamatrix and one QR code.

    Args:
        dc (optional, PyCDC): Python device context wrapper

    Returns:
        dict: layout dictionary
    """

    global LABEL_LAYOUT_DEFINITION

    return _calc_font_heights_for_labeldefinition(LABEL_LAYOUT_DEFINITION["160mm_x_40mm"], dc=dc)


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


def image_to_html_imgtag_data(img: Image, fmt: str = "PNG") -> str:
    """Convert a PIL image into HTML-displayable data.

    The result is a string ``data:image/FMT;base64,xxxxxxxxx`` which you
    can provide as a "src" parameter to a ``<img/>`` tag.

    Examples

    >>> data = image_to_html_imgdata(my_pil_img)
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


#--------------------------------------------------------------------------------------------------


def qr_code(content,
            to_html: bool = False,
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
    if to_html:
        return image_to_html_imgtag_data(img)
    else:
        return img


#--------------------------------------------------------------------------------------------------


def datamatrix(content,
               to_html: bool = False,
               cellsize: int = 5,
               border: int = None,
               border_color: str = "black") -> Image.Image:
    """Return a datamatrix's image data.

    Examples

    >>> data = datamatrix('EGF')
    >>> html_data = '<img src="%s"/>' % data

    Args:
        content (_type_): Data to be encoded in the datamatrix.
        cellsize (int, optional): Size of the codematrix. Defaults to 5.
        border (bool, optional): If None, there will be no border or margin to the datamatrix image. Defaults to None.

    Returns:
        Image.Image: A Pillow image object.
    """

    # # pystrich library:
    # encoder = DataMatrixEncoder(content)
    # img_data = encoder.get_imagedata(cellsize=cellsize)
    # #img_data = encoder.get_imagedata()
    # img = Image.open(BytesIO(img_data))

    # pylibdmtx library:
    encoded = pylibdmtx.encode(content.encode('utf-8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)

    if border is None:
        img = img.crop(ImageOps.invert(img).getbbox())
    else:
        img = ImageOps.expand(img, border=border, fill=border_color)
    if to_html:
        return image_to_html_imgtag_data(img)
    else:
        return img


#--------------------------------------------------------------------------------------------------


def barcode(content,
            to_html: bool = False,
            barcode_class: str = "code128",
            fmt: str = "png",
            add_checksum: bool = True,
            **writer_options) -> str | Image.Image:
    """Return a barcode's image data either as a Pillow image object or as HTML <img> tag.

    Powered by the Python library ``python-barcode``. See this library's
    documentation for more details.

    Examples
    --------

    >>> data = barcode('EGF12134', barcode_class='code128')
    >>> html_data = '<img src="%s"/>' % data

    Examples of writer options:

    >>> { 'background': 'white',
    >>>   'font_size': 10,
    >>>   'foreground': 'black',
    >>>   'module_height': 15.0,
    >>>   'module_width': 0.2,
    >>>   'quiet_zone': 6.5,
    >>>   'text': '',
    >>>   'text_distance': 5.0,
    >>>   'write_text': True
    >>> }

    Args:
        content (str | float | int): Data to be encoded in the datamatrix.
        barcode_class (str, optional): Class/standard to use to encode the data. Different standards have
            different constraints. Defaults to "code128".
        fmt (str, optional): Image type, either svg or png. Defaults to "png".
        add_checksum (bool, optional): If True add a checksum to the barcode. Defaults to True.
        to_html (bool, optional): If True, the image is returned as <img> HTML tag, else image is returned
            as Pilliow object. Defaults to False.
        writer_options: Various options for the writer to tune the appearance of the barcode
            (see python-barcode documentation).
    Returns:
        str | Image.Image: Image either as Pillow object or as image_base64_data. which is
            a string ``data:image/png;base64,xxxxxxxxx`` which you can provide as a
            "src" parameter to a ``<img/>`` tag.

    """

    constructor = get_barcode_class(barcode_class)
    content = str(content).zfill(constructor.digits)
    writer = {
        "svg": barcode_SVGWriter,
        "png": barcode_ImageWriter,
    }[fmt]
    if "add_checksum" in getattr(constructor, "__init__").__code__.co_varnames:
        barcode_img = constructor(content, writer=writer(), add_checksum=add_checksum)
    else:
        barcode_img = constructor(content, writer=writer())
    img = barcode_img.render(writer_options=writer_options)
    if to_html:
        if fmt == "png":
            return image_to_html_imgtag_data(img, fmt="PNG")
        else:
            # SVG can be transformed directly into HTML
            prefix = "data:image/svg+xml;charset=utf-8;base64,"
            return prefix + base64.b64encode(img).decode()
    else:
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


def calc_fontheight_in_dpi(PointSize: float, dc = None) -> int:
    """Assumes MM_TWIPS mapping mode.

    NOTE:     20 TWIPS per point
              72 points per inch
            1440 TWIPS per inch

            Anyway the printer driver scales the fonts to 600 DPI regardsless of the printer setting.
            Thus we set the DPI_y fixed to 600.

    Args:
        PointSize (float): Font size in points, e.g. 12 or 10.5
        dc (optional, PyCDC): Python device context. If given, the DPI scale of the device is being used,
            else a fixed DPI of 600 is used.

    Returns:
        int: Fontsize in device DPI assuming that point means size in 72 DPI
    """

    if dc is not None:
        DPI_y = dc.GetDeviceCaps(win32con.LOGPIXELSY)
    else:
        DPI_y = 600  # see the note above
    return int(-((PointSize / 72) * DPI_y))  # 72 points per inch


#--------------------------------------------------------------------------------------------------


def draw_img_at(dc, img: Image, x: float, y: float, w: float = None, h: float = None) -> None:
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

def print_datamatrix_label(content: str, text: str, label_layout: str, printer_name: str = "DEFAULT") -> bool:
    """_summary_

    Args:
        content (str): _description_
        text (str): _description_
        label_layout (str): _description_
        printer_name (str, optional): _description_. Defaults to "DEFAULT".

    Returns:
        bool: _description_
    """

    global LABEL_LAYOUT_DEFINITION

    assert label_layout in LABEL_LAYOUT_DEFINITION, f"Unknown label definition '{label_layout}'"

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

    if 0:
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

    # img_mx = datamatrix(content, border=1)
    # #img_mx = datamatrix(content.replace("\n",""), border=1)
    # #img_mx = datamatrix("00231872347699829949")
    # dib1 = ImageWin.Dib(img_mx)
    # img_qr = qr_code(content, border=1)
    # dib2 = ImageWin.Dib(img_qr)

    # # rotate it if it's wider than it is height
    # if img.size[0] > img.size[1]:
    #     img = img.rotate (90)

    def activate_font(dc, fontdata):
        _font = win32ui.CreateFont(fontdata)
        _height = fontdata["height"]
        dc.SelectObject(_font)
        return _font, _height

    def calc_font_heights_for_labeldefinition(L, dc = None):
        for k,v in L["fonts"].items():
            if "size" in v:
                L["fonts"][k]["height"] = calc_fontheight_in_dpi(v["size"], dc=dc)
                del L["fonts"][k]["size"]  # size keyword not allowed in further processing
        return L


    # Start the print job, and draw the bitmap to
    #  the printer device at the scaled size.
    doc_name = "dmtx.png"
    dc.StartDoc(doc_name)
    dc.StartPage()

    dc.SetMapMode(win32con.MM_TWIPS)  # Note: upper left is 0,0 with x increasing to the right and y decreasing (negative) moving down
    #win32con.MM_HIMETRIC

    # retrieve the label's layout definition and prepare the font heights by calculation
    #layout =  calc_font_heights_for_labeldefinition(LABEL_LAYOUT_DEFINITION[label_layout], dc=dc)
    layout =  calc_font_heights_for_labeldefinition(LABEL_LAYOUT_DEFINITION[label_layout])
    print(layout)

    # process the 2D codes as defined in the label definition
    for _x, _y, _w, _h, _code_type, _border in layout["codebox"]:
        if (_code_type in ["mx","matrix","datamatrix"]):
            img = datamatrix(content, border=_border)
        elif (_code_type in PROVIDED_BARCODES):
            img = barcode(content, barcode_class=_code_type, border=_border)
        else:
            # fallback is QR-code
            img = qr_code(content, border=_border)
        draw_img_at(dc, img,  _x, _y, w=_w, h=_h)  # copy and scale the image into the device context

    # process the text lines into the textbox definition
    bounding_box_y: float = 0  # would normally need negative sign position, but our function converts it on demand
    for idx, line in enumerate(text.split("\n")):
        print("Text line {:d}: {:s}".format(idx, line))

        if (idx < len(layout["textbox"])):
            # setting for this line available
            _x, _y, _width, _height, _font_type = layout["textbox"][idx]
            if _y is not None:
                bounding_box_y = _y
        else:
            # no explicit definition for this line number: use last definition available
            _x, _y, _width, _height, _font_type = layout["textbox"][-1]
            # bounding_box_y is now being calculated no matter if there is a definition for y
        # activate the font for the device context and get the height of the font in DPI
        _, font_height = activate_font(dc, layout["fonts"][_font_type])

        # draw the current text line into the device context at defined/calculated postion
        line_height = draw_text_at(dc, line,
            _x, bounding_box_y,
            width=_width, font_size=font_height
        )
        if _height is None:
            bounding_box_y += line_height  # no user defined height -> add the last line's font height
        else:
            bounding_box_y += _height  # add the user's height definition for this line

    # DEBUG: draw a box around the label
    draw_box_at(dc, 0,0, layout["dimensions"]["width"], layout["dimensions"]["height"])

    dc.EndPage()
    dc.EndDoc()
    dc.DeleteDC()



#--------------------------------------------------------------------------------------------------


def run_scan_and_print(resource_string: str, label_layout: str, printer_name: str = "DEFAULT") -> None:
    """Runs a scanner task which triggers a print if a valid string is being read. The Termination char is set to LF only.
    It creates either a network socket scanner or a COM port scanner, depending on the resource string given.

    Args:
        resource_string (str): Resource connection string of the scanner. Valid resource strings are:
            "hostname:port", e.g. "172.25.101.43:2000" for IPv4 172.25.101.43 at port 2000.
            "comport,baud,linesettings", e.g."COM7,9600,8N1" for COM7 with 9600 baud and 8 bits No parity, 1 stop bit.
        printer_name (str): Either printer name as known by Windows OS (use print_available_printer_names() to list them)
            or "DEFAULT" as the default printer set by OS.
    """

    if "," in resource_string:
        scanner = SerialComportDevice(resource_string, termination="\r")  # COM port
    else:
        scanner = Eth2SerialDevice(resource_string, termination="\r")   # socket port
    while 1:
        print(f"Please scan label code: ", end="")
        try:
            content = scanner.request(None, timeout=2.0, encoding="utf-8")
            if content and len(content) > 0:
                print(f"got '{content}'")
                print_datamatrix_label(content, content, label_layout, printer_name=printer_name)
            else:
                print("nix!")
        except TimeoutError:
            pass  # just retry
        #except Exception as e:
        #    win32print.ClosePrinter(hPrinter)
        #    message.warning(request, f'Error! {e}')



#--------------------------------------------------------------------------------------------------

def test_create_simple_label() -> None:
    encoded = pylibdmtx.encode('RRC Zellsorter: Problem solved!'.encode('utf8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    _fp = Path('dmtx.png')
    img.save(_fp)
    print(pylibdmtx.decode(Image.open(_fp)))


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    print(["qrcode", "datamatrix", *PROVIDED_BARCODES])
    print_available_printer_names()
    #exit()

    #test_create_simple_label()  # on disk

    #printer_name = "Microsoft Print to PDF"
    printer_name = "ZDesigner ZD220-203dpi ZPL"
    #printer_name = "\\\\printhost-2k16.rrc\\C-1-58-M6630cidn"

    content = "00231872347699829949"  # test buggy QRCode
    content = "Schacht #1\nZelltyp ICR18650E28-XX\nZeile 3\nZeile 4\nZeile 5"
    label_layout = "160mm_x_40mm"
    label_layout = "76mm_x_51mm"

    #print_datamatrix_label(content, content, label_layout, printer_name=printer_name)
    # print_datamatrix_label(
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789"+
    #     "01234567890123456789012345678901234567890123456789",
    #     "Zeile 1\rZeile 2", label_layout, printer_name=printer_name)  # test buggy Datamatrix

    RESOURCE_STR = "COM38,9600,8N1"  # manual scanner
    #RESOURCE_STR = "172.21.101.31:2000"  # HOM Line Corepack
    run_scan_and_print(RESOURCE_STR, label_layout, printer_name=printer_name)  # loop blocks until CTRL-C


# END OF FILE