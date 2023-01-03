from datetime import datetime
from pytz import timezone

def get_tz(tz=None) -> object:
    return timezone(tz if tz else "UTC")

TIME_ZONE = get_tz()

def filterString(self, s):
    n = ""
    for b in s:
        c = chr(b)
        if c.isprintable(): n += c
    return n

def createTimestamp() -> str:
    # make sure we have timezone aware data, even tough it's just UTC
    return datetime.now(tz=TIME_ZONE) # => results in ISO format string in datalog

def createTimestampUnix() -> int:
    return datetime.now(tz=TIME_ZONE).timestamp() * 1e+3 # => ms UNIX timestamp

# END OF FILE