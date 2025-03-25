#
# This is to configure the printer for mockup_information if used on rework more easily
#
#
#
#--------------------------------------------------------------------------------------------------
# Edit this:

SELECTED_PRINTER_LOCATION = "DE_LINE_1"  # "VN_GENERIC", "VN_LINE_1", ..., etc.

DO_PRINT_SINGLEBOX_LABEL = 1
DO_PRINT_HARDPACK_LABEL = 1

#
# Example of use in douple step lookup for mockup_information:
#   PRINTER_LOOKUP[SELECTED_PRINTER_LOCATION]["HARDPACK"]
#   PRINTER_LOOKUP[SELECTED_PRINTER_LOCATION]["SINGLEBOX"]
#   LABELFILE_LOOKUP[SELECTED_PRINTER_LOCATION]["HARDPACK"]
#   BARTENDER_UNC_LOOKUP[SELECTED_PRINTER_LOCATION]
#
#
#--------------------------------------------------------------------------------------------------
# DON'T EDIT HERE
#--------------------------------------------------------------------------------------------------
#
# This is the datamatrix code for the label which printing service expects in a text file
#
LABEL_CODE_DATA = r'[)>061P{01}30P{02}10D{03}S{04}'


PLANT_CODE_LOOKUP = {
    "DE_LINE_1": 1000,
    "VN_GENERIC": 2000,
}


PRINTER_LOOKUP = {
    "VN_GENERIC": {
        "HARDPACK":  "PRN-{01}-{02}_A11-HARDPACK",   # {01}=plant {02}=line
        "SINGLEBOX": "PRN-{01}-{02}_A12-SINGLEBOX",  # {01}=plant {02}=line
    },
    "DE_LINE_1": {
        "HARDPACK":  "A11-HARDPACK_4xy",  # hard coded configuration
        "SINGLEBOX": "A12-SINGLEBOX_4xy",  # hard coded configuration
    }
}


LABELFILE_LOOKUP = {
    "VN_GENERIC": {
        "HARDPACK": "R01_412117_B.BTW",    # product label
        "SINGLEBOX": "R01_412077_B.BTW",   # single outer box label
    },
    "DE_LINE_1": {
        "HARDPACK":  "R01_412117_B.BTW",   # product label
        "SINGLEBOX": "R01_412077_B.BTW",   # single outer box label
    }
}

#
# These are the paths to the Bartender label server's monitored
# directory which triggers the label printing.
# These are differnt between VN and DE environments.
#
BARTENDER_UNC_LOOKUP = {
    # slashes / will be transformed by Path() into backslashes on use
    #"VN_GENERIC": "//sv-vn-bartender.rrcpowersolutions.com/batterylabel/",
    "VN_GENERIC": "C:/bartender-output",  # DEBUG ONLY!
    #"DE_LINE_1": "//sv-de-bartender/input-bla-batterylabel/",
    "DE_LINE_1": "C:/bartender-output",  # DEBUG ONLY!
}


# END OF FILE