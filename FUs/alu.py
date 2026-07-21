import ctypes
import os

from bridges.register_manager import Registers_Interface
from bridges.data_memory import Data_Memory

from .common_classes import Operand, Info

from parsing.instruction_parser import Operand as OP
from conftest import PROJECT_ROOT

class ALU:

    __slots__ = ["lib", "state"]

    def __init__(self, registers: Registers_Interface, memory: Data_Memory, libops_path: str=os.path.join(PROJECT_ROOT, "lib/liboperations.so")) -> None:
        self.lib = ctypes.CDLL(os.path.abspath(libops_path))

        self.lib.create_operand_state.argtypes = []
        self.lib.create_operand_state.restype = ctypes.c_void_p

        self.lib.free_operand_state.argtypes = [ctypes.c_void_p]
        self.lib.free_operand_state.restype = None

        self.lib.set_registers_ref.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.lib.set_registers_ref.restype = None

        self.lib.set_table_ref.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.lib.set_table_ref.restype = None

        self.lib.set_operand_info.argtypes = [
            ctypes.c_void_p,      # Info*
            ctypes.c_char_p,      # operand ("op1" / "op2")
            ctypes.c_longlong,    # address
            ctypes.c_longlong,    # value
            ctypes.c_uint8,       # size
            ctypes.c_char_p,      # op_type
        ]
        self.lib.set_operand_info.restype = None

        self.lib.set_instruction.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
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

        :param instruction: Instruction to do
        :type instruction: str
        :param op1: Operand obj for the first operand
        :param op2: Operand obj for the second operand
        """
        self.lib.clean(self.state)
        self.lib.set_instruction(self.state, instruction.encode())

        if op1.is_valid():
            self.lib.set_operand_info(
                self.state, b"op1",
                op1.address, op1.address, op1.size,
                op1.type
            )

        if op2.is_valid():
            self.lib.set_operand_info(
                self.state, b"op2",
                op2.address, op2.address, op2.size,
                op2.type
            )

    def execute(self) -> None:
        """
        Executes the instruction loaded in the c structure.
        """
        self.lib.dispatch(self.state)