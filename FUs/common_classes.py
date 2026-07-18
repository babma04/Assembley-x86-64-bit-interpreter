import ctypes

class Operand(ctypes.Structure):
    _fields_ = [
        ("address", ctypes.c_int),
        ("value", ctypes.c_int64),
        ("size", ctypes.c_int),
        ("op_type", ctypes.c_char_p)
    ]

class Info(ctypes.Structure):
    _fields_ = [
        ("instruction", ctypes.c_char_p),
        ("op1", Operand),
        ("op2", Operand),
        ("result", Operand)
    ]