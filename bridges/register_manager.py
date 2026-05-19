import ctypes
import os

#---------------------
# Registers interface
#---------------------

class Registers_Interface:

    # Mapping of the sizes of the registers according to their directives
    SIZE_DIRECTIVES = {
        'byte': 1, 'word': 2, 'dword': 4, 'qword': 8
    }

    # Parent registers mapping to get indexes
    REGISTERS_MAP = [
        "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"
    ]

    # Class attributes for the library and the pointer to the registers structure in c
    __slots__ = ["lib", "regs"]

    def __init__(self) -> None:
        # Load the library compiled s
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        _lib_path = os.path.join(_base_dir, "/lib/libreg.so")
        self.lib = ctypes.CDLL(_lib_path)

        # Initializes a costume pointer to the registers structure
        self.regs = self.lib.CPURegs_create()

        # -------------------------------
        # Define C return and args types
        # -------------------------------

        self.lib.CPURegs_create.restype = ctypes.c_void_p
        self.lib.CPURegs_free.argtypes = [ctypes.c_void_p]
        self.lib.write_reg.argtypes = [
            ctypes.c_void_p,      # Pointer to the struct in memory
            ctypes.c_int,                       # reg_id
            ctypes.c_int64,                     # value to write
            ctypes.c_int,                       # byte size of the reg (1, 2, 4, 8)
            ctypes.c_int                        # is_high
        ]
        self.lib.read_8b_reg.argtypes = [
            ctypes.c_void_p,      # Pointer to the struct in memory
            ctypes.c_uint8                      # reg_id
        ]
        self.lib.read_8b_reg.restype = ctypes.c_uint64
        self.lib.read_4b_reg.argtypes = [
            ctypes.c_void_p,      
            ctypes.c_uint8
        ]
        self.lib.read_4b_reg.restype = ctypes.c_uint32
        self.lib.read_2b_reg.argtypes = [
            ctypes.c_void_p, 
            ctypes.c_uint8                      
        ]
        self.lib.read_8b_reg.restype = ctypes.c_uint16
        self.lib.read_1b_reg.argtypes = [
            ctypes.c_void_p,      
            ctypes.c_uint8,                     
            ctypes.c_uint8  # is_high
        ]
        self.lib.read_1b_reg.restype = ctypes.c_uint8
        self.lib.read_rflags.argtypes = [ctypes.c_void_p]
        self.lib.read_rflags.restype = ctypes.c_uint32
        self.lib.read_trap_flag.argtypes = [ctypes.c_void_p]
        self.lib.read_trap_flag.restype = ctypes.c_int
        self.lib.read_carry_flag.argtypes = [ctypes.c_void_p]
        self.lib.read_carry_flag.restype = ctypes.c_int
        self.lib.read_zero_flag.argtypes = [ctypes.c_void_p]
        self.lib.read_zero_flag.restype = ctypes.c_int        
        self.lib.read_sign_flag.argtypes = [ctypes.c_void_p]
        self.lib.read_sign_flag.restype = ctypes.c_int 
        self.lib.read_overflow_flag.argtypes = [ctypes.c_void_p]
        self.lib.read_overflow_flag.restype = ctypes.c_int 
        self.lib.write_rflags.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32                 # value
        ]
        self.lib.exch_rflag.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint8                 # flag_id
        ]
        self.lib.set_trap_flag.argtypes = [ctypes.c_void_p]

    #------------------
    # Register Writing
    #------------------

    def write_reg(self, expression: str, value: int, signed: bool = False) -> None:
        """
        Writes to the register holder in the c file structure of registers.\n
        (Re)Writes the given register with the given size if both are valid.
        Raises ValueError if any are not valid.

        :param expression: Name of the register to write to
        :type expression: str
        :param value: Value to write the register with
        :type value: int
        :param signed: Flag that signals if the value is signed or not
        :type signed: bool
        :raises ValueError: If either the expression is not a register name or the value is too big for the register
        """
        reg_info: tuple[str,int] = self.get_register_parent(expression)
        reg_id: int = -1
        reg_size: int = reg_info[1]

        bits: int = reg_size * 8
        min_signed_val: int = -(2**(bits - 1))
        max_unsigned_val: int = (2**(bits - 1))

        if value < min_signed_val or value > max_unsigned_val:
            raise ValueError(f"INVALID VALUE {value} TO ATTRIBUTE TO {expression}. OVERFLOW DETECTED.")
        try:
            reg_id = next((i for i, key in enumerate(self.REGISTERS_MAP) if key == reg_info[0]), -1)
        except StopIteration:
            raise ValueError(f"REGISTER {expression} DOES NOT EXIST.")
        
        self.lib.write_reg(reg_id, value, reg_size, self.is_high(expression))
        self.lib.set_reg_sign(reg_id, 1 if signed else 0)

    #------------------
    # Register Reading
    #------------------

    def read_reg(self, expression: str) -> int:
        """
        Returns the value of the given register in the c structure file.
        Raises ValueError if the register given is not found.
        
        :param expression: Name of the register to read
        :type expression: str
        :return: Value of the given register
        :rtype: int
        :raises ValueError: If a non existent expression is passed to the execution
        """
        reg_info: tuple[str,int] = self.get_register_parent(expression)
        reg_id: int = -1
        reg_size: int = reg_info[1]
        
        try:
            reg_id = next((i for i, key in enumerate(self.REGISTERS_MAP) if key == reg_info[0]), -1)
        except StopIteration:
            raise ValueError(f"REGISTER {expression} DOES NOT EXIST.")
        # Because int is unbounded in python this is safe
        value: int =  self.match_read(reg_id, reg_size, self.is_high(expression))

        if self.lib.is_signed(reg_id) == 1:
            bits: int = reg_size * 8            
            # Manual 2's complement conversion
            if value & (1 << (bits - 1)):
                value -= (1 << bits)
        return value
    

