from typing import Tuple
import json
import yaml
from pathlib import Path
# import SQL managing modules
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

# need to be known
CONFIG = {}

#-------------------------------------------------------------------------------------------------
# import static configuration from YAML file
def load_config_yaml_file(fname: Path | str):
    """Loads the given filename as YAML while appending the .yaml suffix.

    Args:
        fname (str): filename-string or Path

    Returns:
        dict: configuration dict from yaml
    """
    if isinstance(fname, str):
        _filepath = Path(__file__).parent.absolute() / f"{fname}.yaml"
    else:
        # full filepath -> don't modify
        _filepath = Path(fname)
    with open(_filepath, "r") as stream:
        try:
            CONFIG = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1) # terminate software
    return CONFIG

#-------------------------------------------------------------------------------------------------
def createInternalSession(config, echo=False):
    """Setup a persistent connection to the selected database.
    There is no need to close the connection.

    See: https://docs.sqlalchemy.org/en/14/core/engines.html

    Args:
        config (dict): Possibility to change the connection on demand. Defaults to CONFIG.
        echo (bool, optional): Verbosity level of the SQL driver: True delivers a lot of SQL transfer prints. Defaults to False.

    Returns:
        Tuple of engine and session: These hold and manage the connection for queries.
    """
    # somehow the new Python 310 installation with pymysql does not accept "encoding" parameter for mysql anymore"
    # instead we have to use this WEB API like approach with "charset" appended.
    engine = sa.create_engine("{0}://{1}:{2}@{3}/{4}?charset={5}".format(
                    config["sourceDatabase"]["servertype"],
                    config["sourceDatabase"]["login"],
                    config["sourceDatabase"]["password"],
                    config["sourceDatabase"]["serverhost"],
                    config["sourceDatabase"]["database"],
                    config["sourceDatabase"]["encoding"]
                ),
                echo=echo)
    # engine = sa.create_engine("{0}://{1}:{2}@{3}/{4}".format(
    #                 config["sourceDatabase"]["servertype"],
    #                 config["sourceDatabase"]["login"],
    #                 config["sourceDatabase"]["password"],
    #                 config["sourceDatabase"]["serverhost"],
    #                 config["sourceDatabase"]["database"]
    #             ),
    #             encoding=config["sourceDatabase"]["encoding"],
    #             echo=echo)
    #dialect = sa.dialects.postgresql
    session = sessionmaker(bind=engine, autoflush=False)
    return (engine, session)

#-------------------------------------------------------------------------------------------------
# load the default config file (please set the filename for needed connection)

CONFIG = load_config_yaml_file("config_db_teststand")
CFG_PROTOCOL = load_config_yaml_file("config_db_protocol")
CFG_USER_ACCESS = load_config_yaml_file("config_db_station_users")

def get_teststand_db_connector():
    return createInternalSession(CONFIG, echo=True if DEBUG else False)


def get_protocol_db_connector():
    return createInternalSession(CFG_PROTOCOL, echo=True if DEBUG else False)


def get_teststand_users_db_connector():
    return createInternalSession(CFG_USER_ACCESS, echo=True if DEBUG else False)

def get_mockup_useracess_db_connector():
    return createInternalSession(CFG_USER_ACCESS, echo=True if DEBUG else False)


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # global engine and session generator to share access in the callbacks later
    #srcEngine, SSession = get_teststand_db_connector()
    srcEngine, SSession = get_mockup_useracess_db_connector()

    _log.info(srcEngine.table_names())

# END OF FILE

