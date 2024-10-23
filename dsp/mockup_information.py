#
# Mockup Data for mockup_server and DSP SIMULATION interface
#


#
# Parameters in the form key:value -> key:payload
#  (z.B. “CT-SQ_2020B” mit dann der maximal 40-stelligen Payload in der PRT Description)
#
PART_INFORMATION = {
    #
    # RRC2020B
    #
    "RRC2020B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2020B", "412081_RRC2020B_Cell-Test_C"),
            "part_number": ("CT-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2020B", "A"),
            "part_number": ("CW-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2020B", "411828_RRC2020B_PCBA-Test_C"),
            "part_number": ("PT-PN_2020B", "411828-05"),  # using the pcba part number PN
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_B"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "100496_RRC2020B_EOL-Test_B"),
            "part_number": ("HP-PN_2020B", "100496-18"),  # using the product number PN
        }
    },
    #
    # RRC2040B
    #
    "RRC2040B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2040B", "412083_RRC2040B_Cell-Test_C"),
            "part_number": ("CT-PN_2040B", "412083-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040B", "A"),
            "part_number": ("CW-PN_2040B", "412083-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_C"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040B", "412083_RRC2040B_Corepack-Test_C"),
            "part_number": ("CP-PN_2040B", "412083-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040B", "100498_RRC2040B_EOL-Test_B"),
            "part_number": ("HP-PN_2040B", "100498-18"),
        }
    },
    #
    # RRC2054S
    #
    "RRC2054S": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2054S", "412085_RRC2054S_Cell-Test_B"),
            "part_number": ("CT-PN_2054S", "412085-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2054S", "A"),
            "part_number": ("CW-PN_2054S", "412085-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2054S", "412100_RRC2054S_PCBA-Test_B"),
            "part_number": ("PT-PN_2054S", "412100-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054S", "412085_RRC2054S_Corepack-Test_B"),
            "part_number": ("CP-PN_2054S", "412085-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054S", "100568S_RRC2054S_EOL-Test_B"),
            "part_number": ("HP-PN_2054S", "100568S-15"),
        }
    },
    #
    # RRC2054-SO
    #
    "RRC2054-SO": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2054S", "412085_RRC2054S_Cell-Test_B"),
            "part_number": ("CT-PN_2054S", "412085-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2054S", "A"),
            "part_number": ("CW-PN_2054S", "412085-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2054S", "412100_RRC2054S_PCBA-Test_B"),
            "part_number": ("PT-PN_2054S", "412100-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054S", "412085_RRC2054S_Corepack-Test_B"),
            "part_number": ("CP-PN_2054S", "412085-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054S", "110062S_RRC2054-SO_EOL-Test_A"),
            "part_number": ("HP-PN_2054S", "110062S-08"),
        }
    },
    #
    # RRC2040-2S
    #
    "RRC2040-2S": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2040-2S", "412084_RRC2040-2S_Cell-Test_B"),
            "part_number": ("CT-PN_2040-2S", "412084-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040-2S", "A"),
            "part_number": ("CW-PN_2040-2S", "412084-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040-2S", "412101_RRC2040-2S_PCBA-Test_C"),
            "part_number": ("PT-PN_2040-2S", "412101-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040-2S", "412084_RRC2040-2S_Corepack-Test_B"),
            "part_number": ("CP-PN_2040-2S", "412084-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040-2S", "100559S_RRC2040-2S_EOL-Test_B"),
            "part_number": ("HP-PN_2040-2S", "100559S-11"),
        }
    },
    #
    # RRC2054-2S
    #
    "RRC2054-2S": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2054-2S", "412080_RRC2054-2S_Cell-Test_B"),
            "part_number": ("CT-PN_2054-2S", "412080-02"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2054-2S", "A"),
            "part_number": ("CW-PN_2054-2S", "412080-02"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2054-2S", "412099_RRC2054-2S_PCBA-Test_C"),
            "part_number": ("PT-PN_2054-2S", "412099-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_B"),
            "part_number": ("CP-PN_2054-2S", "412080-02"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054-2S", "110064S_RRC2054-2S_EOL-Test_B"),
            "part_number": ("HP-PN_2054-2S", "110064S-08"),
        }
    },
    #
    # RRC Spinel
    #
    "SPINEL": {
        "CELL_TEST": {
            # Cell Test (Teststand):
            "test_program_id": ("CW-SQ_SPINEL", "110282S_SPINEL_Cell-Test_A"),
            "part_number": ("CW-PN_SPINEL", "110282S-03"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_SPINEL", "A"),
            "part_number": ("CW-PN_SPINEL", "110282B-03"),
        },
        #"LEANPACK_TEST": {
        #     # EOL Test with Corepack hardware (Teststand)
        #     "test_program_id": ("CP-SQ_SPINEL", "110282S_SPINEL_Leanpack-Test_C"),
        #     "part_number": ("CP-PN_SPINEL", "110282S-03"),
        #},
        "LEANPACK_TEST": {
            # EOL Test with Corepack hardware (Teststand)
            "test_program_id": ("CP-SQ_SPINEL", "110282B_SPINEL_Leanpack-Test_A"),
            "part_number": ("CP-PN_SPINEL", "110282B-03"),
        }
    },
    #
    # RRC2020-DR
    #
    "RRC2020-DR": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2020B", "412081_RRC2020B_Cell-Test_C"),
            "part_number": ("CT-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2020B", "A"),
            "part_number": ("CW-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2020B", "411828_RRC2020B_PCBA-Test_C"),
            "part_number": ("PT-PN_2020B", "411828-05"),  # using the pcba part number PN
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_B"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "110102_RRC2020-DR_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "110102-14"),  # using the product number PN
        }
    },
    #
    # RRC2054-2-HM
    #
    "RRC2054-2-HM": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2054-2S", "412080_RRC2054-2S_Cell-Test_B"),
            "part_number": ("CT-PN_2054-2S", "412080-02"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2054-2S", "A"),
            "part_number": ("CW-PN_2054-2S", "412080-02"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2054-2S", "412099_RRC2054-2S_PCBA-Test_C"),
            "part_number": ("PT-PN_2054-2S", "412099-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_B"),
            "part_number": ("CP-PN_2054-2S", "412080-02"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054-2-HM", "110325S_RRC2054-2-HM_EOL-Test_A"),
            "part_number": ("HP-PN_2054-2-HM", "110325S-01"),
        }
    },
    #
    # RRC2054-2-LM
    #
    "RRC2054-2-LM": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2054-2S", "412080_RRC2054-2S_Cell-Test_B"),
            "part_number": ("CT-PN_2054-2S", "412080-02"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2054-2S", "A"),
            "part_number": ("CW-PN_2054-2S", "412080-02"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2054-2S", "412099_RRC2054-2S_PCBA-Test_C"),
            "part_number": ("PT-PN_2054-2S", "412099-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_B"),
            "part_number": ("CP-PN_2054-2S", "412080-02"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054-2-LM", "110186S_RRC2054-2-LM_EOL-Test_A"),
            "part_number": ("HP-PN_2054-2-LM", "110186S-04"),
        }
    },
    #
    # RRC2020B_SDNWAKEUP
    #
    "RRC2020B_SDNWAKEUP": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2020B", "412081_RRC2020B_Cell-Test_C"),
            "part_number": ("CT-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2020B", "A"),
            "part_number": ("CW-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2020B", "411828_RRC2020B_PCBA-Test_B"),
            "part_number": ("PT-PN_2020B", "411828-05"),  # using the pcba part number PN
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_B"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "100496_RRC2020_Re-Program_from_DR_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "100496-18"),  # using the product number PN
        }
    },
    #
    # QSB2040B
    #
    "QSB2040B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2040B", "412083_RRC2040B_Cell-Test_C"),
            "part_number": ("CT-PN_2040B", "412083-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040B", "A"),
            "part_number": ("CW-PN_2040B", "412083-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_C"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040B", "412083_RRC2040B_Corepack-Test_C"),
            "part_number": ("CP-PN_2040B", "412083-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040B", "100498_RRC2040B_EOL-Test_B"),
            "part_number": ("HP-PN_2040B", "100498-18"),
        }
    },
    #
    # QSB2054B
    #
    "QSB2054B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2054B", "412185_QSB2054B_Cell-Test_A"),
            "part_number": ("CT-PN_Q2054B", "412185-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2054B", "A"),
            "part_number": ("CW-PN_Q2054B", "412185-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2054B", "412100_QSB2054B_PCBA-Test_A"),
            "part_number": ("PT-PN_Q2054B", "412100-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2054B", "412185_QSB2054B_Corepack-Test_A"),
            "part_number": ("CP-PN_Q2054B", "412185-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2054B", "150001B_QSB2054_EOL-Test_A"),
            "part_number": ("HP-PN_Q2054B", "150001B-01"),
        }
    },
    #
    # QSB2040-2B
    #
    "QSB2040-2B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2040-2B", "412160_QSB2040-2B_Cell-Test_A"),
            "part_number": ("CT-PN_Q2040-2B", "412160-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2040-2B", "A"),
            "part_number": ("CW-PN_Q2040-2B", "412160-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2040-2B", "412101_QSB2040-2B_PCBA-Test_A"),
            "part_number": ("PT-PN_Q2040-2B", "412101-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2040-2B", "412160_QSB2040-2B_Corepack-Test_A"),
            "part_number": ("CP-PN_Q2040-2B", "412160-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2040-2B", "150004B_QSB2040-2_EOL-Test_A"),
            "part_number": ("HP-PN_Q2040-2B", "150004B-01"),
        }
    },
    #
    # QSB2054-2B
    #
    "QSB2054-2B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2054-2B", "412159_QSB2054-2B_Cell-Test_A"),
            "part_number": ("CT-PN_Q2054-2B", "412159-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2054-2B", "A"),
            "part_number": ("CW-PN_Q2054-2B", "412159-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2054-2B", "412099_QSB2054-2B_PCBA-Test_A"),
            "part_number": ("PT-PN_Q2054-2B", "412099-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2054-2B", "412159_QSB2054-2B_Corepack-Test_A"),
            "part_number": ("CP-PN_Q2054-2B", "412159-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2054-2B", "150002B_QSB2054-2_EOL-Test_A"),
            "part_number": ("HP-PN_Q2054-2B", "150002B-01"),
        }
    },
}


