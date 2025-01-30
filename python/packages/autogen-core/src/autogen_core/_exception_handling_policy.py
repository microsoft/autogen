from enum import Enum

class ExceptionHandlingPolicy(Enum):
    IGNORE_AND_LOG = "IGNORE_AND_LOG"
    RAISE = "RAISE"
