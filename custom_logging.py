"""

custom_logging.py - for production test logging


Use this pattern on top of a module to prepare for logging

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

...

Then at the "__main__" guard use this pattern:

## Initialize the logging
logger_init(filename_base="local_log")  ## init root logger with different filename
_log = getLogger(__name__, DEBUG)


"""

from datetime import datetime
import sys
import logging
import logging.handlers


def logger_init(filename_base: str | None = "C:/Production/station_test") -> None:
    """Initializes the root logger with two handlers for file and stdout logging

    Args:
        filename_base (str): filename base or None to deactivate file logging

    """

    ## get root logger
    # Do NOT use logger = logging.getLogger(__name__) here
    logger = logging.getLogger() ## root logger

    # check if we have already handlers set
    if len(logger.handlers)>0:
        logger.debug(f"Logger already set.")
        return

    print("print in logging.logger_init()")
    print("print logging.py __name__: " +__name__)
    logger.setLevel(logging.NOTSET)

    # File handler
    if filename_base:
        logfilepath = f"{filename_base}_{datetime.utcnow().strftime('%Y%m%d')}.log"
        file = logging.handlers.TimedRotatingFileHandler(f"{logfilepath}", when="midnight", interval=1)
        fileformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(process)d %(module)s %(name)s %(lineno)d: %(message)s")
        file.setLevel(logging.NOTSET) # if debug>0 else logging.INFO)
        file.setFormatter(fileformat)
        logger.addHandler(file)  # activate file handler

    # Stream handler
    stream = logging.StreamHandler()
    streamformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(name)s: %(message)s")
    stream.setLevel(logging.NOTSET) # if debug>0 else logging.INFO)
    stream.setFormatter(streamformat)
    logger.addHandler(stream)  # activate handler

    # now add a handler for all uncaugt exceptions to find programming errors
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    return

#--------------------------------------------------------------------------------------------------

def getLogger(namespace: str, debug: int) -> logging.Logger:
    """Get a local logger. This function should be used to get a module logger.

    Args:
        namespace (str): _description_
        debug (int): 0=warning level (normal), 1=info level, 2=debug level

    Returns:
        logging.Logger: _description_
    """
    if debug > 1:
        level = logging.DEBUG
    elif debug > 0:
        level = logging.INFO
    else:
        level = logging.WARNING
    _log = logging.getLogger(namespace)
    _log.setLevel(level)
    return _log


# END OF FILE