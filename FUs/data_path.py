import ctypes
import os

from bridges.register_manager import Registers_Interface
from bridges.data_memory import Data_Memory

# might not be needed later
from .common_classes import Operand, Info

from parsing.patter_matching_helpers import INSTRUCTIONS
from parsing.instruction_parser import Operand as OP
from conftest import PROJECT_ROOT


# Cached O(1) lookup dictionary for data path instruction opcodes
DATA_PATH_OPCODES = {name.lower(): index for index, name in enumerate(INSTRUCTIONS['data_path'])}

class Data_Path:
    """
    
    """    

    __slots__ = ["lib", "state"]

    def __init__(self, registers: Registers_Interface, memory: Data_Memory, libops_path: str = os.path.join(PROJECT_ROOT, "lib/liboperations.so")) -> None:
            self.lib = ctypes.CDLL(os.path.abspath(libops_path))
    
            self.lib.create_operand_state.argtypes = []
            self.lib.create_operand_state.restype = ctypes.c_void_p
    
            self.lib.free_operand_state.argtypes = [ctypes.c_void_p]
            self.lib.free_operand_state.restype = None
    
            self.lib.set_registers_ref.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            self.lib.set_registers_ref.restype = None
    
            self.lib.set_table_ref.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            self.lib.set_table_ref.restype = None
    
            # Updated to match the new Operand C struct fields
            self.lib.set_operand_info.argtypes = [
                ctypes.c_void_p,      # Info*
                ctypes.c_char_p,      # operand slot ("op1" / "op2")
                ctypes.c_longlong,    # address
                ctypes.c_int,         # op_type (OpType enum)
                ctypes.c_uint8,       # size
                ctypes.c_uint8,       # is_high
                ctypes.c_uint8,       # is_signed
            ]
            self.lib.set_operand_info.restype = None
    
            # Opcode is now an enum/int instead of a string pointer
            self.lib.set_instruction.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self.lib.set_instruction.restype = None
    
            self.lib.clean.argtypes = [ctypes.c_void_p]
            self.lib.clean.restype = None
    
            self.lib.dispatch.argtypes = [ctypes.c_void_p]
            self.lib.dispatch.restype = None
    
            # Prepares all needed info
            self.state = self.lib.create_operand_state()
            self.lib.set_registers_ref(self.state, registers)
            self.lib.set_table_ref(self.state, memory)


    def __del__(self) -> None:
        """
        Frees C-allocated state structures upon garbage collection.
        """
        state = getattr(self, "state", None)
        lib = getattr(self, "lib", None)
        if state and lib:
            lib.free_operand_state(state)
        
    
    def load_values(self, instruction: str, op1: OP, op2: OP) -> None:
            """
            Initializes the c structure in operations.c
    
            :param instruction: Instruction to execute
            :type instruction: str
            :param op1: Operand obj for the first operand
            :param op2: Operand obj for the second operand
            """
            self.lib.clean(self.state)
            opcode: int = self.get_opcode(instruction)
            self.lib.set_instruction(self.state, opcode)
    
            if op1 and op1.is_valid():
                self.lib.set_operand_info(
                    self.state, b"op1",
                    op1.address,
                    int(op1.type),
                    op1.size,
                    getattr(op1, "is_high", 0),
                    getattr(op1, "is_signed", 0)
                )
    
            if op2 and op2.is_valid():
                self.lib.set_operand_info(
                    self.state, b"op2",
                    op2.address,
                    int(op2.type),
                    op2.size,
                    getattr(op2, "is_high", 0),
                    getattr(op2, "is_signed", 0)
                )


    def execute(self):
        """
        Executes the instrcutions valid in the data path (mov and jumps)
        """
        if self.instruction == "mov":
            self.ex_mov()
        elif self.instruction in Data_Path.JUMPS_MAPPING:
            self.ex_jp()


    @staticmethod
    def get_opcode(instruction: str) -> int:
        """
        Retrieves the numeric opcode corresponding to the given data path instruction (e.g., mov, lea, jmp).

        :param instruction: Name of the instruction (e.g., "mov", "lea", "jmp")
        :type instruction: str
        :return: 0-based opcode index if valid, or -1 if the instruction is unsupported
        :rtype: int
        """
        return DATA_PATH_OPCODES.get(instruction.lower(), -1)









    
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
        elif self.op1_address != None and self.op1_address < 0x600000:  # Assuming rodata segment finishes at most at 0x600000
            raise SyntaxError("The source operand must be in the data or bss segment for the mov instruction.")
        # COMPLEMENT WITH MORE CONDITIONS
        
    def ex_jp(self):
        """
        Executes the jump instructions
        """
        
        
        
        