"""
Configuration module for mockup server. Please edit here, not in mockup_server.py anymore.
"""

#--------------------------------------------------------------------------------------------------
#
# Mockup server port is 8000 by default. It is selectable by the .CMD batch file so you
# can easily configure more than one server to run in parallel on this PC by adding
# --port parameter on the call:
#
# Example:
#   uvicorn mockup.server:app --host 0.0.0.0 --port 8011
#   uvicorn mockup.server:app --host 0.0.0.0 --port 8022
#   uvicorn mockup.server:app --host 0.0.0.0 --port 8033
#
#   Please not that there is no --reload parameter so you can change the CONFIGURED_PRODUCT
#   before calling each mockup -> on TSDEV we can run 3 mockups for the lines that way!
#
#
# Besides that  you need also to set this port in the station_config.yaml of a
# workstation under test or used for rework on a line.
#
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#
# Edit this to set the product to test for mockup server:
#
#CONFIGURED_PRODUCT = "RRC2020B_RECALIBRATION"
#CONFIGURED_PRODUCT = "RRC2020-DR_RECALIBRATION"
#CONFIGURED_PRODUCT = "RRC2020B"
CONFIGURED_PRODUCT = "RRC2020-DR"
#CONFIGURED_PRODUCT = "RRC2020-GE"
#CONFIGURED_PRODUCT = "RRC2040B"
#CONFIGURED_PRODUCT = "RRC2054S"
#CONFIGURED_PRODUCT = "RRC2054-SO"
#CONFIGURED_PRODUCT = "SPINEL"
#CONFIGURED_PRODUCT = "RRC2040-2S"
#CONFIGURED_PRODUCT = "RRC2054-2S"
#CONFIGURED_PRODUCT = "RRC2054-2-HM"
#CONFIGURED_PRODUCT = "RRC2054-2-LM"
#CONFIGURED_PRODUCT = "QSB2040B"
#CONFIGURED_PRODUCT = "QSB2054B"
#CONFIGURED_PRODUCT = "QSB2040-2B"
#CONFIGURED_PRODUCT = "QSB2054-2B"
#
#
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
#
# This is to configure the printer for mockup_information if used on rework more easily
#
#
SELECTED_PRINTER_LOCATION = "VN_GENERIC"  # "VN_GENERIC", "DE_LINE_1", ..., etc.
#
# set to 1 to allow mockup server to trigger label print for all products, set 0 to disable
ENABLE_LABEL_PRINTING = 1
#
# set to 1 to allow entry in label .DAT file otherwise set to 0
DO_PRINT_HARDPACK_LABEL = 1
DO_PRINT_SINGLEBOX_LABEL = 1
#
#
#--------------------------------------------------------------------------------------------------
#
#
# END OF FILE