#
# Mockup Data for mockup_server and DSP SIMULATION interface
#
from .config import CONFIGURED_PRODUCT, SELECTED_PRINTER_LOCATION, DO_PRINT_SINGLEBOX_LABEL, DO_PRINT_HARDPACK_LABEL, ENABLE_LABEL_PRINTING
from .lookup import PRINTER_LOOKUP, BARTENDER_UNC_LOOKUP

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------

PRODUCT_CONFIGURATION_TABLE = [
     #----------------------------------------------------------------------------------
    # Please edit here to add product (Material name) is used on label!)
    # (keep in alphabetical order)
    #----------------------------------------------------------------------------------
    # Model name, Part number, Material name, SAP key,
    # then 5 elements in (brackets) to setup Teststand)
    #----------------------------------------------------------------------------------
    ("RRC2020B", "100496-18", "RRC2020", "2020B",
            ("412081_RRC2020B",     "C", "412081-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412081-01"),     # Cell-Welding (id,rev,pn)
            ("411828_RRC2020B",     "C", "411828-05"),     # PCBA-Test (id,rev,pn)
            ("412081_RRC2020B",     "C", "412081-01"),     # Corepack-Test (id,rev,pn)
            ("100496_RRC2020B",     "C", "100496-18")),    # EOL-Test (id,rev,pn)
    # ("RRC2020-DR", "110102-15"),
    ("RRC2020-GE", "110270-02", "RRC2020-GE", "2020-GE",
            ("412081_RRC2020B",     "C", "412081-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412081-01"),     # Cell-Welding (id,rev,pn)
            ("411828_RRC2020B",     "C", "411828-05"),     # PCBA-Test (id,rev,pn)
            ("412081_RRC2020B",     "C", "412081-01"),     # Corepack-Test (id,rev,pn)
            ("110270_RRC2020-GE",   "C", "110270-02")),    # EOL-Test (id,rev,pn)
    ("RRC2040B", "100498-19", "RRC2040","2040B",
           ("412083_RRC2040B",      "C", "412083-01"),     # Cell-Test (id,rev,pn)
           (None,                   "A", "412083-01"),     # Cell-Welding (id,rev,pn)
           ("411829_RRC2040B",      "D", "411829-05"),     # PCBA-Test (id,rev,pn)
           ("412083_RRC2040B",      "D", "412083-01"),     # Corepack-Test (id,rev,pn)
           ("100498_RRC2040B",      "B", "100498-19")),    # EOL-Test (id,rev,pn)
    ("RRC2040-2S", "100559S-12", "RRC2040-2", "2040-2",
           ("412084_RRC2040-2S",    "B", "412084-02"),     # Cell-Test (id,rev,pn)
           (None,                   "A", "412084-03"),     # Cell-Welding (id,rev,pn)
           ("412101_RRC2040-2S",    "D", "412101-01"),     # PCBA-Test (id,rev,pn)
           ("412084_RRC2040-2S",    "D", "412084-02"),     # Corepack-Test (id,rev,pn)
           ("100559S_RRC2040-2S",   "B", "100559S-12")),   # EOL-Test (id,rev,pn)
    # ("RRC2040-2-OL", "110059S-09", 
    ("RRC2054S", "100568S-15", "RRC2054", "2054S",
            ("412085_RRC2054S",     "B", "412085-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412085-01"),     # Cell-Welding (id,rev,pn)
            ("412100_RRC2054S",     "B", "412100-01"),     # PCBA-Test (id,rev,pn)
            ("412085_RRC2054S",     "D", "412085-01"),     # Corepack-Test (id,rev,pn)
            ("100568S_RRC2054S",    "C", "100568S-15")),   # EOL-Test (id,rev,pn)
    ("RRC2054-SO", "110062S-08", "RRC2054-SO", "2054-S0",
            ("412085_RRC2054S",     "B", "412085-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412085-01"),     # Cell-Welding (id,rev,pn)
            ("412100_RRC2054S",     "B", "412100-01"),     # PCBA-Test (id,rev,pn)
            ("412085_RRC2054S",     "D", "412085-01"),     # Corepack-Test (id,rev,pn)
            ("110064S_RRC2054-SO",  "B", "110064S-08")),   # EOL-Test (id,rev,pn)
    # ("RRC2054-OL", "110310S-02"),
    ("RRC2054-2S", "110064S-08", "RRC2054-2", "2054-2S",
            ("412080_RRC2054-2S",   "B", "412080-02"),      # Cell-Test (id,rev,pn)
            (None,                  "A", "412080-02"),      # Cell-Welding (id,rev,pn)
            ("412099_RRC2054-2S",   "C", "412099-01"),      # PCBA-Test (id,rev,pn)
            ("412080_RRC2054-2S",   "C", "412080-02"),       # Corepack-Test (id,rev,pn)
            ("110064S_RRC2054-2S",  "B", "110064S-08")),    # EOL-Test (id,rev,pn)
    # ("RRC2054-2-HM", "110325S-01"),
    # ("RRC2054-2-HM", "110325S-01"),
    ("RRC2054-2-LM", "110186S-04", "RRC2054-2-LM", "2054-2-LM",
            ("412080_RRC2054-2S",   "B", "412080-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412080-01"),     # Cell-Welding (id,rev,pn)
            ("412099_RRC2054-2S",   "B", "412099-01"),     # PCBA-Test (id,rev,pn)
            ("412080_RRC2054-2S",   "B", "412080-01"),     # Corepack-Test (id,rev,pn)
            ("110186S_RRC2054-2-LM","A", "110186S-04")),   # EOL-Test (id,rev,pn)
    # ("QSB2040", "150003B-02"),
    # ("QSB2040-2", "150004B-02"),
    ("QSB2054", "150001B-02", "QSB2054", "QSB2054B",
            ("412158_QSB2054B",     "B", "412158-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412158-02"),     # Cell-Welding (id,rev,pn)
            ("412158_QSB2054B",     "B", "412100-01"),     # PCBA-Test (id,rev,pn)
            ("412185_QSB2054B",     "B", "412185-01"),     # Corepack-Test (id,rev,pn)
            ("150001B_QSB2054B",    "C", "150001B-02")),   # EOL-Test (id,rev,pn)
    ("QSB2054-2", "150002B-02", "QSB2054-2", "Q2054-2B",
            ("412159_QSB2054-2B",   "B", "412159-01"),     # Cell-Test (id,rev,pn)
            (None,                  "A", "412159-01"),     # Cell-Welding (id,rev,pn)
            ("412159_QSB2054-2B",   "B", "412099-01"),     # PCBA-Test (id,rev,pn)
            ("412159_QSB2054-2B",   "B", "412159-01"),     # Corepack-Test (id,rev,pn)
            ("150002B_QSB2054-2",   "B", "150002B-02")),   # EOL-Test (id,rev,pn)

]

