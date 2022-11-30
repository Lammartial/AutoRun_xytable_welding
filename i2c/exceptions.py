""" Exceptions for battery related errors
"""
__author__="Markus Ruth"
__version__="1.0.0"

# pylint: disable=line-too-long,C0103,C0321,C0413,W0703,W0107,R1702,R0904


class BatteryError(Exception):
    """Our battery base exception class so that all related Exceptions can easiy be catched.

        NOTE: This design adheres to the Liskov substitution principle, since you can
              replace an instance of a base exception class with an instance of a derived exception class.
              Also, it allows you to create an instance of a derived class with the same parameters as the parent.
    Args:
        Exception ([type]): [description]
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.message = args[0]
        self.payload = kwargs.get("payload")

    def __str__(self):
        return "{}[{}]".format(type(self).__name__, self.message)


class BatterySecurityError(BatteryError):
    pass


class BatteryNotRespondError(OSError):
    """Raised if there is any issue on the bus."""
    pass


# END OF FILE
