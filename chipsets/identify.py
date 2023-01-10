"""Convenience module to support chipset identification.
"""
# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904

from .bq20z65 import BQ20Z65R1, BQ20Z65R2
from .bq40z50 import BQ40Z50R1, BQ40Z50R2

# This list is a reference of the order in which the presence of a chipset should
# be checked for to avoid false positive detections.
#
# NOTE: if more chipsets are added, this list must be extended accordingly
#
CHIPSETS_AVAILABLE = [
    BQ20Z65R1,
    BQ20Z65R2,
    BQ40Z50R1,
    BQ40Z50R2,
]

def get_list_of_chipset_names():
    global CHIPSETS_AVAILABLE

    listofchipsets = [c.__name__.lower() for c in CHIPSETS_AVAILABLE]
    return listofchipsets

def autodetect_chipset(smbus):
    global CHIPSETS_AVAILABLE

    listofchipsets = [c(smbus) for c in CHIPSETS_AVAILABLE] # make a list of instances
    for cs in listofchipsets:
        if cs.autodetect():
            return cs
    return None


# END OF FILE
