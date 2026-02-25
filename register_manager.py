import ctypes
import os


# !!! TO BE REVISED !!!


#--------------------
# C Register Mapping
#--------------------

class X86GeneralReg(ctypes.Union):
    """
    Handles the main aliasing of the same registers in same sizes (RAX/EAX/AX/AL/AH) using the c reg script
    """
    class _R8(ctypes.Structure):
        """
        Handles the structure of the low and high bytes for the registers that enable it
        """
        # Signals no padding padding in between the structure entries
        _pack_ = 1

        _fields_ = [("l", ctypes.c_uint8), ("h", ctypes.c_uint8)]
    _fields_ = [
        ("r64", ctypes.c_uint64),
        ("e32", ctypes.c_uint32),
        ("x16", ctypes.c_uint16),
        ("r8", _R8)
    ]

class CPURegsStruct(ctypes.Structure):
    """
    The exact memory layout of your registers.c struct
    """
    # Signals no padding in between values
    _pack_ = 1
    # Defines the structure fields and attributes them to a tuple key at the order they appear in memory
    _fields_ = [
        ("rax", X86GeneralReg), ("rbx", X86GeneralReg),
        ("rcx", X86GeneralReg), ("rdx", X86GeneralReg),
        ("rsi", ctypes.c_uint64), ("rdi", ctypes.c_uint64),
        ("rbp", ctypes.c_uint64), ("rsp", ctypes.c_uint64),
        ("r8", ctypes.c_uint64),  ("r9", ctypes.c_uint64),
        ("r10", ctypes.c_uint64), ("r11", ctypes.c_uint64),
        ("r12", ctypes.c_uint64), ("r13", ctypes.c_uint64),
        ("r14", ctypes.c_uint64), ("r15", ctypes.c_uint64),
        ("rflags", ctypes.c_uint32)
    ]

#----------------------
# Registers interface
#----------------------

class Registers_Interface:

    MASKS_DIRECTIVES = {
        'byte': 0xFF, 'word': 0xFFFF, 'dword': 0xFFFFFFFF, 'qword': 0xFFFFFFFFFFFFFFFF
    }

    def __init__(self, lib_path: str="./libreg.so"):
        # Load the library compiled on your Vivobook
        self.lib = ctypes.CDLL(os.path.abspath(lib_path))
        # Define C return types
        self.lib.get_cpu_state.restype = ctypes.POINTER(CPURegsStruct)
        self.lib.read_8b_reg.restype = ctypes.c_uint64
        self.lib.read_4b_reg.restype = ctypes.c_uint32
        self.lib.read_2b_reg.restype = ctypes.c_uint16
        self.lib.read_1b_reg.restype = ctypes.c_uint8

        self.state = self.lib.get_cpu_state().contents
        self.regs_map = {"rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"}
    
    def read_reg(self, expression: str) -> bytes:
        reg_info: tuple[str,int] = self.get_register_parent(expression)
        reg_id: int = -1
        reg_size: int = reg_info[1]
        try:
            reg_id = next((i for i, key in enumerate(reg_info) if key == expression), -1)
        except StopIteration:
            raise ValueError(f"RERGISTER {expression} DOES NOT EXIST.")
        value: bytes = self.match_read(reg_id, reg_size, self.is_high(expression))


    def get_register_parent(self, expression: str) -> tuple[str,int]:
        """
        Maps the sub-registers to its 64-bit parent and returns it with the mask require to obtain its value
        
        :param expression: sub 64-bit register (has a falback option if a 64-bit register is passed)
        :type expression: str
        :return: Tuple containing the parent register and the mask to the given register
        :rtype: tuple[str, int]
        """
        reg = expression.lower()
        
        # 32-bit: eax -> rax, r8d -> r8
        if reg.startswith('e') or reg.endswith('d'):
            parent = reg.replace('e', 'r', 1) if reg.startswith('e') else reg[:-1]
            return parent, self.MASKS_DIRECTIVES['dword']

        # 16-bit: ax -> rax, r8w -> r8
        if (len(reg) == 2 and reg.endswith('x')) or reg.endswith('w'):
             parent = 'r' + reg if reg.endswith('x') else reg[:-1]
             return parent, self.MASKS_DIRECTIVES['word']

        # 8-bit Low: al -> rax, r8b -> r8
        if reg.endswith('l') or reg.endswith('b'):
            parent = 'r' + reg[:-1] + 'x' if len(reg) == 2 else reg[:-1]
            return parent, self.MASKS_DIRECTIVES['byte']
        
        # 8-bit High: ah -> rax
        if reg.endswith('h') and len(reg) == 2:
            parent = 'r' + reg[0] + 'x'
            return parent, 0xFF00

        # Fallback for 64-bit
        return reg, self.MASKS_DIRECTIVES['qword']
    
    def is_high(self, expression:str ) -> int:
        """
        Verifies if the expression referes to the second eight bytes of a register based on its expression.

        :param expression: Name of the register to use
        :type expression: str
        :return: 1 if the register signals to the second byte of a larger register, 0 if it doesn't
        :rtype: int
        """
        if len(expression) == 2 and expression[1] == 'h':
            return 1
        return 0
    
    def match_read(self, reg_id: int, size: int, is_high: int) -> bytes:
        """
        Directs execution to the correct read funtion in c according to the specified size.

        :param reg_id: Index of the register according to the c structure entries
        :type reg_id: int
        :param size: Size of the rregister to read
        :type size: int
        :param is_high: Flag to signal if the register is the second byte of a parent register (1 - yes; 0 - no)
        :type is_high: int
        :return: bytes of that register
        :rtype: bytes
        """
        if size == 8: return self.lib.read_8b_reg(reg_id)
        if size == 4: return self.lib.read_4b_reg(reg_id)
        if size == 2: return self.lib.read_2b_reg(reg_id)
        if size == 1: return self.lib.read_1b_reg(reg_id, is_high)