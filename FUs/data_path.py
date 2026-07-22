import sys

from exit_codes import ExitCode

from helpers.my_types import LabelMap

from bridges.register_manager import Registers_Interface
from bridges.data_memory import Data_Memory

from parsing.patter_matching_helpers import INSTRUCTIONS
from parsing.instruction_parser import Operand


# Cached O(1) lookup dictionary for data path instruction opcodes
DATA_PATH_OPCODES = {name.lower(): index for index, name in enumerate(INSTRUCTIONS['data_path'])}

class Data_Path:
    """
    
    """    

    __slots__ = ["registers", "memory", "labels", "op1", "op2", "opcode", "_execute_data_path_map"]

    def __init__(self, registers: Registers_Interface, memory: Data_Memory, labels: LabelMap) -> None:

            self.registers = registers
            self.memory = memory
            self.labels = labels

            self._execute_data_path_map = (
                self.execute_lea,       # 0: lea
                self.execute_mov,       # 1: mov
                
                self.execute_jmp,       # 2: jmp
                
                self.execute_je,        # 3: je
                self.execute_je,        # 4: jz (alias)
                self.execute_jne,       # 5: jne
                self.execute_jne,       # 6: jnz (alias)
                
                self.execute_jb,        # 7: jb
                self.execute_jb,        # 8: jc (alias)
                self.execute_jb,        # 9: jnae (alias)
                self.execute_jnb,       # 10: jnb
                self.execute_jnb,       # 11: jnc (alias)
                self.execute_jnb,       # 12: jae (alias)
                self.execute_ja,        # 13: ja
                self.execute_ja,        # 14: jnbe (alias)
                self.execute_jbe,       # 15: jbe
                self.execute_jbe,       # 16: jna (alias)
                
                self.execute_jl,        # 17: jl
                self.execute_jl,        # 18: jnge (alias)
                self.execute_jge,       # 19: jge
                self.execute_jge,       # 20: jnl (alias)
                self.execute_jg,        # 21: jg
                self.execute_jg,        # 22: jnle (alias)
                self.execute_jle,       # 23: jle
                self.execute_jle,       # 24: jng (alias)
                
                self.execute_js,        # 25: js
                self.execute_jns,       # 26: jns
                
                self.execute_jo,        # 27: jo
                self.execute_jno,       # 28: jno
                
                self.execute_jp,        # 29: jp
                self.execute_jp,        # 30: jpe (alias)
                self.execute_jnp,       # 31: jnp
                self.execute_jnp,       # 32: jpo (alias)
            )

            self.opcode: int
            self.op1: Operand
            self.op2: Operand


    def __del__(self) -> None:
        """
        Frees C-allocated state structures upon garbage collection.
        """
        state = getattr(self, "state", None)
        lib = getattr(self, "lib", None)
        if state and lib:
            lib.free_operand_state(state)
        
    
    def load_values(self, instruction: str, op1: Operand, op2: Operand) -> None:
            """
            Initializes the operands and instruction's opcode to be make the execution runnable
    
            :param instruction: Instruction to execute
            :type instruction: str
            :param op1: Operand obj for the first operand
            :param op2: Operand obj for the second operand
            """
            self.opcode = self.get_opcode(instruction)

            if op1 and op1.is_valid():
                self.op1 = op1
    
            if op2 and op2.is_valid():
                self.op2 = op2


    def execute(self):
        """
        Executes the instructions valid in the data path 
        
        :raises RuntimeError: If comes across any invalid condition to the operation's execution or an error is raised during execution
        """
        try:
            self.validate_data_path_instruction()
            self._execute_data_path_map[self.opcode]()
        except SyntaxError as e:
            print(e)
            raise RuntimeError
        except NotImplementedError as e:
            print(e)
            raise RuntimeError
        

    # ----------------
    # Static helpers 
    # ----------------

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


    # ----------------------
    # Conditions Validation
    # ----------------------

    def validate_data_path_instruction(self) -> None:
        """
        Routes the parsed integer opcode to the correct validation logic.
        
        :param opcode: The 0-based ordinal index of the data path instruction.
        :raises NotImplementedError: If an invalid opcode is provided.
        """
        opcode = self.opcode

        if opcode == 1:
            self.validate_mov_conditions()
        elif opcode == 0:
            self.validate_lea_conditions()
        elif 2 <= opcode <= 12:
            self.validate_jump_conditions()
        else:
            raise NotImplementedError(f"Validation for data path opcode {opcode} is not implemented.")

    def validate_lea_conditions(self) -> None:
        """
        Validates the conditions for the LEA (Load Effective Address) instruction.
        Optimized for high-performance instruction decoding.

        :raises SyntaxError: If any LEA execution rules are violated.
        """
        op1 = self.op1
        op2 = self.op2

        # 1. Fast-fail validity check
        if not op1.is_valid() or not op2.is_valid():
            raise SyntaxError("Both destination and source operands must exist for the LEA instruction.")

        # 2. Destination MUST be a register (Type 1)
        if op1.type != 1:
            raise SyntaxError("The destination operand for LEA must be a register.")

        # 3. Source MUST be a memory expression (Type 2)
        if op2.type != 2:
            raise SyntaxError("The source operand for LEA must be a memory address expression.")

    def validate_mov_conditions(self) -> None:
        """
        Validates the conditions for the MOV instruction to be executed correctly.
        Optimized for high-performance instruction decoding.

        :raises SyntaxError: If any of the MOV instruction execution rules are violated.
        """
        
        op1 = self.op1
        op2 = self.op2

        # 1. Fast-fail validity check
        if not op1.is_valid() or not op2.is_valid():
            raise SyntaxError("Both destination and source operands must exist for the MOV instruction.")

        op1_type = op1.type
        op2_type = op2.type

        # 2. Destination cannot be an immediate
        if op1_type == 3:
            raise SyntaxError("The destination operand cannot be an immediate value or constant for the MOV instruction.")

        dest_is_mem = op1_type == 2

        # 3. Read-Only Memory Protection (.rodata segment validation)
        if dest_is_mem and op1.address < 0x600000:
            raise SyntaxError("The destination memory address lies in read-only memory (.rodata/.text) and cannot be written to.")

        # 4. Memory-to-Memory check
        if dest_is_mem and op2_type == 2:
            raise SyntaxError("The source and destination operands cannot both be memory addresses for the MOV instruction.")

        op1_size = op1.size
        op2_size = op2.size

        # 5. Operand size mismatch check
        if op1_size and op2_size and not op2_type == 3:
            if op1_size != op2_size:
                raise SyntaxError(
                    f"Operand size mismatch for MOV instruction: "
                    f"Destination size is {op1_size} byte(s), but source size is {op2_size} byte(s)."
                )

        # 6. High-register byte access mismatch
        if op1.is_high and not op2.is_high and op2_size == 8:
            raise SyntaxError("Cannot mix high 8-bit registers (AH, BH, CH, DH) with 64-bit registers or extended byte registers.")


    def validate_jump_conditions(self) -> None:
        """
        Validates the conditions for all branching and jump instructions (jmp, je, jne, etc.).
        Optimized for high-performance instruction decoding.

        :raises SyntaxError: If jump instruction execution rules are violated.
        """
        # Cache references locally
        op1 = self.op1
        op2 = self.op2

        # 1. Must have exactly one valid operand (the destination)
        if not op1.is_valid():
            raise SyntaxError("Control flow instructions require exactly one destination operand.")

        # 2. Ensure the parser didn't accidentally attach a second operand
        if op2.is_valid():
            raise SyntaxError("Control flow instructions cannot take a second operand.")
        

    # -----------------
    # Implementations
    # -----------------
        
    def execute_jmp (self) -> int:
        try: 
            return self.labels[self.op1.expression]
        except KeyError: 
            return -1   

    def execute_je(self) -> None:
        """Jump if Equal / Jump if Zero (ZF == 1)."""
        if self.registers.read_zero():
            self.execute_jmp()

    def execute_jne(self) -> None:
        """Jump if Not Equal / Jump if Not Zero (ZF == 0)."""
        if not self.registers.read_zero():
            self.execute_jmp()

    def execute_jb(self) -> None:
        """Jump if Below / Jump if Carry (CF == 1). Unsigned comparison."""
        if self.registers.read_carry():
            self.execute_jmp()

    def execute_jnb(self) -> None:
            """Jump if Not Below / Not Carry (CF == 0)."""
            if not self.registers.read_carry():
                self.execute_jmp()

    def execute_ja(self) -> None:
        """Jump if Above (CF == 0 and ZF == 0). Unsigned comparison."""
        if not self.registers.read_carry() and not self.registers.read_zero():
            self.execute_jmp()

    def execute_jbe(self) -> None:
            """Jump if Below or Equal (CF == 1 or ZF == 1)."""
            if self.registers.read_carry() or self.registers.read_zero():
                self.execute_jmp()

    def execute_jl(self) -> None:
        """Jump if Less (SF != OF). Signed comparison."""
        sf = self.registers.read_sign()
        of = self.registers.read_overflow
        if sf != of:
            self.execute_jmp()

    def execute_jg(self) -> None:
        """Jump if Greater (ZF == 0 and SF == OF). Signed comparison."""
        zf = self.registers.read_zero()
        sf = self.registers.read_sign()
        of = self.registers.read_overflow()
        if not zf and (sf == of):
            self.execute_jmp()

    def execute_jge(self) -> None:
            """Jump if Greater or Equal (SF == OF)."""
            if self.registers.read_sign() == self.registers.read_overflow():
                self.execute_jmp()

    def execute_jle(self) -> None:
        """Jump if Less or Equal (ZF == 1 or SF != OF)."""
        if self.registers.read_zero() or (self.registers.read_sign() != self.registers.read_overflow()):
            self.execute_jmp()

    def execute_js(self) -> None:
        """Jump if Sign (SF == 1). Negative result."""
        if self.registers.read_sign():
            self.execute_jmp()

    def execute_jns(self) -> None:
        """Jump if Not Sign / Positive (SF == 0)."""
        if not self.registers.read_sign():
            self.execute_jmp()

    def execute_jo(self) -> None:
        """Jump if Overflow (OF == 1)."""
        if self.registers.read_overflow():
            self.execute_jmp()
    
    def execute_jno(self) -> None:
            """Jump if Overflow (OF == 1)."""
            if not self.registers.read_overflow():
                self.execute_jmp()

    def execute_jp(self) -> None:
        """Jump if Parity Even (PF == 1)."""
        if self.registers.read_parity():
            self.execute_jmp()

    def execute_jnp(self) -> None:
        """Jump if Parity Odd (PF == 0)."""
        if not self.registers.read_parity():
            self.execute_jmp()