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
            "test_program_id": ("PT-SQ_2040B", "411829_RRC2040B_PCBA-Test_B"),
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
            "test_program_id": ("PT-SQ_2040-2S", "412101_RRC2040-2S_PCBA-Test_B"),
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
            "test_program_id": ("PT-SQ_2054-2S", "412099_RRC2054-2S_PCBA-Test_B"),
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
            "test_program_id": ("PT-SQ_2054-2S", "412099_RRC2054-2S_PCBA-Test_B"),
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
}
 
# END OF FILE
