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

class RegisterManager:
    def __init__(self, lib_path: str="./libreg.so"):
        # Load the library compiled on your Vivobook
        self.lib = ctypes.CDLL(os.path.abspath(lib_path))
        self.lib.get_cpu_state.restype = ctypes.POINTER(CPURegsStruct)
        
        # Pointer to the actual C memory address
        self.raw = self.lib.get_cpu_state().contents
        
        # Mapping for easy string-based access
        self.complex_regs = {"rax", "rbx", "rcx", "rdx"}
        self.regs_map = {"rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"}