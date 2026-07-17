from enum import IntEnum

class ExitCode(IntEnum):
    DATA_FORMAT_ERROR = -1
    BSS_FORMAT_ERROR = -2
    CONSTANT_ERROR = -3
    NO_START_LABEL = 1
    DUPLICATE_LABEL = 2
    STACK_OVERFLOW = 16
    # To be continued later