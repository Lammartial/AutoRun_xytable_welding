from typing import Tuple
import json
# import SQL managing modules
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

def _createDatabaseSession(config, echo: bool = False, autocommit: bool = True, autoflush: bool = False) -> Tuple[sa.Engine, Session]:
    """Setup a persistent connection to the selected database.
    There is no need to close the connection.

    See: https://docs.sqlalchemy.org/en/14/core/engines.html

    Args:
        config (dict): Possibility to change the connection on demand. Defaults to CONFIG.
        echo (bool, optional): Verbosity level of the SQL driver: True delivers a lot of SQL transfer prints. Defaults to False.
        autocommit (bool, optional): _explanation_ . Defaults to True.
        autoflush (bool, optional): _explanation_ . Defaults to False.

    Returns:
        Tuple of engine and session: These hold and manage the connection for queries.
    """
    # somehow the new Python 310 installation with pymysql does not accept "encoding" parameter for mysql anymore"
    # instead we have to use this WEB API like approach with "charset" appended.
    engine = sa.create_engine("{0}://{1}:{2}@{3}/{4}?charset={5}".format(
                    config["servertype"],
                    config["login"],
                    config["password"],
                    config["serverhost"],
                    config["database"],
                    config["encoding"]
                ),
                pool_pre_ping=True,  # this should automatically reconnect if connection has been lost due to be stale
                echo=echo).execution_options(autocommit=autocommit, autoflush=autoflush)
    #dialect = sa.dialects.postgresql
    session = sessionmaker(bind=engine, autoflush=autoflush)  # autocommit option has been dropped in SQLAlchemy 2.x
    return (engine, session)

def create_connection_welding(server_host: str = "sv-prod") -> Tuple[sa.Engine, Session]:
    return _createDatabaseSession({
            "servertype": "mysql+pymysql",
            "serverhost": server_host,
            "database":   "protocol",
            "login":      "testprotocol",
            "password":   "gedoehns!!",
            "encoding":   "utf8",          
    }, echo=False, autocommit=False)

def create_connection_teststand(server_host: str = "sv-prod") -> Tuple[sa.Engine, Session]:    
    return _createDatabaseSession({
            "servertype": "mysql+pymysql",
            "serverhost": server_host,
            "database":   "teststand",
            "login":      "teststand",
            "password":   "gedoehns!",        
            "encoding":   "utf8",
    }, echo=False, autocommit=False)

def create_connection_trackr2(db_name: str = "trackr2", server_host: str = "sv-prod") -> Tuple[sa.Engine, Session]:
    return _createDatabaseSession({
            "servertype": "mysql+pymysql",
            "serverhost": server_host,
            "database":   db_name,
            "login":      "teststand",
            "password":   "gedoehns!",        
            "encoding":   "utf8",
    }, echo=False, autocommit=False)


# END OF FILE