import sys
import re
from storage import Storage
from data_memory import Data_Memory
from segment_mapper import Segment_Mapper
from my_types import DataSectionInfo, BssSectionInfo, LabelMap, ConstantMap, FU
from data_path import Data_Path
from alu import ALU
from fpu import FPU


class Control_Unit:

    SIZE_DIRECTIVES = {
        'byte': 1, 'word': 2, 'dword': 4, 'qword': 8
    }

    MASKS_DIRECTIVES = {
        'byte': 0xFF, 'word': 0xFFFF, 'dword': 0xFFFFFFFF, 'qword': 0xFFFFFFFFFFFFFFFF
    }


    COMPONENTS_ADDRESSING_PATTERN = r'(0x[\da-fA-F]+|[a-zA-Z_][a-zA-Z0-9_]*|\d+)'
    GENERAL_PURPOSE_REGISTERS_PATTERN = r'([er]?[abcd]x|[er]?[sb]p|[er]?[sd]i|[er]?ip|r[89][bdlw]?|r1[0-5][bdlw]?|[abcd][hl])'
    FPU_REGISTERS_PATTERN = r'(ymm[0-9]|xmm[0-9]|ymm1[0-5]|xmm1[0-5])'
    NUMBER_REPRESENTATION_PATTERN = r'(0x[\da-fA-F]+|\d[\da-fA-F]*h|0b[01]+|[01]+b|0d\d+|[-+]?\d+d|[0-7]+[oq]|[-+]?\d+)'
    WORD_OR_CHARACTERS_PATTERN = r'(\".*?\"|\'.*?\')'
    IMMEDIATE_VALUE_PATTERN = fr'({NUMBER_REPRESENTATION_PATTERN}|{WORD_OR_CHARACTERS_PATTERN})'
    REGISTER_PATTERN = fr'{GENERAL_PURPOSE_REGISTERS_PATTERN}|{FPU_REGISTERS_PATTERN}'
    CONSTANTS_AND_LABELS_PATTERN = r'\b[a-zA-Z_]\w*\b'
    DIRECT_AND_BASE_ADDRESSING_PATTERN = fr'^\[(?:\s*){COMPONENTS_ADDRESSING_PATTERN}(?:\s)*([\+\-](?:\s)*{COMPONENTS_ADDRESSING_PATTERN})*(?:\s)*\]$'
    INDEXED_ADDRESSING_PATTERN = fr'^\[(?:\s*){COMPONENTS_ADDRESSING_PATTERN}(?:\s)*([\+\-\*](?:\s)*{COMPONENTS_ADDRESSING_PATTERN})*(?:\s)*\]$'
    MEMORY_ADDRESSING_PATTERN = fr'^{INDEXED_ADDRESSING_PATTERN}|{DIRECT_AND_BASE_ADDRESSING_PATTERN}$'
    OPERAND_PATTERN = fr'{MEMORY_ADDRESSING_PATTERN}|{REGISTER_PATTERN}|{IMMEDIATE_VALUE_PATTERN}{CONSTANTS_AND_LABELS_PATTERN}'
    


    def __init__(self, memory: Data_Memory, loader: Segment_Mapper, validation_file_name: str) -> None:
        # Initialize Control Unit with memory, segment mapper, funtional units and registers (general purpose, fpu and flags)
        self.memory: Data_Memory = memory
        self.loader: Segment_Mapper = loader
        self.data_path: Data_Path = Data_Path()
        self.alu: ALU = ALU()
        self.fpu: FPU = FPU()     

        self.registers: dict[str, int] = {
            # General Purpose Registers (64-bit Integers)
            "rax": 0, "rbx": 0, "rcx": 0, "rdx": 0,
            "rsi": 0, "rdi": 0, "rbp": 0, "rsp": loader.stack_pointer,
            "r8": 0,  "r9": 0,  "r10": 0, "r11": 0,
            "r12": 0, "r13": 0, "r14": 0, "r15": 0
        }

        # xmm registers are treated as the lower 16 bytes of each respective ymm register
        self.ymm: dict[str, bytearray] = {
            f"ymm{i}": bytearray(32) for i in range(16)
        }

        # Instruction Pointer
        self.rip: int = loader.rip  # Instruction Pointer initialized from Segment Mapper
        # Flag state holders
        self.flags: dict[str, int] = {
            'ZF': 0,  # Zero Flag
            'SF': 0,  # Sign Flag
            'OF': 0,  # Overflow Flag
            'CF': 0   # Carry Flag
        }

        # Gets the parsed sections from segment_mapper
        self.text_section: list[list[str]] = loader.memory_list
        self.rodata_section: DataSectionInfo = loader.rodata_segment
        self.data_section: DataSectionInfo = loader.data_segment
        self.bss_section: BssSectionInfo = loader.bss_segment
        self.labels: LabelMap = loader.labels
        self.constants: ConstantMap = loader.constants

        # Helper instances for the execution
        self.halted: bool = False
        self.finished: bool = False
        self.current_fu: str = "cpu" # (cpu/data_path/alu/fpu)
        self.current_instruction: str | None = None
        self.op1: str | None = None
        self.op1_size: int = 0  # size must be 0 if self.op1 = None
        self.op1_value: bytes = b"" # value must be 0 if self.op1 = None
        self.op1_address: int | None = None # address must be None if self.op1 is not a memory operand
        self.op1_type: str | None = None # type must be None if self.op1 = None, otherwise it must be either 'direct memory'/'base memory'/'indexed memory'/'address'/'register'/'constant'/'immediate'
        self.op2: str | None = None
        self.op2_size: int = 0  # size must be 0 if self.op2 = None
        self.op2_value: bytes = b"" # value must be 0 if self.op2 = None
        self.op2_address: int | None = None # address must be None if self.op2 is not a memory operand
        self.op2_type: str | None = None # type must be None if self.op2 = None, otherwise it must be either 'direct memory'/'base memory'/'indexed memory'/'address'/'register'/'constant'/'immediate'
        self.valid_instructions: dict[str, dict[str, int]] = Storage.read_valid_instructions(validation_file_name)


    #---------------------------------
    # Cicle execution methods
    #---------------------------------

    def run(self) -> None:
        self.rip += 1
        # Improve this loop to enable debugging features
        while not self.halted or not self.finished:
            try:
                self.step()
            except Exception as e:
                print(f"CPU Exception at line {self.rip}: {e}")
                self.finished = True
    
    def step(self) -> None:
        try:
            # 1. Gets the instruction, operands and funtional unit in use and verifies it's compatibility it the operator count of the instruction
            self.fetch()
            # current_instruction will only be 'None' if rip points to a label in .text (which should be skiped)
            if self.current_instruction != None:
                # 2. Verifies if the instruction-operand set is valid and triggers the execution of the instruction in the respective funtional unit
                self.execute(self.current_instruction, self.op1_value, self.op1_address, self.op1_type, self.op1_size, self.op2_value, self.op2_address, self.op2_type, self.op2_size, self.flags)
                # 4. Verifies if the execution generated any type of side effects of flags and halted state and updates them
                self.validate_execution_state()
                # 5. Increases rip 
            self.rip += 1
        except ValueError as e:
            print(e)
            sys.exit(1) 

    def fetch(self) -> None:
        """
        Fetches the current instruction and its operands from the text section based on the instruction pointer (RIP).\n
        Sets the current instruction and current funtional unit in use and validates and sets the operands and its size.
        Raises a ValueError if the instruction is invalid or if the operands are invalid.        
        
        :return: None
        :rtype: None
        :raises ValueError: If the instruction is invalid or if the operands are invalid.
        """
        line: list[str] = self.text_section[self.rip]

        # Verifies if the line is a label declaration and skips it if so
        if len(line) == 1 and line[0] in self.labels:
            return 
        # Verifies if the line is an instruction and sets the instruction, f.u. in use and operand info needed for execution (size, type, value, address)
        elif self.is_valid_instruction(line[0]):
            self.curretent_instruction = line[0]

            # This block might raise an exception if it ran into bad syntax or impossible operations/operands
            try:
                self.validate_operands(line)
                self.set_operand_type(line)
                self.set_operand_value_and_address(line)
            except ValueError as e:
                print(f"Error at line {self.rip}: {e}")
                self.current_instruction = None
                self.finished = True

            # Verifies if the number of operands registered are compatible with the instructions documentation in the valid_instructions json file    
            if self.valid_operand_count():
                return
            else:
                # If incompatible reset all info to a Null value and raise an exception
                self.set_operand("both", None, 0)
                raise ValueError(f"INVALID OPERAND COUNT FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
        
        # If the instruction wasn't found, raise an excpetion
        else:
            raise ValueError(f"INVALID INSTRUCTION AT LINE {self.rip}!")
    
    def execute(self, instruction: str, op1_value: bytes, op1_address: int | None, op1_type: str | None, op1_size: int, op2_value: bytes, op2_address: int | None, op2_type: str | None, op2_size: int, flags: dict[str, int]) -> None:
        """
        Transfers executions to the class with the funtional unit responsible for the instaruction
        in the current instruction in this class's respective instance
        and retrives the result of the operation if any and the flags state that resulted from the operation.
        
        """
        if self.current_fu == "cpu":
            if self.current_instruction == "syscall":
                self.syscall()
            elif self.curretent_instruction == "call":
                self.call()
        else:
            current_fu: FU = self.get_current_fu()
            current_fu.load_values(instruction, op1_value, op1_address, op1_type, op1_size, op2_value, op2_address, op2_type, op2_size, flags)
            current_fu.execute()
            if current_fu.result != b'0':
                self.set_result(...)

    def validate_execution_state(self) -> None:
        """
        Docstring for validate_execution_state
        
        :param self: Description
        """
        ...

    #-----------------------------------
    # General validation methods
    #-----------------------------------

    def is_valid_instruction(self, instruction: str) -> bool:
        """
        Verifies if a given instruction is supported by the program and if so sets the current funtional unit in use.\n
        Enables syscalls and funtion calls methods taken care by this class.

        :param instruction: Instruction in verification
        :type instruction: str
        :return: True if the instruction is present in the valid_instructions.json file
        :rtype: bool
        """
        for funtional_units in self.valid_instructions.keys():
            if instruction in self.valid_instructions[funtional_units]:
                self.current_fu = funtional_units
                return True
            elif instruction == "syscall":
                self.current_fu = "cpu"
                return True
            elif instruction == "call":
                self.current_fu = "cpu"
                return True
        return False
    
    def validate_operands(self, line: list[str]) -> None:
        """
        Validates the operands of the current instruction based on the number of operands provided in the line.\n
        Sets the operand attributes accordingly or raises a ValueError if the operands are invalid.

        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises ValueError: If the operands are invalid for the current instruction, including invalid syntax or invalid operand sets
        """
        instruction_length: int = len(line)

        if instruction_length == 1:
        # One element code line means a no explicit operand so set both to a Null value
            try:
                self.set_operand("both", None, 0)
                return
            except ValueError as e:
                raise ValueError(e)
            
        elif instruction_length > 5:
            # instructions with more than 5 elements means it is most definitely wrong syntax
            try:
                self.set_operand("both", None, 0)   # Will never return a ValueError
            except ValueError as e:
                print(e)
                sys.exit(...)
            raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
        
        else:
            # If none of the above cases are triggered try to parse the operands and sizes
            try:
                operand_info: list[str] = self.get_operand_info(line[1:]) 
                self.parse_operand_info(operand_info)
            except ValueError as e:
                print(e)
                sys.exit(109101)
            except SyntaxError as e:
                print(e)
                sys.exit(...)
    
    def valid_operand_count(self) -> bool:
        """
        Verifies if the current operand count is valid for the current instruction

        :return: True if the current operand count is valid for the current instruction
        :rtype: bool
        """
        # Gets the number of expected arguiments of an instruction based on the valid_instructions.json file
        expected_operand_count: int = self.valid_instructions[self.current_fu][self.curretent_instruction]
        # Gets the number of operands in use for for the current instruction   
        actual_operand_count: int = 0
        if self.op1 != None:
            actual_operand_count += 1
        if self.op2 != None:
            actual_operand_count += 1
        # Returns if they both match (valid operand count)    
        return expected_operand_count == actual_operand_count        

    #---------------------------
    # Operand setting methods
    #---------------------------

    def set_operand(self, operand: str, expression: str | None, size: int) -> None:
        """
        Attribute a declaration expression and a size to the respective attributes  of the specified operand.

        :param operand: Expression for which operand(s) to update (both/op1/op2)
        :type operand: str
        :param expression: Unaltered expression used to refer to the operand in the line of code
        :type expression: str | None
        :param size: Number of bytes used by the operand(s)
        :type size: int
        :raises ValueError: If an invalid operand identifier is used
        """
        if operand == "both":
            self.op1 = expression
            self.op1_size = size
            self.op2 = expression
            self.op2_size = size
        elif operand == "op1":
            self.op1 = expression
            self.op1_size = size
        elif operand == "op2":
            self.op2 = expression
            self.op2_size = size
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")
        
    def set_operand_type(self, line: list[str]) -> None:
        """
        Attribute a type to the operand type attributes based on the operand expression
        
        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises ValueError: If an invalid label is found during operand type determination
        """
        # For each of the attributes that hold the operands expression, if they are not None get their type
        if self.op1 != None:
            try:
                self.op1_type = self.determine_operand_type(self.op1)
            except ValueError as e:
                raise ValueError(e)
        if self.op2 != None:
            try:
                self.op2_type = self.determine_operand_type(self.op2)
            except ValueError as e:
                raise ValueError(e)
    
    def set_operand_value_and_address(self, line: list[str]) -> None:
        """
        Attribute a value and address to the operand value and address attributes based on the operand expression and type
        
        :param line: List of strings representing the instruction line
        :type line: list[str]
        :raises ValueError: If an invalid label is found during operand value or address determination
        """
        # For each of the attributes that hold the operands expression, if they are not None get their address (if it is a memory reference) and value
        operation_size: int = self.get_operation_size()
        if self.op1 != None:
            try:
                op1_info: tuple[bytes, int | None]= self.determine_operand_value_and_address(self.op1, self.op1_type, self.op1_size, operation_size, self.memory)
                self.set_operand_value("op1", op1_info[0])  
                self.set_operand_address("op1", op1_info[1])
            except ValueError as e:
                raise ValueError(e)
        if self.op2 != None:
            try:
                op2_info: tuple[bytes, int | None]= self.determine_operand_value_and_address(self.op2, self.op2_type, self.op1_size, operation_size, self.memory)
                self.set_operand_value("op2", op2_info[0])      
                self.set_operand_address("op2", op2_info[1])    
            except ValueError as e:
                raise ValueError(e)

    def set_operand_value(self, operand:str, value: bytes) -> None:
        """
        Attribute a value to the operand value attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param value: Value of the operand (must be calculated)
        :type value: int
        :raises ValueError: If an invalid operand identifier is used
        :raises SyntaxError: If any operator value with an invalid type (non byte) is passed to the execution of this method
        """
        if not isinstance(value, bytes):
            raise SyntaxError("\n   Software bug detected.\nInvalid type for operator value. Values should always be bytes!")
        if operand == "both":
            self.op1_value = value
            self.op2_value = value
        elif operand == "op1":
            self.op1_value = value
        elif operand == "op2":
            self.op2_value = value
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")
        
    def set_operand_address(self, operand:str, address: int | None) -> None:
        """
        Attribute an address to the operand address attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param address: Address of the operand (must be calculated, None if not a memory operand)
        :type address: int | None
        :raises ValueError: If an invalid operand identifier is used
        """
        if operand == "both":
            self.op1_address = address
            self.op2_address = address
        elif operand == "op1":
            self.op1_address = address
        elif operand == "op2":
            self.op2_address = address
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")

    #------------------------
    # Operand Determination
    #------------------------

    def determine_operand_type(self, operand: str) -> str:
        """
        Determines the operand type based on its expression by going through the possible operand types and verifying if the expression matches any of them.        

        :param operand: Expression for the operand to determine the type
        :type operand: str
        :return: Description of the operand type (either 'direct memory'/'base memory'/'indexed memory'/'address'/'register'/'constant'/'immediate')
        :rtype: str
        :raises ValueError: If an invalid label is found during operand type determination or if the operand does not match any valid type
        """
        try:
            if self.verify_memory_addressing(operand, self.DIRECT_AND_BASE_ADDRESSING_PATTERN):
                return 'direct memory'
            elif self.verify_memory_addressing(operand,self.DIRECT_AND_BASE_ADDRESSING_PATTERN, 2):
                return 'base memory'
            elif self.verify_memory_addressing(operand, self.INDEXED_ADDRESSING_PATTERN, 2):
                return 'indexed memory'
            elif self.is_address(operand):
                return 'address'
            elif self.is_register(operand):
                return 'register'
            elif self.is_constant(operand):
                return 'constant'
            elif self.is_immediate_value(operand):
                return 'immediate'
            else:
                # should never happen
                raise ValueError(f"UNABLE TO DETERMINE OPERAND TYPE FOR {operand} AT LINE {self.rip}!")
        except ValueError as e:
            print(e)
            sys.exit(...)
    
    ### RETURNOF BYTES MUST BE DELT WITH

    def determine_operand_value_and_address(self, operand: str, operand_type: str | None, operand_size: int, operation_size: int, memory: Data_Memory) -> tuple[bytes, int|None]:
        """
        Determines the operand value and address based on its expression and type by going through the possible operand types and calculating the value and address accordingly.        

        :param operand: Expression for the operand to determine the value and address
        :type operand: str
        :param operand_type: Type of the operand to determine the value and address
        :type operand_type: str | None
        :param operand_size: Number of bytes that the operand uses (1, 2, 4, 8)
        :type operand_size: int
        :param operation_size: Size of the current operation to be executed (size of the biggest dominant operator)
        :type operation_size: int
        :param memory: Data memory instance to retrieve values from memory operands
        :type memory: Data_Memory
        :return: Tuple containing the operand value and address (address is None if not a memory operand)
        :rtype: tuple[bytes, int | None]
        :raises ValueError: If an invalid label is found during operand value or address determination or if the operand type is invalid
        """
        value: bytes = b"0"
        address: int | None = None 

        if operand_type == 'direct memory' or operand_type == 'base memory' or operand_type == 'indexed memory':
            address = self.calculate_memory_address(operand)
            value = memory.read_bytes(address, operand_size)  
        elif operand_type == 'address':
            if re.match(self.CONSTANTS_AND_LABELS_PATTERN, operand):
                try:
                    value = self.get_label_address(operand).to_bytes(8, byteorder="little")
                except ValueError as e:
                    raise ValueError(e)
            else:
                # should never happen
                raise ValueError(f"INVALID ADDRESS OPERAND {operand} AT LINE {self.rip}!")
        elif operand_type == 'register':
            value = self.get_register_value(operand).to_bytes(operand_size, byteorder="little")
        elif operand_type == 'constant':
            value  = self.get_encoded_value(self.constants[operand]['value']).to_bytes(operation_size, byteorder="little")
        elif operand_type == 'immediate':
            value  = self.get_encoded_value(operand).to_bytes(operation_size, byteorder="little")
        else:
            # should never happen
            raise ValueError(f"INVALID OPERAND TYPE {operand_type} AT LINE {self.rip}!")
        return (value, address)


    #----------------------
    # Operand capture
    #----------------------

    def get_operand_info(self, line: list[str]) -> list[str]:
        """
        Dinamically parses the operand declarations of an instruction.\n
        Tries to match size key words and skips over the expected operand, if it finds one else raises an exception. Also tries to match unspecified sized operands and tries to get their size (if register).
        If doesnt match either a size keyword or an operand format raises a SyntaxError.\n
        Returns pairs of sizes and operand expressions used in the declaration as list elements (always 4 elements but the sizes could be '""')
        
        :param line: Line of code in which the operands are declared without the instruction previously removed
        :type line: list[str]
        :return: List os size and operand expression pairs always following the format: [size;op2;size;op1]
        :rtype: list[str]
        :raises SyntaxError: If comes accross an invalid syntax format for assembly x86-64bit code
        :raises ValueError: If comes accross a software bug (Unexpected but preventive)
        """
        ret_list: list[str] = []
        max_ret_value: int = 3  # 4 list elements
        length: int = len(line) - 1

        # Verify each element of the list and tries to match either size keywords or an operand
        for i in range(len(line)):
            if line[i] in self.SIZE_DIRECTIVES.keys():
                # if a match with a size keyword happened verify it's position and if it's followed by an operand. If not raises SyntaxError to signal bad format
                if i == length:
                    raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")
                elif not re.match(fr'^({self.OPERAND_PATTERN})$',line[i+1]):
                    raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")
                else:
                    # Fail safe mechanism
                    if max_ret_value <= 1:
                        raise ValueError("Program parsing ran into a problem! Aborting execution ...")
                    # Appends the values of the operator info to the list, appending always to the last position available
                    ret_list[max_ret_value] = line[i+1]
                    ret_list[max_ret_value-1] = str(self.SIZE_DIRECTIVES[line[i]])
                    # Skips over one element already accounted for
                    i += 1
                    max_ret_value -= 2
            elif re.match(fr'^({self.OPERAND_PATTERN})$',line[i-length]):
                # If a match with an operand happened append it to the list and trys to get its size (if register), else appends a null size to the list to calculate/get later
                ret_list[max_ret_value] = line[i]
                if self.is_register(line[i]):
                    try:
                        ret_list[max_ret_value-1] = str(self.get_register_size(line[i]))
                    except SyntaxError as e:
                        print(e)
                        sys.exit(...)
                    max_ret_value -= 2
                else:
                    ret_list[max_ret_value-1] = ""
                    max_ret_value -= 2
            # If no match happened then the code could be faulty or bad syntax was used so raise a generic exception
            else:
                raise ValueError("Program parsing ran into a problem! Aborting execution ...")
        return ret_list

    def get_operand(self, operand: str) -> list[str]:
        """
        Retrieves the operand expression and size if valid.\n
        Goes through all the possible operand types and verifies if the given operand matches any of them. Else will raise an error.
        Acts as a dispatcher to the specific operand type verifiers.
        
        :param operand: Expression for the operand to retrieve 
        :type operand: str
        :return: List containing the operand expression and its size if valid, otherwise an empty list
        :rtype: list[str]
        :raises ValueError: If the operand is invalid or if an invalid label is found during size retrieval
        """
        ret: list[str] = []

        try: 
            condition: bool = self.is_memory_addressing(operand) or self.is_address(operand) or self.is_register(operand) or self.is_constant(operand) or self.is_immediate_value(operand)
        except ValueError as e:
            raise ValueError(e)
        if condition:
            ret.append(operand)
            try:
                size: int = self.get_label_size(operand)
            except ValueError as e:
                raise ValueError(e)
            ret.append(str(size))
        return ret
    
    def get_operation_size(self) -> int:
        """
        Returns the size of the current operation to be executed, meaning the size of the biggest of the operands.\n
        Will always return the biggestof the sizes in the current execution context.
        To be used in contexts of constants or immidiate value parsing where size is not specified but needted for byte transformations of integer values.
    
        
        :return: The size of the biggest operand in the current instruction
        :rtype: int
        """
        return self.op1_size if self.op1_size > self.op2_size else self.op2_size
    
    def get_register_size(self, register: str) -> int:
        """
        Returns the size of a register as a number of bytes it takes (1-8)
        
        :param register: Register expression
        :type register: str
        :return: Size in number of bytes of the given register
        :rtype: int
        :raises SyntaxError: If no register match happend (Fail safe mechanism)
        """
        register = register.lower()

        if register in self.registers.keys():
            return 8
        elif register.startswith('e') or register.endswith('d'):
            return 4
        elif register.endswith('x') or register.endswith('i') or register.endswith('w'):
            return 2
        elif register.endswith('h') or register.endswith('l') or register.endswith('b'):
            return 1
        else:
            raise SyntaxError(f"INVALID REGISTER '{register}' FOUND!")
    
    def get_labels(self, expressions: str) -> list[str]:
        """
        Extracts all labels from a given expression list by order.

        :param expression: Expression in verification
        :type expression: str
        :return: List of labels found in the expression in order of appearance 
        or ['Invalid'] if an invalid label-like element is found
        :rtype: list[str]
        """
        labels: list[str] = []
        found_labels: list[str] = re.findall(self.CONSTANTS_AND_LABELS_PATTERN, expressions)
        for item in found_labels:
            if not (Segment_Mapper.exists_in_section(item, self.data_section) or Segment_Mapper.exists_in_section(item, self.rodata_section) or Segment_Mapper.exists_in_section(item, self.bss_section)):
                    return ['Invalid']
            else:
                labels.append(item)
        return labels

    def get_label_size(self, label: str) -> int:
        """
        Gets the size of a given label from the data/bss/rodata sections

        :param label: Label in verification
        :type label: str
        :return: Size of the label in bytes
        :rtype: int
        :raises ValueError: If the label is not found in any section
        """
        if Segment_Mapper.exists_in_section(label, self.data_section):
            return self.data_section[label]['size'] # type: ignore  
        elif Segment_Mapper.exists_in_section(label, self.rodata_section):
            return self.rodata_section[label]['size']   # type: ignore
        elif Segment_Mapper.exists_in_section(label, self.bss_section):
            return self.bss_section[label]['size']  # type: ignore
        else:
            raise ValueError(f"LABEL {label} NOT FOUND IN ANY SECTION DURING SIZE RETRIEVAL AT LINE {self.rip}!")       # should not happen
        
    def get_label_address(self, label: str) -> int:
        """
        Returns the address of a given label (variable)
        
        :param label: Label given to a value on its declaration
        :type label: str
        :return: Address of this label in memory
        :rtype: int
        """
        # Return types are ignored because the return type of each section is specific and mask for int values

        if Segment_Mapper.exists_in_section(label, self.rodata_section):
            return self.rodata_section[label]['addresses'][0]   #type: ignore 
        elif Segment_Mapper.exists_in_section(label, self.data_section):
            return self.data_section[label]['addresses'][0]     #type: ignore
        else:
            return self.bss_section[label]['addresses'][0]      #type: ignore


    def get_address_value(self, components: list[str], expression: str) -> int:
        """
        Docstring for get_address_value
        
        :param components: Elements of an operand declaration in an instruction
        :type components: list[str]
        :return: Description
        :rtype: int
        :raises ValueError:  ...
        """
        ret: int = 0
        list: list[str] = components
        try:
            ret_list: list[int] = self.verify_multiplication(components, expression)
            ret = ret_list[0]
            if ret_list[1] != -1:
                list = Control_Unit.get_new_list(list, ret_list[-1], 3)
        except ValueError as e:
            print(f"{e}")
            sys.exit(...)   # To be determined
        try:
            ret += Control_Unit.calculate_list(list)
        except ValueError:
            print(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
            sys.exit(...)   # To be determined
        return ret
    
    def get_register_value(self, expression: str) -> int:
        """
        Returns a register value based on the expression given and it's parent value defined as a class instance

        :param expression: Register to obtain the value of
        :type expression: str
        :return: Integer value of that register
        :rtype: int
        :raises KeyError: If the obtained parent register is not defined in this classes instances
        """
        if expression in self.registers.keys():
            return self.registers[expression]
        parent, mask = self.get_register_parent(expression)
        
        if parent not in self.registers:
            raise KeyError(f"Unknown register: {expression}")

        raw_val: int = self.registers[parent] & mask
        
        # Shift high-bytes down to the 0-255 range
        if expression.lower().endswith('h') and len(expression) == 2:
            return raw_val >> 8
            
        return raw_val

    def get_register_parent(self, expression: str) -> tuple[str, int]:
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

    def get_encoded_value(self, value: str | int) -> int:
        """
        Processes a given value of type string or int to be returned as an integer.
        
        :param value: Value to be processed
        :type value: str | int
        :return: Integer value of the given value
        :rtype: int
        """
        if re.match(self.NUMBER_REPRESENTATION_PATTERN, str(value)):
            return int(value, 0)   #type: ignore
        else:
            # The value is a String
            new_value: str = str(value).replace('"', '').replace("'", "")
            byte_value: bytes = str(new_value).encode()
            return int.from_bytes(byte_value, 'little')
    
    def get_current_fu(self) -> FU:
        """
        Returns the object to the current funtional unit in use

        :return: Funtional unit object at use
        :rtype: FU (Type Aliase for all funtional unit types)
        """
        if self.current_fu == "cpu":
            return self.data_path
        elif self.current_fu == "alu":
            return self.alu
        elif self.current_fu == "fpu":
            return self.fpu
        else:
            raise ValueError("NO FUNTIONAL UNIT FOUND.\n Exiting program...")
            
    #-------------------------
    # Operand type validation
    #-------------------------

    def is_memory_addressing(self, expression: str) -> bool:
        """
        Verifies if a given expression is a memory addressing mode

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a memory addressing mode
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        try:
            result: bool = self.verify_memory_addressing(expression, self.DIRECT_AND_BASE_ADDRESSING_PATTERN) or self.verify_memory_addressing(expression,self.DIRECT_AND_BASE_ADDRESSING_PATTERN, 2) or self.verify_memory_addressing(expression, self.INDEXED_ADDRESSING_PATTERN, 2)
        except ValueError as e:
            raise ValueError(e)
        return result
    
    def verify_memory_addressing(self, expression: str, pattern: str, number_registers: int=0, number_labels: int=1) -> bool:
        """
        Verifies if a given expression is a direct, base or indexed memory addressing mode based on the number of registers and labels allowed to be used in it and the pattern to use for the verification.\n
        If the expression is none of those and does not take invalid registers or not existing labels  returns False.
        If any invalid or not existing components are found raises a ValueError.

        :param expression: Expression in verification
        :type expression: str
        :param pattern: Pattern to use for the match
        :type pattern: str
        :param number_registers: Number of registers allowed in the expression. Default to 0.
        :type number_registers: int
        :param number_labels: Number of labels allowed in the expression. Default to 1.
        :type number_labels: int
        :return: True if the expression follows the pattern given and has the correct number of each component or False otherwise.
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        if re.match(pattern, expression):
            # If a match with the Direct/Base memory addressing pattern was found get the list of the labels used in the expression and the list of registers used in the expression
            labels: list[str] = self.get_labels(expression)
            registers_in_expression: list[str] = re.findall(self.REGISTER_PATTERN, expression)
            # If the list returned 'invalid' then non existing label was found
            if 'Invalid' in labels:
                raise ValueError(f"INVALID LABEL IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            # If there are more than label or registers involved in the expression than it is permitted by the arguments the expression is not syntactically correct
            elif len(labels) > number_labels or len(registers_in_expression) > number_registers:
                return False
            else:
                return True
        return False
    
    def is_address(self, expression: str) -> bool:
        """
        Verifies if a given expression is a direct address (immediate value or label)

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a direct address
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        # If the expression has the memory address brakets it is not an address
        if expression.startswith('[') and expression.endswith(']'):
            return False
        # Assuming it is an address, tries to match the components valid in an address declaration declaration and verify if they are valid
        elif re.match(fr'^{self.CONSTANTS_AND_LABELS_PATTERN}$', expression):
            if not (Segment_Mapper.exists_in_section(expression, self.data_section) or Segment_Mapper.exists_in_section(expression, self.rodata_section) or Segment_Mapper.exists_in_section(expression, self.bss_section)):
                raise ValueError(f"INVALID LABEL {expression} AT LINE {self.rip}!")
            else:
                return True
        elif re.match(fr'^{self.NUMBER_REPRESENTATION_PATTERN}$', expression):
            return True
        return False
    
    def is_register(self, expression: str) -> bool:
        """
        Verifies if a given expression is a register

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a register
        :rtype: bool
        """
        if re.match(fr'^{self.REGISTER_PATTERN}$', expression):
            return True
        return False
    
    def is_constant(self, expression: str) -> bool:
        """
        Verifies if a given expression is a constant

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a constant
        :rtype: bool
        """
        if expression in self.constants:
            return True
        return False
    
    def is_immediate_value(self, expression: str) -> bool:
        """
        Verifies if a given expression is an immediate value

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is an immediate value
        :rtype: bool
        """
        if re.match(fr'^{self.IMMEDIATE_VALUE_PATTERN}$', expression):
            return True
        return False
    
    def is_valid_line_for_constant(self, line: int) -> bool:
        """
        Verifies if a constant was declared before the current line being executed
        
        :param line: Line of the declaration of the constant
        :type line: int
        :return: True if the current line is bigger than line, False otherwise
        :rtype: bool
        """
        return self.rip > line
    
    #----------------------------------------------
    # Operand and expressions calculation methods
    #----------------------------------------------

    def parse_operand_info(self, op_info: list[str]) -> None:
        """
        Attributes the size and expression value of each operand to the respective instances of this class.\n
        If comes accross a non declared size and there are no registers in the instruction raises SyntaxError. If any of the expressions for the operands are not set raises ValueError
        
        :param op_info: List with the size and expression of each operand as a pair in the format: [size;op2;size;op1]
        :type op_info: list[str]
        :raises SyntaxError: If comes accross undeclared sizes with out registers in the instruction.
        :raises ValueError: If any of the operand expressions are not set.
        """
        # Fail safe verification
        if op_info[3] == "" or op_info[1] == "":
            raise ValueError("Program parsing ran into a problem! Aborting execution ...")
        # If any operand doesn't have size and there is no registers in the instruction the syntax is invalid
        elif (op_info[0] == "" or op_info[2] == "") and not (self.is_register(op_info[1]) or self.is_register(op_info[3])):
            raise SyntaxError(f"INVALID SYNTAX FORMAT AT LINE {self.rip}!")
        else:
            # If a register existes and one of the sizes for the operands is a null identifier, give it the size of the register used
            if op_info[0] == "" or op_info[2] == "":
                if self.is_register(op_info[1]):
                    op_info[2] = op_info[0]
                else:
                    op_info[0] = op_info[2]
            self.set_operand("op1", op_info[3], int(op_info[2]))
            self.set_operand("op2", op_info[1], int(op_info[0]))
    
    def calculate_memory_address(self, expression: str) -> int:
        """
        Calculates the address value of a memory addressing operand expression
        
        :param expression: Full operand expression to calculate
        :type expression: str
        :return: Address value of the expression
        :rtype: int
        """
        new_expression: str = expression.replace(" ", "").replace("[", "").replace("]", "")
        components: list[str] = re.split(r'([\+\-\*])', new_expression)
        try:
            parsed_address_expression: list[str] = self.parse_address_expression(components, expression)
        except ValueError as e:
            print(e)
            sys.exit(...)
        return self.get_address_value(parsed_address_expression, expression)

    def parse_address_expression(self, components: list[str], expression: str) -> list[str]:
        """
        Returns a parsed list equivelent to the one given but with all labels and constants substituted by their address (labels) or values (constants)

        :param components: Operand declaration in an instruction to be parsed to integer values
        :type components: list[str]
        :param expression: Expression for the memory operand to calculate the address
        :type expression: str
        :return: Parsed list with integer representation of labels addresses and constants values
        :rtype: list[str]
        :raises ValueError: If an invalid label is found in the expression or if the memory addressing mode is invalid
        """

        ret: list[str] = []

        for element in components:
            if re.match(self.GENERAL_PURPOSE_REGISTERS_PATTERN, element):
                register_value: str = str(self.get_register_value(element))
                ret.append(register_value)
            elif re.match(self.FPU_REGISTERS_PATTERN, element):
                ### NOT CURRENTLY ACTIVE
                pass
            elif re.match(self.CONSTANTS_AND_LABELS_PATTERN, element):
                if Segment_Mapper.exists_in_section(element, self.data_section) or Segment_Mapper.exists_in_section(element, self.rodata_section) or Segment_Mapper.exists_in_section(element, self.bss_section):
                    try:
                        label_address: str = str(self.get_label_address(element))
                        ret.append(label_address)
                    except ValueError as e:
                        raise ValueError(e)
                elif Segment_Mapper.exists_in_section(element, self.constants):
                    if not self.is_valid_line_for_constant(int(self.constants[element]['line'])):
                        raise ValueError(f"Constant {element} is not yet defined")
                    constant_value: str = str(self.get_encoded_value(self.constants[element]['value']))
                    ret.append(constant_value)
                else:
                    raise ValueError(f"INVALID LABEL {element} IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            else:
                ret.append(element)
        return ret        

    def verify_multiplication(self, components: list[str], expression: str) -> list[int]:
        """
        Verifies if an operand instruction as a multiplication in its declaration.
        If so calculates it and verifies its correctness.\n
        Returns a list with 2 elements: 1º - Result of the calculation; 2º - Index of the first element used in the calculation (if -1 no calculation was made) 
        
        :param components: Elements of an operand declaration in an instruction
        :type components: list[str]
        :param expression: Expression of a memory addressing operand 
        :type expression: str
        :return: Parial calculation of the address and the index of the first element used in the calculation (will use always 3 followed indexes). Only multiplications calculated.
        :rtype: list[int]
        :raises ValueError: If a multiplication is detected but can't be calculated due to bad syntax
        """
        if Control_Unit.has_symbol(components, '*'):
            try:
                mult_index: int = Control_Unit.get_index_of(components, '*', 1)[0]
            except ValueError:
                print(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
                sys.exit(...)   # To be determined
            if mult_index != 0 and mult_index != len(components)-1:
                try:
                    return [int(components[mult_index-1]) * int(components[mult_index+1]), mult_index-1]
                except ValueError as e:
                    print(f"{e}")
                    sys.exit(...)   # To be determined
            else:
                raise ValueError(f"INVALID EXPRESSION {expression} IN MEMORY ADDRESSING MODE AT LINE {self.rip}!")
        else:
            return [0,-1]
        
    #-------------------------------
    # SYSCALL'S  AND CALL'S METHODS
    #-------------------------------

    def syscall(self) -> None:
        """
        Reproduces syscall behaviour accordingly to the values of certain registers
        """
        # Exit syscall
        if self.registers['rax'] == 60:
            print(f"Program finished with exit status {self.registers['rdi']}")
            sys.exit(0)
            # Write syscall (could be improved to allow writing into the stdin)
        elif self.registers['rax'] == 1 and self.registers['rdi'] == 1:
            for i in range(self.registers['rdx']):
                print(Data_Memory.read_bytes(self.memory, self.registers['rsi'] + i, 1).decode('utf-8'))
    
    def call(self) -> None:
        pass
    
    # -----------------------
    # STATIC HELPERS 
    # -----------------------

    @staticmethod
    def has_symbol(list: list[str], symbol: str) -> bool:
        """
        Verifies if a multiplication exists in a operand expression
        
        :param list: List of string elements
        :type list: list[str]
        :param symbol: character/element to search for
        :type symbol: str
        :return: True if a match was found, False if it wasn't
        :rtype: bool
        """
        for element in list:
            if element == symbol:
                return True
        return False
    
    @staticmethod
    def get_index_of(list: list[str], symbol: str, count: int) -> list[int]:
        """
        Returns the indexes of the occurrences of symbol in a given list of strings.\n
        If the return length does not match the count of indexes desired raises ValueError, else returns the list
        
        :param list: List of string elements 
        :type list: list[str]
        :param symbol: character/element to search for
        :type symbol: str
        :param count: Number of desired occurrences of the symbol on the list.
        :type count: int
        :return: List of the indexes of those occurrences
        :rtype: list[int]
        :raises ValueError: If the occurrence count and the length of the list do not match
        """
        ret: list[int] = []

        for i in range(len(list)):
            if list[i] == symbol:
                ret.append(i)
        
        if len(ret) != count:
            raise ValueError
        else:
            return ret

    @staticmethod
    def get_new_list(list: list[str], index: int, count: int) -> list[str]:
        """
        Returns a new list based on a given one without a given number of followed elements of that base list given by the first index of the sequence.
        
        :param list: List of string elements 
        :type list: list[str]
        :param index: Index of the first element to remove
        :type index: int
        :param count: Number of times to remove the element at index
        :type count: int
        :return: A new list without count elements starting at position index
        :rtype: list[str]
        """
        new_list: list[str] = list.copy()
        for _ in range(count):
            new_list.pop(index)
        return new_list
    
    @staticmethod
    def calculate_list(list: list[str]) -> int:
        """
        Calculates the value of a mathematic expression in list elements.\n
        Expects the elements to start on a digit and alternate between a addition or subtration operator and a number.
        Raises ValueError if ths syntax is not followed
        
        :param list: List of string elements to calculate the value of 
        :type list: list[str]
        :return: Result of the mathematial expression on this list
        :rtype: int
        :raises ValueError: If no operation symbol is found on a given odd index of the list or if an even index of the list do not point to a digit
        """
        try:
            result: int = int(list[0])

            for i in range(1, len(list), 2):
                operator: str = list[i]
                value: int = int(list[i+1])

                if operator == "+":
                    result += value
                elif operator == "-":
                    result -= value
                else:
                    raise ValueError
                
            return result
        except ValueError, IndexError:
            raise ValueError