#--------------------------------------------------------------------------------------------------
#
#  To enable product label printing while bypassing the MES
#
#--------------------------------------------------------------------------------------------------
#
# NOTE: all column names come from MES -> Bartender interface
#
LABEL_PRINTING = {

    #
    # RRC2054-2S
    #
    "110064S-08": {
        "enabled": True,  # set to True to trigger a label print file (.dat) written into unc path
        "mdate_lookup_path": "dummy.csv",  # lookup .csv/.tsv file for manufacturer dates
        #"unc_path": "//sv-vn-bartender.rrcpowersolutions.com/bartender-input/batterylabel/",  # slashes / will be transformed by Path() into backslashes on use
        "unc_path": "C:/bartender-out/",  # DEBUG
        "file_content": [  # list of possible label file row entries - at least one
            {
                "PRINTERNAME": "PRN-2000-1_A11-HARDPACK",  # hardcoded
                "LABELFILE": "HPLABEL.BTW", # hardcoded
                "MATNR": None,       # will be replaced by the KEY above
                "MATNAME": "RRC2054-2S",
                "DATECODE": None,
                "SERIAL": "542S 02 R2 {01} {02}",  # {01}=00 {02}=S/N
                "QUANTITY": int(1),
                "CODEDATA": r'[)>061P{01}30P{02}10D{03}S{04}',
                "CODEDATABIG": None,  # stays empty
                "MANUFACTURE_DATE": None, 	# will be set to the current date as we do not have access to DB here
                "WEEKDAY": None,   # day of week of MANUFACTURE_DATE
            },
            {
                "PRINTERNAME": "PRN-2000-1_A12-SINGLEBOX",
                "LABELFILE": "SBLABEL.BTW",
                "MATNR": None,
                "MATNAME": "RRC2054-2S",
                "DATECODE": None,
                "SERIAL": "542S 02 R2 {01} {02}",  # {01}=00 {02}=S/N
                "QUANTITY": int(1),
                "CODEDATA": r'[)>061P{01}30P{02}10D{03}S{04}',
                "CODEDATABIG": None,
                "MANUFACTURE_DATE": None,
                "WEEKDAY": None,
            },
            # ...
        ]
    },

    #
    # RRC2040-2S
    #
    "100559S-11": {
        "enabled": True,  # set to True to trigger a label print file (.dat) written into unc path
        "mdate_lookup_path": "dummy.csv",  # lookup .csv/.tsv file for manufacturer dates
        #"unc_path": "//sv-vn-bartender.rrcpowersolutions.com/bartender-input/batterylabel/",  # slashes / will be transformed by Path() into backslashes on use
        "unc_path": "C:/bartender-out/",  # DEBUG
        "file_content": [  # list of possible label file row entries - at least one
            {
                "PRINTERNAME": "PRN-2000-1_A11-A11-HARDPACK",  # hardcoded
                "LABELFILE": "HPLABEL.BTW", # hardcoded
                "MATNR": None,       # will be replaced by the KEY above
                "MATNAME": "RRC2040-2S",
                "DATECODE": None,
                "SERIAL": "99ZZ 01 9Z {01} {02}",  # {01}=00 {02}=S/N
                "QUANTITY": int(1),
                "CODEDATA": r'[)>061P{01}30P{02}10D{03}S{04}',
                "CODEDATABIG": None,  # stays empty
                "MANUFACTURE_DATE": None, 	# will be set to the current date as we do not have access to DB here
                "WEEKDAY": None,   # day of week of MANUFACTURE_DATE
            },
            {
                "PRINTERNAME": "PRN-2000-1_A12-SINGLEBOX",
                "LABELFILE": "SINGLEBOXLABEL.BTW",
                "MATNR": None,
                "MATNAME": "RRC2040-2S",
                "DATECODE": None,
                "SERIAL": "99ZZ 01 9Z {01} {02}",
                "QUANTITY": int(1),
                "CODEDATA": r'[)>061P{01}30P{02}10D{03}S{04}',
                "CODEDATABIG": None,
                "MANUFACTURE_DATE": None,
                "WEEKDAY": None,
            },
            # ...
        ]
    },
    # ...

    # filename template: 99ZZ 01 9Z 00 0089 0050568936F31EEEB8D5BAD85F3A82C0 20240315092436.dat
    #                    {product_serial  } { GUID                         } { datetime_str}.dat
    #

}

# END OF FILE
