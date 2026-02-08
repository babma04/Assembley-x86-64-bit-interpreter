class Register64:

    """
    utility class used to create and simulate register behaviour for the CPU class.
    It's purpose is to enable register objects to be created, stored and used all along the cpu class.
    Provides methods to set and alter its values for each size of register in Assembly x86.
    """
    def __init__(self):
        self._value = 0  # internal raw 64-bit value

    # ------------ 64-bit ------------
    @property
    def _64(self):
        return self._value & 0xFFFFFFFFFFFFFFFF

    @_64.setter
    def _64(self, v):
        self._value = int(v) & 0xFFFFFFFFFFFFFFFF

    # ------------ 32-bit ------------
    @property
    def _32(self):
        return self._value & 0xFFFFFFFF

    @_32.setter
    def _32(self, v):
        # only replace lower 32 bits
        self._value = (self._value & 0xFFFFFFFF00000000) | (int(v) & 0xFFFFFFFF)

    # ------------ 16-bit ------------
    @property
    def _16(self):
        return self._value & 0xFFFF

    @_16.setter
    def _16(self, v):
        self._value = (self._value & 0xFFFFFFFFFFFF0000) | (int(v) & 0xFFFF)

    # ------------ 8-bit low ------------
    @property
    def L8(self):
        return self._value & 0xFF

    @L8.setter
    def L8(self, v):
        self._value = (self._value & 0xFFFFFFFFFFFFFF00) | (int(v) & 0xFF)

    # ------------ 8-bit high ------------
    @property
    def H8(self):
        return (self._value >> 8) & 0xFF

    @H8.setter
    def H8(self, v):
        # clear bits 8–15, then insert v
        self._value = (self._value & 0xFFFFFFFFFFFF00FF) | ((int(v) & 0xFF) << 8)