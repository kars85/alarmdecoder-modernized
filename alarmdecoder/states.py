from enum import IntEnum

class FireState(IntEnum):
    """
    Fire alarm status
    """
    NONE = 0
    ALARM = 1
    ACKNOWLEDGED = 2