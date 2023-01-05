"""
Minimal module to read data by modbus from a device (w.g. welder) and store it into database.

Sketch - not functional yet !

"""

import uuid
import pandas as pd
from dbcon import srcEngine, SSession
# this import is only needed if connection has to be changed
from dbcon import load_config_yaml_file, createInternalSession
from rrc.modbus.welder_aws3 import factory_get_device

#
# Test porstgres connections
#
print("\nTest POSTGRES connection:\n","-"*80,"\n")

result = None
with srcEngine.connect() as connection:
    welder = factory_get_device()
    s = welder.read_status()
    df = pd.DataFrame(s)
    df["uid"] = uuid.uuid1()
    df.to_sql("ems_table", con=connection, if_exists="append")

# END OF FILE