# ---------
# Helpers
# ---------

    def get_register_parent(self, expression: str) -> tuple[str,int]:
        """
        Maps the sub-registers to its 64-bit parent and returns it with the mask require to obtain its value.
        
        :param expression: sub 64-bit register (has a fallback option if a 64-bit register is passed)
        :type expression: str
        :return: Tuple containing the parent register and the size of the given register
        :rtype: tuple[str, int]
        """
        reg = expression.lower()
        
        # 32-bit
        if reg.startswith('e') or reg.endswith('d'):
            parent = reg.replace('e', 'r', 1) if reg.startswith('e') else reg[:-1]
            return parent, self.SIZE_DIRECTIVES['dword']

        # 16-bit
        if (len(reg) == 2 and reg.endswith('x')) or reg.endswith('w'):
             parent = 'r' + reg if reg.endswith('x') else reg[:-1]
             return parent, self.SIZE_DIRECTIVES['word']

        # 8-bit
        if reg.endswith('l') or reg.endswith('h') or reg.endswith('b'):
            parent = 'r' + reg[:-1] + 'x' if len(reg) == 2 else reg[:-1]
            return parent, self.SIZE_DIRECTIVES['byte']

        # Fallback for 64-bit
        return reg, self.SIZE_DIRECTIVES['qword']
    
    def is_high(self, expression:str ) -> int:
        """
        Verifies if the expression refers to the second eight bytes of a register based on its expression.

        :param expression: Name of the register to use
        :type expression: str
        :return: 1 if the register signals to the second byte of a larger register, 0 if it doesn't
        :rtype: int
        """
        if len(expression) == 2 and expression[1] == 'h':
            return 1
        return 0
    
    def match_read(self, reg_id: int, size: int, is_high: int) -> int:
        """
        Directs execution to the correct read function in c according to the specified size.

        :param reg_id: Index of the register according to the c structure entries
        :type reg_id: int
        :param size: Size of the register to read
        :type size: int
        :param is_high: Flag to signal if the register is the second byte of a parent register (1 - yes; 0 - no)
        :type is_high: int
        :return: value of that register
        :rtype: int
        """
        if size == 8: return self.lib.read_8b_reg(reg_id)
        elif size == 4: return self.lib.read_4b_reg(reg_id)
        elif size == 2: return self.lib.read_2b_reg(reg_id)
        else: return self.lib.read_1b_reg(reg_id, is_high)

#----------------------------------
# Flag Reading and Writing Methods
#----------------------------------

    # TO IMPLEMENT
    ## CURRENT PLAN IT TO ADD A STEP VERIFICATION STEP THAT VERIFIES ALL FLAGS IN THE CONTROL UNIT AND THEN CALLS THE APPROPRIATE FUNCTION IN THE C STRUCTURE TO UPDATE THE FLAGS IN THE CPU STATE STRUCTURE.
    def read_flags(self) -> int:
        """
        Reads the value of the flags register in the c structure file.
        :return: Value of the flags register
        :rtype: int
        """
        return int(self.lib.read_rflags())
    
    def read_trap_flag(self) -> int:
        """
        Reads the value of the trap flag in the c structure file.
        :return: Value of the trap flag
        :rtype: int
        """
        return int(self.lib.read_trap_flag())
    
    def set_trap_flag(self, value: int) -> None:
        """
        Sets the value of the trap flag in the c structure file.
        :param value: Value to set the trap flag to
        :type value: int
        """
        self.lib.set_trap_flag(value)
        