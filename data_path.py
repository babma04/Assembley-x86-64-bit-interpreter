import ctypes
import os
from register_manager import Registers_Interface
from segment_mapper import Segment_Mapper

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



class Data_Path:
    """
    
    """    

    JUMPS_MAPPING = ["je", "jne", "jg", "jge", "jl", "jle", "ja", "jae", "jb", "jbe", "jz", "js", "jo", "jc"]

    def __init__(self, register: Registers_Interface, libmmu_path: str="./libmmu.so") -> None:
        self.libmmu = ctypes.CDLL(os.path.abspath(libmmu_path))
        self.register = register

        # Define C return and args types
        self.libmmu.write_memory.argtypes = [ctypes.c_int, ctypes.c_int64, ctypes.c_int]
        self.libmmu.read_memory.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int64)]

        __slot__ = ["libmmu", "register", "instruction", "op1", "op2", "op1_value", "op2_value", "op1_address", "op2_address", "op1_type", "op2_type", "op1_size", "op2_size"]


        
    
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
        self.instruction = instruction
        self.op1_value = op1_value
        self.op1_address = op1_address
        self.op1_type = op1_type
        self.op1_size = op1_size
        self.op2_value = op2_value
        self.op2_address = op2_address
        self.op2_type = op2_type
        self.op2_size = op2_size

    def execute(self):
        """
        Executes the instrcutions valid in the data path (mov and jumps)
        """
        if self.instruction == "mov":
            self.ex_mov()
        elif self.instruction in Data_Path.JUMPS_MAPPING:
            self.ex_jp()
    
    def ex_mov(self):
        """
        Executes the mov instruction
        """
        try:
            self.validate_mov_conditions() # Should already be validated in the instruction fetch stage.
            self.libmmu.write_memory(self.op2_address, self.op1_value, self.op1_size)
        except SyntaxError as e:
            print(f"Error: {e}")

    def validate_mov_conditions(self):
        """
        Validates the conditions for the mov instruction to be executed correctly.

        :raises SyntaxError: if any of the mov instruction conditions are not met
        """

        # INVALID CONDITIONS:

        # Both operands must exist for the mov instruction.
        if self.op1_type == None or self.op2_type == None:
            raise SyntaxError("Both operands must exist for the mov instruction.")
        # Both operands cannot be memory addresses simultaneously for the mov instruction.
        elif len(self.op1_type.split()) == 2 or len(self.op2_type.split()) == 2 and self.op1_type[1] == "memory" and self.op2_type[1] == "memory":
            raise SyntaxError("The source and destination operands cannot both be memory addresses for the mov instruction.")
        # The destination operand cannot be an immediate value or a constant for the mov instruction.
        elif self.op1_type == "immediate" or self.op1_type == "constant":
            raise SyntaxError("The source operand cannot be an immediate value or a constant for the mov instruction.")
        # The destination operand cannot be a value in immutable rodata for the mov instruction.
        elif self.op1_address != None and self.op1_address < Segment_Mapper.DATA_BASE:
            raise SyntaxError("The source operand must be in the data or bss segment for the mov instruction.")
        # COMPLEMENT WITH MORE CONDITIONS
        
    def ex_jp(self):
        """
        Executes the jump instructions
        """
        
        
        
        