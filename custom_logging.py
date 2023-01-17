#
# logging.py - for production test logging
#
from datetime import datetime
import sys

## Init logging start
import logging
import logging.handlers

def logger_init(debug: int, filename_base: str = "C:/Production/station_test") -> None:
    """Initializes the root logger with two handlers for file and stdout logging 

    Args:
        debug (int): 0=info level (normal), 1=debug level on all loggers
    """

    ## get root logger
    # Do NOT use logger = logging.getLogger(__name__) here
    logger = logging.getLogger() ## root logger
    
    # check if we have already handlers set
    if len(logger.handlers)>0:
        logger.debug(f"Logger already set. DEBUG={debug}")
        return
    print("print in logging.logger_init()")
    print("print logging.py __name__: " +__name__)
    print(f"Set logger to DEBUG={debug}")    
    logger.setLevel(logging.DEBUG) # if debug>0 else logging.INFO)
     
    # File handler
    logfilepath = f"{filename_base}_{datetime.utcnow().strftime('%Y%m%d')}.log"
    file = logging.handlers.TimedRotatingFileHandler(f"{logfilepath}", when="midnight", interval=1)
    fileformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(process)d %(module)s %(name)s %(lineno)d: %(message)s")
    file.setLevel(logging.DEBUG) # if debug>0 else logging.INFO)
    file.setFormatter(fileformat)

    # Stream handler
    stream = logging.StreamHandler()
    streamformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(name)s: %(message)s")
    stream.setLevel(logging.DEBUG) # if debug>0 else logging.INFO)
    stream.setFormatter(streamformat)

    # Adding all handlers to the logs
    logger.addHandler(file)
    logger.addHandler(stream)

    # now add a handler for all uncaugt exceptions to find programming errors
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    return

# END OF FILE