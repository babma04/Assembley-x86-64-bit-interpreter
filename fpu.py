import ctypes
import os

class Operand(ctypes.Structure):
    _fields_ = [
        ("address", ctypes.c_int),
        ("value", ctypes.c_int),
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

class FPU:
    def __init__(self, lib_path: str="./libops.so"):
        self.lib = ctypes.CDLL(os.path.abspath(lib_path))

        self.lib.get_operand_info.argtypes = [
            ctypes.c_char_p, ctypes.c_int, ctypes.c_int, 
            ctypes.c_int, ctypes.c_char_p
        ]
        self.lib.set_instruction.argtypes = [ctypes.c_char_p]
        self.lib.clean.argtypes = []
    
    def load_values(self, instruction: str, op1_value: int, op1_address: int | None, op1_type: str | None, op1_size: int, op2_value: int, op2_address: int | None, op2_type: str | None, op2_size: int, flags: dict[str, int]) -> None:
        """
        Initializes the c structure in operations.c
        
        :param instruction: Instruction to do
        :type instrution: str
        :param op1_value: Value of the source operand
        :type op1_value: int
        :param op1_address: Address of the source operand if any
        :type op1_address: int | None
        :param op1_type: Operand type of the source operand if it exists
        :type op1_type: str | None
        :param op1_size: Number of bytes the source operand takes
        :type op1_size: int
        :param op2_value: Value of the destination operand
        :type op2_value: int
        :param op2_address: Address of the destination operand if any
        :type op2_address: int | None
        :param op2_type: Operand type of the destination operand if it exists
        :type op2_type: str | None
        :param op2_size: Number of bytes the destination operand takes
        :type op2_size: int
        :param flags: Current state of the program flags
        :type flags: dict[str, int]
        """
        self.lib.set_instruction(instruction)
        if op1_type != None:
            self.lib.get_operand_info("op1", op1_address, op1_value, op1_size, op1_type)
        if op2_type != None:
            self.lib.get_operand_info("op2", op2_address, op2_value, op2_size, op2_type)
    
    def execute(self):
        self.lib.dispatch()
