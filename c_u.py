from storage import Storage
from data_memory import Data_Memory
from segment_mapper import Segment_Mapper
import sys
import re
from alu import ALU

class _:
    """
    A simple CPU simulator with registers, program counter, and memory.
    Does not yet support memory addressing besides direct addressing.
    Does not support memory addressing modes for the first operand (destiny).
    64-bit architecture with basic arithmetic and logic instructions.
    Created mainly for educational purposes.
    """
    TEXT_START = 0x400000
    STACK_START = 0x7fffffffe000

    def __init__(self, memory: Data_Memory, loader: Segment_Mapper):
        """
        Initialize the CPU with registers, program counter, and memory.

        :param file_name: The name of the file with extension.
        :requires: file_name includes the .json extension && the file exists
        """
        self.rax :bytearray= bytearray(8)
        self.rbx :bytearray= bytearray(8)
        self.rcx :bytearray= bytearray(8)
        self.rdx :bytearray= bytearray(8)
        self.rdi :bytearray= bytearray(8)
        self.rsi :bytearray= bytearray(8)
        self.rbp :bytearray= bytearray(8)
        self.r8 :bytearray= bytearray(8)
        self.r9 :bytearray= bytearray(8)
        self.r10 :bytearray= bytearray(8)
        self.r11 :bytearray= bytearray(8)
        self.r12 :bytearray= bytearray(8)
        self.r13 :bytearray= bytearray(8)
        self.r14 :bytearray= bytearray(8)
        self.r15 :bytearray= bytearray(8)
        # make method that gets each registers
        

        self.rip :int= loader.rip  # Instruction pointer
        self.rsp :int= loader.stack_pointer  # Stack pointer
        self.flags :dict[str, int]= {
            'Z': 0,  # Zero flag
            'C': 0,  # Carry flag
            'S': 0,  # Sign flag
            'O': 0   # Overflow flag
        }
        
        # memory initialized with a Data_Memory object
        self.memory :Data_Memory= memory
        # Program Loader object pass to an instance
        self.loader :Process_Loader= loader
        
        self.text_segment :list[list[str]]= loader.memory_list
        self.rodata_segment :dict[str, str]= loader.rodata_segment
        self.data_segment :dict[str, str]= loader.data_segment
        self.bss_segment :dict[str, dict[str, int | list[int]]]= loader.bss_segment
        self.labels :dict[str, int]= loader.labels
        self.constants :dict[str, int]= loader.constants
                
        #sets of supported instructions and their operand counts
        self.valid_instructions :dict[str, int]= {
            'mov': 2,
            'halt': 0,
            'cmp': 2,
            'jmp': 1,
            'jb': 1,
            'jl': 1,
            'ja': 1,
            'jg': 1,
            'je': 1,
            'jne': 1,
            'jz': 1,
            'js': 1,
            'jc': 1,
            'jo': 1
        }
    
        self.halted :bool = False  # CPU halted state/finished execution
        self.instruction :str | None= None  # Current instruction being executed
        self.instruction_size :int | None= None
        self.operand1 :str | None= None
        self.operand2 :str | None= None


    def execute(self):
        """
        Main branch of the class.
        Should conduct execution through all stages needed of the execution.
        Will first fetch the line of the instruction which will verify it's syntax and semantics.
        Afterwards will call execution on the line.
        This cicle should only be stoped by either a verification error, a halt instruction or an exit syscall instruction.
        Producess side effects but returns nothing.
        """

        self.pc += 1  # Start execution from the first instruction
        while not self.halted:
            # Step 1: find the instruction and if it is valid
            size :str | None= self.fetch_instruction()   
            # Step 2: verify if the instruction syntax is correct 
            if not self.valid_operand_syntax(self.operand1) or not self.valid_operand_syntax(self.operand2):
                print(f"Instruction at {self.pc} has invalid operand syntax!")
                print("SyntaxError raised")
                sys.exit(-1)
            # Step 3: execute if all valid
            self.execute_instruction(size)
            if not self.halted:
                self.pc += 1


    def fetch_instruction(self) -> None | str:
        """
        Fetches the line of code that self.pc points towards.
        Tries to 'disassemble' the line separating each component of it and verify it's type/sence on the line.
        Does partial semantics verification.
        If there is not a line to verify exits the program on a error.
        """
        # Verify if the last instruction (syscall) gets out of bouds for this condition
        if self.pc >= len(self.text_segment):   
            print("NO MORE INSTRUCTIONS FOUND\nRaising ExitError...\nProgram exited with ForcedExitError.")
            self.halted = True
            return None
        
        instr:list[str] = self.text_segment[self.pc]
        # Verifies if the instruction present in the code line is valid/supported
        if instr[0] not in self.valid_instructions or instr[0] not in ALU.valid_instructions:   # Change condition when FPU unit is created
                print(f"INVALID INSTRUCTION AT LINE {self.pc}!\nHALTING EXECUTION")
                print("InvalidInstructionError raised")
                sys.exit(-1)
        else:
            self.instruction = instr[0]

        # Verifies if the code line has a correct length for the instruction passed 
        len_instr :int= len(instr)
        if len_instr != self.valid_instructions[self.instruction]+1 or len_instr != self.valid_instructions[self.instruction]+2:
            print(f"INVALID INSTRUCTION FORMAT AT LINE {self.pc}!\nHALTING EXECUTION")
            print("SyntaxError raised")
            sys.exit(-1)
        # Verifies if a size key word is present in the code line
        kword_index :int= self.get_size_kword_index(instr)
        if kword_index != -1:
            # If a size key word is present but not in the expected position exit and print an error message
            if kword_index != 1:
                print(f"INVALID INSTRUCTION FORMAT AT LINE {self.pc}!\nHALTING EXECUTION")
                print("SyntaxError raised")
                sys.exit(-1)
            # If the key word is in the correct position but the instruction does not allow for size specifiers exit and print an error message
            elif kword_index == 1 and self.instruction in ["jmp", "je", "jne", "jz", "js", "jc", "jo", "halt", "syscall", "xchg"]:
                print(f"INVALID INSTRUCTION FORMAT AT LINE {self.pc}!\nHALTING EXECUTION")
                print("SyntaxError raised")
                sys.exit(-1)

            # Attributes the operands to the respective instance of the class, accounting for the size of the instruction
            self.instruction_size = instr[1]
            self.operand1 = instr[2] if len(instr) == 3 or len(instr) == 4 else print(f"INVALID INSTRUCTION FORMAT AT LINE {self.pc}!\nHALTING EXECUTION") and sys.exit(-1, "SyntaxError raised")
            self.operand2 = instr[3] if len(instr) == 4 else print(f"INVALID INSTRUCTION FORMAT AT LINE {self.pc}!\nHALTING EXECUTION") and sys.exit(-1, "SyntaxError raised")
        else:
            self.operand1 = instr[1] if len(instr) == 2 or len(instr) == 3 else None
            self.operand2 = instr[2] if len(instr) == 3 else None
            self.instruction_size = None
        return instr[kword_index] if kword_index != -1 else None

    def execute_instruction(self, size):
        """
        Instruction distribution method responsible for ensuring the instruction already verified is conducted to the correct method attributed to it.
        Still verifies if the operands are compatible with one-another and with the instruction and if it's size is sepecified in the instruction (if needed).
        The instruction should alway be led to a method because it was already verified it's compatibility.
        """

        # Step 2.5: verify if the operands are compatible with the instruction and themselves
        try:
            if not self.verify_size_compatibility(self.operand1, self.operand2, size):
                ### To be verified
                print(f"INVALID OPERAND TYPE COMBINATION FOR INSTRUCTION AT LINE {self.pc}.\nHALTING EXECUTION")
                print("OperandsSizeMismatchError raised")
                sys.exit(-1)
        except TypeError:
            print(f"NO SIZE SPECIFIER EXPLICITED FOR INSTRUCTION AT LINE {self.pc}.\nHALTING EXECUTION")
            print("MissingSize raised")
            sys.exit(-1)
        except type:
            print(f"INVALID FIRST OPERANT TYPE AT LINE {self.pc}.\nHALTING EXECUTION")
            print("OperandTypeError raised")
            sys.exit(-1)
        except SyntaxError:
            print(f"INVALID SIZE SPECIFIER FOR THIS OPERATION AT LINE {self.pc}.\nHALTING EXECUTION")
            print("InstructionSizeError raised")
            sys.exit(-1)
        # Step 3: Attribute the coded instruction to the method to use
        if self.instruction == 'halt':
            self.halted = True
        elif self.instruction == 'mov':
            self.mov()
        elif self.instruction == 'cmp':
            self.cmp(self.operand1, self.operand2)
        elif self.instruction == 'jmp':
            self.jmp()
        elif self.instruction in {'je', 'jne', 'jz', 'js', 'jc', 'jo'}:
            self.conditional_jump(self.instruction)
        elif self.instruction[0].lower() == "syscall":
            self.syscall_decode()
        # Alu instructions
        # elif self.instruction in ALU.valid_instructions:
        #     alu = ALU(self.instruction, self.operand1, self.operand2, self.flags)
        #     alu.attribute_instruction()
        #     self.set_from_functional_unit(alu)
        # Fpu instructions
        

    def valid_operand_syntax(self, operand):
        """
        Verification for operand sintax
        
        :param operand: full operand in verification
        """
        if operand is None:
            # To account for calls on unintended operands (op2 when it does not exist)
            return True
        elif (not operand.startswith('[') and operand.endswith(']')) or (operand.startswith('[') and not operand.endswith(']')) or operand.startswith(']') or operand.endswith('[') or (not operand.startswith("[") and not operand.endswith("]") and ("+" in operand or "-" in operand)):
            return False
        return True
    

    def verify_size_compatibility(self, op1, op2, size):
        """
        Multi-instruction verification for size compatibility between operands.
        Should be paired with specific compatibility requirenments for each instruction (if needed).
        
        :param op1: first operand of the instruction
        :param op2: second operand of the instruction
        :param size: key word specifier for the operations size ['None', 'byte', 'word', 'dword', 'qword']
        """
        
        size_map = {
            'byte': 8,
            'word': 16,
            'dword': 32,
            'qword': 64
        }
        size = int(size_map[size]) if size != None else size

        if self.is_immediate(op1) or self.is_constant(op1):
            raise ... 
        elif self.is_immediate(op2) or self.is_constant(op2):
            return True
        elif self.is_memory_addressing(op1):
            if size == None and not self.is_register(op2) and self.instruction not in ['push', 'pop']:  # Add more instruction
                raise TypeError
            else:
                if op2 != None:
                    if self.get_size(op1) != size:
                        raise SyntaxError
                    elif self.is_memory_addressing(op2):
                        # if self.get_size(op2) <= self.get_size(op1) and self.instruction in ['movsx', 'movzx']: # Complement with fpu instructions
                        #     return True
                        # elif self.get_size(op2) != self.get_size(op1):
                        #     return False
                        return False    # Both operands being memory addressing is not allowed on any operation suported currently
                        
                    elif self.is_address(op2):
                        # if 2**(self.get_size(op1)) >= self.get_address(op2):
                        #     return True
                        # else:
                        #     return False
                        return False    # Both operands being memory addressing is not allowed on any operation suported currently
                        
                    elif self.is_register(op2):
                        if self.get_size(op2) <= self.get_size(op1) and self.instruction in ['movsx', 'movzx']: # Complement with fpu instructions
                            return True
                        elif self.get_size(op2) != self.get_size(op1):
                            raise SyntaxError
                    else:
                        return False    # Should never reach this point
                else:
                    # Will always output false or never reach here if the instruction is not one of those specified
                    # Just to make expansion easier
                    if size == None and self.instruction not in ['push', 'pop']:
                        return False
                    if self.get_size(op1) != size and size != None:
                        raise SyntaxError
                    else:
                        return True
                
        elif self.is_register(op1):
            if op2 != None:                
                if self.is_address(op2):
                    if size != None and size != self.get_size(op1):
                        return False
                    elif 2**(self.get_size(op1)) >= self.get_address(op2):
                        return True
                    else:
                        return False

                elif self.is_memory_addressing(op2) or self.is_register(op2):
                    if size != None and size != self.get_size(op1):
                        return False
                    elif self.get_size(op2) <= self.get_size(op1) and self.instruction in ['movsx', 'movzx']: # Complement with fpu instructions
                        return True
                    elif self.get_size(op1) != self.get_size(op2):
                        return False
                    else:
                        return True
            if op2 == None:
                return True
            
    
    def get_size_kword_index(instruction: list[str]):
        """
        Verifies if a size specifier is on the istruction passed to this method.
        Will return -1 if no size specifier is found or the index where it was found.
        
        :param instruction: Line of code passed as a list of string
        :type instruction: list[str]
        """
        for i in range(len(instruction)):
            if instruction[i] in ['byte', 'word', 'dword', 'qword']:
                return i
        return -1
            


    def set_from_functional_unit(self, unit):
        """
        Sets the correct flag values after the execution of a code line entered a funtuional unit outside this class.

        :param unit: Funtional Unit responsible for the potential alteration of the flags state.
        """
        self.flags = unit.flags
        self.operand1 = unit.op1
        self.operand2 = unit.op2
        self.halted = unit.halted

    def select_operand(self, operand):
        # Registers
        registers_map = {
            'rax': ('_64', self.rax), 'eax': ('_32', self.rax), 'ax': ('_16', self.rax), 'al': ('L8', self.rax), 'ah': ('H8', self.rax),
            'rbx': ('_64', self.rbx), 'ebx': ('_32', self.rbx), 'bx': ('_16', self.rbx), 'bl': ('L8', self.rbx), 'bh': ('H8', self.rbx),
            'rcx': ('_64', self.rcx), 'ecx': ('_32', self.rcx), 'cx': ('_16', self.rcx), 'cl': ('L8', self.rcx), 'ch': ('H8', self.rcx),
            'rdx': ('_64', self.rdx), 'edx': ('_32', self.rdx), 'dx': ('_16', self.rdx), 'dl': ('L8', self.rdx), 'dh': ('H8', self.rdx),
            'rsi': ('_64', self.rsi), 'esi': ('_32', self.rsi), 'si': ('_16', self.rsi), 'sil': ('L8', self.rsi),
            'rdi': ('_64', self.rdi), 'edi': ('_32', self.rdi), 'di': ('_16', self.rdi), 'dil': ('L8', self.rdi),
            'rsp': ('_64', self.rsp), 'esp': ('_32', self.rsp), 'sp': ('_16', self.rsp),
            'rbp': ('_64', self.rbp), 'ebp': ('_32', self.rbp), 'bp': ('_16', self.rbp),
            'r8': ('_64', self.r8), 'r8d': ('_32', self.r8), 'r8w': ('_16', self.r8), 'r8b': ('L8', self.r8),
            'r9': ('_64', self.r9), 'r9d': ('_32', self.r9), 'r9w': ('_16', self.r9), 'r9b': ('L8', self.r9),
            'r10': ('_64', self.r10), 'r10d': ('_32', self.r10), 'r10w': ('_16', self.r10), 'r10b': ('L8', self.r10),
            'r11': ('_64', self.r11), 'r11d': ('_32', self.r11), 'r11w': ('_16', self.r11), 'r11b': ('L8', self.r11),
            'r12': ('_64', self.r12), 'r12d': ('_32', self.r12), 'r12w': ('_16', self.r12), 'r12b': ('L8', self.r12),
            'r13': ('_64', self.r13), 'r13d': ('_32', self.r13), 'r13w': ('_16', self.r13), 'r13b': ('L8', self.r13),
            'r14': ('_64', self.r14), 'r14d': ('_32', self.r14), 'r14w': ('_16', self.r14), 'r14b': ('L8', self.r14),
            'r15': ('_64', self.r15), 'r15d': ('_32', self.r15), 'r15w': ('_16', self.r15), 'r15b': ('L8', self.r15),
        }

        if operand in registers_map:
            attr, reg = registers_map[operand]
            return (
                lambda: getattr(reg, attr),
                lambda v: setattr(reg, attr, v)
            )
        # Memory
        elif operand.startswith('[') and operand.endswith(']'):
            var_name = operand[1:-1]
            return lambda: self.memory.read(var_name), lambda v: self.memory.write(var_name, v)
        # Immediate
        elif self.is_immediate(operand):
            if operand.startswith("0x") or operand.endswith("h"):
                value = int(operand, 16)
            elif operand.startswith("0b") or operand.endswith("b"):
                value = int(operand, 2) 
            elif operand.startswith("0o") or operand.endswith("o"):
                value = int(operand, 8)
            else:
                value = int(operand)
            return value
        # Addressing
        elif self.is_address(operand):
            return self.get_address(operand)
        # Constants
        elif self.is_constant(operand):
            return self.constants[operand]
        else:   
            print(f"INVALID OPERAND TYPE {operand}\n HALTING EXECUTION")
            sys.exit(-1, "TypeError raised")

    #re-do
    def get_address(self, operand):
        if operand.startswith('[') and operand.endswith(']'):
            operand = operand.strip("[]")
        if "+" in operand:
            operand, sum = operand.split("+")
            return self.get_address(operand) + int(sum)
        elif "-" in operand:
            operand, sub = operand.split("-")
            return self.get_address(operand) - int(sub)
        if operand in self.rodata_segment:
            return self.rodata_segment[operand]['address'][0]
        elif operand in self.data_segment:
            return self.rodata_segment[operand]['address'][0]
        elif operand in self.bss_segment:
            return self.rodata_segment[operand]['address'][0]
    
    @staticmethod                
    def is_register(operand):
        """
        Checks if the operand is a register.
        :return: True if the operand is a register, False otherwise.
        :rtype: bool
        """
        registers = [
            'rax', 'eax', 'ax', 'al', 'ah',
            'rbx', 'ebx', 'bx', 'bl', 'bh',
            'rcx', 'ecx', 'cx', 'cl', 'ch',
            'rdx', 'edx', 'dx', 'dl', 'dh',
            'rsi', 'esi', 'si', 'sil',
            'rdi', 'edi', 'di', 'dil',
            'rsp', 'esp', 'sp',
            'rbp', 'ebp', 'bp',
            'r8', 'r8d', 'r8w', 'r8b',
            'r9', 'r9d', 'r9w', 'r9b',
            'r10', 'r10d', 'r10w', 'r10b',
            'r11', 'r11d', 'r11w', 'r11b',
            'r12', 'r12d', 'r12w', 'r12b',
            'r13', 'r13d', 'r13w', 'r13b',
            'r14', 'r14d', 'r14w', 'r14b',
            'r15', 'r15d', 'r15w',  'r15b'
        ]
        return operand in registers
    
    
    def is_address(self, operand):
        return "[" not in operand and self.op_is_label(operand)
    

    def is_memory_addressing(self, operand):
        if "/" in operand:
            raise SyntaxError
        try:
            return self.is_direct_memory_addressing(operand) or self.is_base_memory(operand) or self.is_indexed_memory_addressing(operand)
        except ValueError(operand):
            print(f"INVALID OPERAND SYNTAX {operand}\n HALTING EXECUTION")
            sys.exit(-1, "SyntaxError raised")


    def is_base_memory(self, operand):
        """
        Verifies if an operand is of the base memory addressing type.
        """
        if operand.startswith('[') and operand.endswith(']'):
            operand = operand.strip('[]')
            if "*" in operand:
                return False
            else:
                operand = re.split(r'[+-]', operand)

                registers = 0
                for i in range(len(operand)):
                    if self.is_register(operand[i]):
                        registers += 1
                        if registers > 1:
                            raise ValueError
                if registers == 0:
                    return False
                else: 
                    return True
        else:
            return False
    

    def is_direct_memory_addressing(self, operand):
        """
        Verifies if an operand is of the direct memory addressing type.
        """
        if operand.startswith('[') and operand.endswith(']'):
            operand = operand.strip("[]")
            if  "*" in operand:
                return False
            else:
                operand = re.split(r'[+-]', operand)
                
                labels = 0
                for i in range(len(operand)):
                    if not self.is_immediate(operand[i]) and not self.op_is_label(operand[i]) and not self.is_constant(operand[i]):
                        return False
                    elif self.op_is_label(operand[i]):
                        labels += 1
                        if labels > 1:
                            raise ValueError
                
                if labels == 0:
                    raise ValueError
                else:
                    return True
        else:
            return False
    
    def is_indexed_memory_addressing(self, operand):
        if operand.startswith('[') and operand.endswith(']'):
            operand = operand-lstrip("[").rstrip("]")
            if "[" in operand or "]" in operand:
                raise ValueError
            elif "*" not in operand:
                return False
            else:
                operand = re.split(r'[+-]', operand)
                
                registers = 0
                labels = 0
                for i in range(len(operand)):
                    if "*" in operand[i]:
                        # Needs one scale as an imidiate value with a correct size
                        imidiate = 0
                        # Needs a register as an index
                        register2 = 0
                        ops = operand[i].split("*")
                        for j in range(2):
                            if self.is_immediate(ops[j]):
                                imidiate += 1
                            elif self.is_register(ops[j]):
                                registers += 1
                            else:
                                raise ValueError
                        
                        if imidiate <= 1:
                            raise ValueError
                    else:
                        if self.is_register(operand[i]):
                                registers += 1
                                if registers > 2:
                                    raise ValueError
                        elif self.op_is_label(operand[i]):
                            labels += 1
                            if labels > 1:
                                raise ValueError
                if registers <= 1:
                    raise ValueError
                else:
                    return True
        else:
            return False

    def op_is_label(self, operand):
        """
        Verifies if the operand is in any of the data sections
        
        :param operand: Operand being verified for its existance in any of the data sections
        """
        return operand in self.rodata_segment or operand in self.data_segment or operand in self.bss_segment
    

    def is_immediate(self, operand):
        return isinstance(operand, int) or (isinstance(operand.strip('-'), int) or (operand.startswith("0x") or operand.endswith("h")) or (operand.startswith("0b") or operand.endswith("b")) or (operand.startswith("0o") or operand.endswith("o")))
    
    def is_constant(self, operand):
        return operand in self.constants
    

    def get_size(self, operand):
            """
            Returns the size of the operand in bits.
            :return: Size of the operand in bits.
            :rtype: int
            """
            if self.is_register(operand):
                if operand in ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rsp', 'rbp', 'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']:
                    return 64
                elif operand in ['eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'esp', 'ebp', 'r8d', 'r9d', 'r10d', 'r11d', 'r12d', 'r13d', 'r14d', 'r15d']:
                    return 32
                elif operand in ['ax', 'bx', 'cx', 'dx', 'si', 'di', 'sp', 'bp',  'r8w', 'r9w', 'r10w', 'r11w', 'r12w', 'r13w', 'r14w', 'r15w']:
                    return 16
                elif operand in ['al', 'ah', 'bl', 'bh', 'cl', 'ch', 'dl', 'dh',  'sil', 'dil',  'r8b', 'r9b', 'r10b', 'r11b', 'r12b', 'r13b', 'r14b',  'r15b']:
                    return 8
            else:
                # Rever
                if self.is_memory_addressing(operand):
                        operand = operand.strip("[]").split("+")[0] if "+" in operand else operand.strip("[]").split("-")[0] if "-" in operand else operand
                        return self.return_variable_size(operand)
                
                elif self.is_address(operand):
                        # Meaning its an address
                        return 64
                elif self.is_immediate(operand) or self.is_constant(operand):
                        # Immediate values and constants are treated as 64-bit
                        return None
                else:
                    print(f"Invalid operand or unsupported: {operand}")
                    sys.exit(-1, "Program forced exit on SemanticsError")


    def return_variable_size(self, operand):
        if operand in self.data_segment:
            size_str = self.data_segment[operand]['size']
            if size_str == 'db':
                return 8
            elif size_str == 'dw':
                return 16
            elif size_str == 'dd':
                return 32
            elif size_str == 'dq':
                return 64
        elif operand in self.bss_segment:
            size_str = self.bss_segment[operand]['size']
            if size_str == 'resb':
                return 8
            elif size_str == 'resw':
                return 16
            elif size_str == 'resd':
                return 32
            elif size_str == 'resq':
                return 64
        elif operand in self.rodata_segment:
            size_str = self.rodata_segment[operand]['size']
            if size_str == 'db':
                return 8
            elif size_str == 'dw':
                return 16
            elif size_str == 'dd':
                return 32
            elif size_str == 'dq':
                return 64
        else:
            print(f"Size specifier not found for variable {operand}.")
            sys.exit(-1, "Program forced exit on SemanticsError")                      
        

    def mov(self):
        if self.is_immediate(self.operand1) or self.operand1 in self.constants:
            print("INVALID MOV OPERATION: DESTINY OPERAND CANNOT BE IMMEDIATE VALUE OR A CONSTANT\nHALTING EXECUTION")
            sys.exit(-1, "ImmediateValueError raised")
        if self.is_memory_addressing(self.operand1) and self.is_memory_addressing(self.operand2):
            print("INVALID MOV OPERATION: BOTH OPERANDS CANNOT BE MEMORY ADDRESSED\nHALTING EXECUTION")
            sys.exit(-1, "MemoryAddressingError raised")

        if (not self.verify_size_compatibility(self.operand1, self.operand2)):
            print("INVALID MOV OPERATION: OPERANDS SIZE MISMATCH\nHALTING EXECUTION")
            sys.exit(-1, "SizeMismatchError raised")
        op1_get, op1_set = self.select_operand(self.operand1)
        op2_get, _ = self.select_operand(self.operand2)
        op1_set(op2_get())
        
    # Jump methods
    def jmp(self):
        label = self.operand1
        if label in self.labels:
            self.pc = self.labels[label]
        else:
            print(f"Undefined label: {label}")
            sys.exit(-1, "UndefinedLabelError raised")

    def conditional_jump(self, instr):
        # Simplified conditional jump using flags
        label = self.instruction[1]
        condition_map = {
            'je': lambda: self.flags['Z'] == 1,
            'jne': lambda: self.flags['Z'] == 0,
            'jz': lambda: self.flags['Z'] == 1,
            'js': lambda: self.flags['S'] == 1,
            'jc': lambda: self.flags['C'] == 1,
            'jo': lambda: self.flags['O'] == 1
        }
        if condition_map[instr]():
            if label in self.labels:
                self.pc = self.labels[label]
            else:
                print(f"Undefined label: {label}")
                sys.exit(-1, "UndefinedLabelError raised")

    def cmp(self, op1, op2):
        op1_get, _ = self.select_operand(op1)
        op2_get, _ = self.select_operand(op2)
        result = op1_get() - op2_get()
        self.flags['Z'] = int(result == 0)
        self.flags['S'] = int(result*op1_get < 0)

    def syscall_decode(self):
        if self.rax._64 == 60 and self.rdi._64 == 0:  # Exit syscall
            print("Program exited successfully.")
            sys.exit(0)
        elif self.rax._64 == 1 and self.rdi._64 == 1 and int(self.rdx._64): # Print syscall
            print(self.rsi._64[:self.rdx._64 -1])
        else:
            print(f"Unsupported syscall with rax={self.rax}. Halting execution.")
            self.halted = True
    
    def verify_operation(self, instr, op1, op2):
        # Verifies if instruction is valid
        if instr not in self.valid_instructions:
            print(f"Instruction {instr} is invalid!")
            sys.exit(-1, "InvalidInstructionError raised")

        # Verifies if the number of operands is correct
        expected_operands = self.valid_instructions[instr]
        actual_operands = 0
        if op1 is not None:
            actual_operands += 1
        if op2 is not None:
            actual_operands += 1
        if expected_operands != actual_operands:
            print(f"Instruction {instr} expects {expected_operands} operands, but got {actual_operands}!")
            sys.exit(-1, "OperandCountError raised")

        # Verifies size compatibility
        if (not self.verify_size_compatibility(op1, op2)) and self.is_register(op1) and self.is_register(op2):
            print(f"Instruction {instr} has incompatible operand sizes!")
            sys.exit(-1, "SizeMismatchError raised")


# Needs to be added to the valid instructions
    def call(self, operand1):
        if operand1 not in self.labels:
            print(f"INVALID LABEL {self.instruction} FOR 'call' OPERATION.\nHALTING EXECUTION")
            sys.exit(-1, "Program forced exit on SemanticsError")
        else:
            self.memory.push(self.pc +1)
            self.pc = self.labels[operand1]
        
    def ret(self):
        self.pc = self.memory.pop()
    

    # def lea(self, operand1, operand2):
    #     #TODO