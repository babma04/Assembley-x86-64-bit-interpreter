import ctypes
import os

from bridges.register_manager import Registers_Interface
from bridges.data_memory import Data_Memory

# might not be needed later
from .common_classes import Operand, Info

from parsing.patter_matching_helpers import INSTRUCTIONS
from parsing.instruction_parser import Operand as OP
from conftest import PROJECT_ROOT


# Lookup opcodes table
ALU_OPCODES = {name.lower(): index for index, name in enumerate(INSTRUCTIONS['alu'])}

class ALU:  

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
        # Best-effort: free the C-side struct once this ALU is collected.
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

    def execute(self) -> None:
        """
        Executes the instruction loaded in the c structure.
        """
        self.lib.dispatch(self.state)


    @staticmethod
    def get_opcode(instruction: str) -> int:
        """
        Retrieves the numeric opcode corresponding to the given ALU instruction.

        :param instruction: Name of the instruction (e.g., "add", "sub")
        :type instruction: str
        :return: 0-based opcode index if valid, or -1 if the instruction is unsupported
        :rtype: int
        """
        return ALU_OPCODES.get(instruction.lower(), -1)
