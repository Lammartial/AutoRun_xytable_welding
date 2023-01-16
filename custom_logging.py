#
# logging.py - for production test logging
#
from datetime import datetime

## Init logging start
import logging
import logging.handlers

def logger_init():
    print("print in logging.logger_init()")
    print("print logging.py __name__: " +__name__)
    path = "C:/Production/"
    filename = "station_test.log"

    ## get logger
    #logger = logging.getLogger(__name__) ## this was my mistake, to init a module logger here
    logger = logging.getLogger() ## root logger
    logger.setLevel(logging.INFO)

    # File handler
    logfilename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{filename}"
    file = logging.handlers.TimedRotatingFileHandler(f"{path}{logfilename}", when="midnight", interval=1)
    #fileformat = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fileformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(name)s: %(message)s")
    file.setLevel(logging.INFO)
    file.setFormatter(fileformat)

    # Stream handler
    stream = logging.StreamHandler()
    #streamformat = logging.Formatter("%(asctime)s [%(levelname)s:%(module)s] %(message)s")
    streamformat = logging.Formatter("%(asctime)s [%(levelname)s]: %(name)s: %(message)s")
    stream.setLevel(logging.INFO)
    stream.setFormatter(streamformat)

    # Adding all handlers to the logs
    logger.addHandler(file)
    logger.addHandler(stream)


# END OF FILE