#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#
# here we generate the big part information table based on the product configuration list above
# and also add some hard coded stuff like SPINEL
#
# activated by renaming 11.04.2025 MR
PART_INFORMATION = dict([
    # our smart batteries
    *[(model,
        {
            "CELL_TEST": {
                # Cell Test PRT IDs
                "test_program_id": (f"CT-SQ_{sap_key}", f"{cell_test[0]}_Cell-Test_{cell_test[1]}"),
                "part_number": (f"CT-PN_{sap_key}", f"{cell_test[2]}"),
            },
            "CELL_WELDING": {
                # Cell Welding PRT IDs:
                "test_program_id": (f"CW-SQ_{sap_key}", f"{cell_welding[1]}"),
                "part_number": (f"CW-PN_{sap_key}", f"{cell_welding[2]}"),
            },
            "PCBA_TEST": {
                # PCBA Test PRT IDs:
                "test_program_id": (f"PT-SQ_{sap_key}", f"{pcba_test[0]}_PCBA-Test_{pcba_test[1]}"),
                "part_number": (f"PT-PN_{sap_key}", f"{pcba_test[2]}"),
            },
            "COREPACK_TEST": {
                # Core Pack Test PRT IDs:
                "test_program_id": (f"CP-SQ_{sap_key}", f"{corepack_test[0]}_Corepack-Test_{corepack_test[1]}"),
                "part_number": (f"CP-PN_{sap_key}", f"{corepack_test[2]}"),
            },
            "EOL_TEST": {
                # Hard Pack (End-Of-Line) Test PRT IDs:
                "test_program_id": (f"HP-SQ_{sap_key}", f"{eol_test[0]}_EOL-Test_{eol_test[1]}"),
                "part_number": (f"HP-PN_{sap_key}", f"{eol_test[2]}"),
            }

        }) for (model, pn, matname, sap_key, cell_test, cell_welding, pcba_test, corepack_test, eol_test) in PRODUCT_CONFIGURATION_TABLE

    ],  # wrapper to allow more elements appended manually below

    #
    # BQ40Z50 recalibration configurations
    #
    ("RRC2020B_RECALIBRATION", {
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "BQ40Z50_Recalibration_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "100496-18"),
        }
    }),
    ("RRC2020-DR_RECALIBRATION", {
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "BQ40Z50_Recalibration_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "110102-14"),
        }
    }),

    #
    # SOFTPACK products
    #
    ("SPINEL", {
        "CELL_TEST": {
            # Cell Test (Teststand):
            "test_program_id": ("CW-SQ_SPINEL", "110282S_SPINEL_Cell-Test_A"),
            "part_number": ("CW-PN_SPINEL", "110282S-03"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_SPINEL", "A"),
            "part_number": ("CW-PN_SPINEL", "110282S-03"),
        },
        "LEANPACK_TEST": {
            # EOL Test with Corepack hardware (Teststand)
            "test_program_id": ("CP-SQ_SPINEL", "110282B_SPINEL_Leanpack-Test_A"),
            "part_number": ("CP-PN_SPINEL", "110282B-03"),
        }
    }),

    # ... add more if you like ...

])

