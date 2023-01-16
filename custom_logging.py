#
# logging.py - for production test logging
#
from datetime import datetime
import sys

## Init logging start
import logging
import logging.handlers

def logger_init(debug: int) -> None:
    print("print in logging.logger_init()")
    print("print logging.py __name__: " +__name__)
    path = "C:/Production/"
    filename = "station_test.log"

    ## get logger
    # Do NOT use logger = logging.getLogger(__name__) here
    logger = logging.getLogger() ## root logger
    logger.setLevel(logging.DEBUG if debug>0 else logging.INFO)

    # File handler
    #logfilename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{filename}"
    logfilename = datetime.utcnow().strftime("%Y%m%d") + f"_{filename}"
    file = logging.handlers.TimedRotatingFileHandler(f"{path}{logfilename}", when="midnight", interval=1)
    fileformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(process)d %(module)s %(name)s %(lineno)d: %(message)s")
    file.setLevel(logging.DEBUG if debug>0 else logging.INFO)
    file.setFormatter(fileformat)

    # Stream handler
    stream = logging.StreamHandler()
    streamformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(name)s: %(message)s")
    stream.setLevel(logging.DEBUG if debug>0 else logging.INFO)
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