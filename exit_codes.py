from enum import IntEnum

class ExitCode(IntEnum):
    DATA_FORMAT_ERROR = -1
    BSS_FORMAT_ERROR = -2
    CONSTANT_DECLARATION_ERROR = -3
    NO_START_LABEL = 1
    DUPLICATE_LABEL = 2
    STACK_OVERFLOW = 16
    UNOPENABLE_FILE = 10
    # To be continued later