#--------------------------------------------------------------------------------------------------

# removed by renaming 11.04.2025 MR
PART_INFORMATION_MANUAL = {
    #
    # BQ40Z50_RECALIBRATION
    #
    "RRC2020B_RECALIBRATION": {
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "BQ40Z50_Recalibration_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "100496-18"),
        }
    },
    "RRC2020-DR_RECALIBRATION": {
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "BQ40Z50_Recalibration_EOL-Test_A"),
            "part_number": ("HP-PN_2020B", "110102-14"),
        }
    },
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
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_C"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "100496_RRC2020B_EOL-Test_C"),
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
            "test_program_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_D"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040B", "412083_RRC2040B_Corepack-Test_D"),
            "part_number": ("CP-PN_2040B", "412083-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040B", "100498_RRC2040B_EOL-Test_B"),
            "part_number": ("HP-PN_2040B", "100498-19"),
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
            "test_program_id": ("CP-SQ_2054S", "412085_RRC2054S_Corepack-Test_C"),
            "part_number": ("CP-PN_2054S", "412085-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054S", "100568S_RRC2054S_EOL-Test_C"),
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
            "test_program_id": ("PT-SQ_2054S", "412100_RRC2054S_PCBA-Test_C"),
            "part_number": ("PT-PN_2054S", "412100-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2054S", "412085_RRC2054S_Corepack-Test_C"),
            "part_number": ("CP-PN_2054S", "412085-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054S", "110062S_RRC2054-SO_EOL-Test_B"),
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
            "part_number": ("CT-PN_2040-2S", "412084-02"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040-2S", "A"),
            "part_number": ("CW-PN_2040-2S", "412084-02"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040-2S", "412101_RRC2040-2S_PCBA-Test_D"),
            "part_number": ("PT-PN_2040-2S", "412101-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040-2S", "412084_RRC2040-2S_Corepack-Test_D"),
            "part_number": ("CP-PN_2040-2S", "412084-02"),
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
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_C"),
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
            "part_number": ("CW-PN_SPINEL", "110282S-03"),
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
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_C"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "110102_RRC2020-DR_EOL-Test_C"),
            "part_number": ("HP-PN_2020B", "110102-15"),  # using the product number PN
        }
    },
    #
    # RRC2020-GE
    #
    "RRC2020-GE": {
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
            "test_program_id": ("CP-SQ_2020B", "412081_RRC2020B_Corepack-Test_C"),
            "part_number": ("CP-PN_2020B", "412081-01"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "110270_RRC2020-GE_EOL-Test_B"),
            "part_number": ("HP-PN_2020B", "110270-02"),  # using the product number PN
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
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_C"),
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
            "test_program_id": ("CP-SQ_2054-2S", "412080_RRC2054-2S_Corepack-Test_C"),
            "part_number": ("CP-PN_2054-2S", "412080-02"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2054-2-LM", "110186S_RRC2054-2-LM_EOL-Test_A"),
            "part_number": ("HP-PN_2054-2-LM", "110186S-04"),
        }
    },
    #
    # QSB2040B
    #
    "QSB2040B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2040B", "412169_QSB2040B_Cell-Test_A"),
            "part_number": ("CT-PN_2040B", "412083-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040B", "A"),
            "part_number": ("CW-PN_2040B", "412083-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040B", "412169_QSB2040B_PCBA-Test_B"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040B", "412169_QSB2040B_Corepack-Test_B"),
            "part_number": ("CP-PN_2040B", "412083-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040B", "150003B_QSB2040_EOL-Test_B"),
            "part_number": ("HP-PN_2040B", "150003B-02"),
        }
    },
    #
    # QSB2054B
    #
    "QSB2054B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2054B", "412158_QSB2054B_Cell-Test_B"),
            "part_number": ("CT-PN_Q2054B", "412185-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2054B", "A"),
            "part_number": ("CW-PN_Q2054B", "412158-02"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2054B", "412158_QSB2054B_PCBA-Test_B"),
            "part_number": ("PT-PN_Q2054B", "412100-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2054B", "412158_QSB2054B_Corepack-Test_B"),
            "part_number": ("CP-PN_Q2054B", "412185-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2054B", "150001B_QSB2054_EOL-Test_C"),
            "part_number": ("HP-PN_Q2054B", "150001B-02"),
        }
    },
    #
    # QSB2040-2B
    #
    "QSB2040-2B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2040-2B", "412160_QSB2040-2B_Cell-Test_B"),
            "part_number": ("CT-PN_Q2040-2B", "412160-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2040-2B", "A"),
            "part_number": ("CW-PN_Q2040-2B", "412160-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2040-2B", "412160_QSB2040-2B_PCBA-Test_B"),
            "part_number": ("PT-PN_Q2040-2B", "412101-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2040-2B", "412160_QSB2040-2B_Corepack-Test_B"),
            "part_number": ("CP-PN_Q2040-2B", "412160-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2040-2B", "150004B_QSB2040-2_EOL-Test_B"),
            "part_number": ("HP-PN_Q2040-2B", "150004B-02"),
        }
    },
    #
    # QSB2054-2B
    #
    "QSB2054-2B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_Q2054-2B", "412159_QSB2054-2B_Cell-Test_B"),
            "part_number": ("CT-PN_Q2054-2B", "412159-01"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_Q2054-2B", "A"),
            "part_number": ("CW-PN_Q2054-2B", "412159-01"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_Q2054-2B", "412159_QSB2054-2B_PCBA-Test_B"),
            "part_number": ("PT-PN_Q2054-2B", "412099-01"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_Q2054-2B", "412159_QSB2054-2B_Corepack-Test_B"),
            "part_number": ("CP-PN_Q2054-2B", "412159-01"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_Q2054-2B", "150002B_QSB2054-2_EOL-Test_B"),
            "part_number": ("HP-PN_Q2054-2B", "150002B-02"),
        }
    },
}


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#
# To enable product label printing while bypassing the MES, we need to create a lookup table
# containing the label and printer configurations identified by part number.
#
# Label print is triggered by the output of a file into the configuraed UNC path with scheme:
#
# filename template: 99ZZ 01 9Z 00 0089 0050568936F31EEEB8D5BAD85F3A82C0 20240315092436.dat
#                    {product_serial  } { GUID                         } { datetime_str}.dat
#

#
# This is the datamatrix code for the label which printing service expects in a text file
#
LABEL_CODE_DATA = r'[)>061P{01}30P{02}10D{03}S{04}'

#
# generate the lookup dictionary for each part number listed in PRODUCT_CONFIGURATION_TABLE
#
LABEL_PRINTING_LOOKUP = dict([
    *[(pn,
        {
            "enabled": bool(ENABLE_LABEL_PRINTING),  # set to True to trigger a label print file (.dat) written into unc path
            "unc_path": BARTENDER_UNC_LOOKUP[SELECTED_PRINTER_LOCATION],
            "file_content": [  # list of possible label file row entries - at least one
                {
                    "PRINTERNAME": PRINTER_LOOKUP[SELECTED_PRINTER_LOCATION]["HARDPACK"],
                    "LABELFILE": "R01_412117_B.BTW", # hardpack label
                    "MATNR": pn,  # will also be replaced by the KEY above on printfile generation
                    "MATNAME": matname,
                    "DATECODE": None,
                    "SERIAL": None,  # {01}=MODEL CODE(4) {02}=PREASS-REV(2) {03}=MFC(2) {04}=SN-OVERFLOW(2) {05}=S/N(4)
                    "QUANTITY": int(1),
                    "CODEDATA": LABEL_CODE_DATA,
                    "CODEDATABIG": None,  # stays empty
                    "MANUFACTURE_DATE": None, 	# will be set to the current date as we do not have access to DB here
                    "WEEKDAY": None,   # day of week of MANUFACTURE_DATE
                } if DO_PRINT_HARDPACK_LABEL else None,
                {
                    "PRINTERNAME": PRINTER_LOOKUP[SELECTED_PRINTER_LOCATION]["SINGLEBOX"],
                    "LABELFILE": "R01_412077_B.BTW",  # single outer box label
                    "MATNR": pn,  # will also be replaced by the KEY above on printfile generation
                    "MATNAME": matname,
                    "DATECODE": None,
                    "SERIAL": None,  # {01}=MODEL CODE(4) {02}=PREASS-REV(2) {03}=MFC(2) {04}=SN-OVERFLOW(2) {05}=S/N(4)
                    "QUANTITY": int(1),
                    "CODEDATA": LABEL_CODE_DATA,
                    "CODEDATABIG": None,
                    "MANUFACTURE_DATE": None,
                    "WEEKDAY": None,
                } if DO_PRINT_SINGLEBOX_LABEL else None,
                # ...
            ]
        }) for (model, pn, matname, _1, _2, _3, _4, _5, _6,) in PRODUCT_CONFIGURATION_TABLE  # Note: the _x, means not needed

    ],  # wrapper to allow more elements appended manually below

    # add others with different configuration as you need
    # in the form ( "part_number", dict ),
    # ...

])

# END OF FILE