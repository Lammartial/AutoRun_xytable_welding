"""
This is a lookup module to configure the printer for mockup_information if used on rework more easily.
"""

#--------------------------------------------------------------------------------------------------
# DON'T EDIT HERE
#--------------------------------------------------------------------------------------------------


PLANT_CODE_LOOKUP = {
    "DE_LINE_1": 1000,
    "VN_GENERIC": 2000,
}


PRINTER_LOOKUP = {
    "DE_LINE_1": {
        "HARDPACK":  "MF_ZEBRA_ZT411_03",  # hard coded configuration
        "SINGLEBOX": "MF_ZEBRA_ZT411_03",  # hard coded configuration
    },
    "VN_GENERIC": {
        "HARDPACK":  "PRN-{01}-{02}_A11-HARDPACK",   # {01}=plant {02}=line
        "SINGLEBOX": "PRN-{01}-{02}_A12-SINGLEBOX",  # {01}=plant {02}=line
    },
}


LABELFILE_LOOKUP = {
    "DE_LINE_1": {
        "HARDPACK":  "R01_412117_B.BTW",   # product label
        "SINGLEBOX": "R01_412077_B.BTW",   # single outer box label
    },
    "VN_GENERIC": {
        "HARDPACK":  "R01_412117_B.BTW",   # product label
        "SINGLEBOX": "R01_412077_B.BTW",   # single outer box label
    },
}

#
# These are the paths to the Bartender label server's monitored
# directory which triggers the label printing.
# These are differnt between VN and DE environments.
#
BARTENDER_UNC_LOOKUP = {
    #
    # slashes / will be transformed by Path() into backslashes on use
    #
    "DE_LINE_1": "//sv-de-bartender.rrc/bartender-input/batterylabel/",
    #"DE_LINE_1": "C:/bartender-output",  # DEBUG ONLY!

    "VN_GENERIC": "//sv-vn-bartender.rrcpowersolutions.com/batterylabel/",
    #"VN_GENERIC": "C:/bartender-output",  # DEBUG ONLY!

}


# END OF FILE