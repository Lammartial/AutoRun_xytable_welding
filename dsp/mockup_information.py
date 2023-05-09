#
# Mockup Data for mockup_server and DSP SIMULATION interface
#

MOCK_PARTNUMBER = {
    "RRC2020B": {
        "product":        "100496-17",
        "pre_assembly":   "412031-16",
        "pcba":           "411828-05",
    },
    "RRC2040B": {
        "product":        "100498-17",
        "pre_assembly":   "412036-16",
        "pcba":           "411829-05",
    }
}


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
            "test_program_id": ("CT-SQ_2020B", "412031_RRC2020B_Cell-Test_B"),
            "part_number": ("CT-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2020B", "A"),
            "part_number": ("CW-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2020B", "411828_RRC2020B_PCBA-Test_B"),
            "part_number": ("PT-PN_2020B", "411828-05"),  # using the pcba part number PN
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2020B", "412031_RRC2020B_Corepack-Test_B"),
            "part_number": ("CP-PN_2020B", "412031-16"),  # using the pre-assembly PN
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2020B", "100496_RRC2020B_EOL-Test_B"),
            "part_number": ("HP-PN_2020B", "100496-17"),  # using the product number PN
        }
    },
    #
    # RRC2040B
    #
    "RRC2040B": {
        "CELL_TEST": {
            # Cell Test PRT IDs
            "test_program_id": ("CT-SQ_2040B", "412036_RRC2040B_Cell-Test_A"),
            "part_number": ("CT-PN_2040B", "412036-16"),
        },
        "CELL_WELDING": {
            # Cell Welding PRT IDs:
            "test_program_id": ("CW-SQ_2040B", "A"),
            "part_number": ("CW-PN_2040B", "412036-16"),
        },
        "PCBA_TEST": {
            # PCBA Test PRT IDs:
            "test_program_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_A"),
            "part_number": ("PT-PN_2040B", "411829-05"),
        },
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_2040B", "412036_RRC2040B_Corepack-Test_A"),
            "part_number": ("CP-PN_2040B", "412036-16"),
        },
        "EOL_TEST": {
            # Hard Pack (End-Of-Line) Test PRT IDs:
            "test_program_id": ("HP-SQ_2040B", "100498_RRC2040B_EOL-Test_A"),
            "part_number": ("HP-PN_2040B", "100498-17"),
        }
    },
    #
    # RRC Spinel
    #
    "SPINEL": {
        "COREPACK_TEST": {
            # Core Pack Test PRT IDs:
            "test_program_id": ("CP-SQ_SPINEL", "110282_SPINEL_Corepack-Test_A"),
            "part_number": ("CP-PN_SPINEL", "110282-02"),
        }
    }
}


# END OF FILE