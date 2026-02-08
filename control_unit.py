import sys
import re
from storage import Storage
from data_memory import Data_Memory
from segment_mapper import Segment_Mapper
from .types import DataSectionInfo, BssSectionInfo, LabelMap, ConstantMap, Address
from alu import ALU

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
    INDIRECT_ADDRESSING_PATTERN = fr'^\[(?:\s*){COMPONENTS_ADDRESSING_PATTERN}(?:\s)*([\+\-\*](?:\s)*{COMPONENTS_ADDRESSING_PATTERN})*(?:\s)*\]$'
    


    def __init__(self, memory: Data_Memory, loader: Segment_Mapper, validation_file_name: str) -> None:
        # Initialize Control Unit with memory, segment mapper, funtional units and registers (general purpose, fpu and flags)
        self.memory: Data_Memory = memory
        self.loader: Segment_Mapper = loader
        self.alu: ALU = ALU(self)
        self.fpu: FPU = FPU(self)

        self.registers: dict[str, int] = {
            # General Purpose Registers (64-bit Integers)
            "rax": 0, "rbx": 0, "rcx": 0, "rdx": 0,
            "rsi": 0, "rdi": 0, "rbp": 0, "rsp": loader.stack_pointer,
            "r8": 0,  "r9": 0,  "r10": 0, "r11": 0,
            "r12": 0, "r13": 0, "r14": 0, "r15": 0,
        }

        # xmm registers are treated as the lower 16 bytes of each respective ymm register
        self.ymm: dict[str, bytearray] = {
            f"ymm{i}": bytearray(32) for i in range(16)
        }

        # Instruction Pointer
        self.rip: int = loader.rip  # Instruction Pointer initialized from Segment Mapper
        # Flag state holders
        self.flags = {
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
        self.current_fu: str = "cpu" # (cpu/alu/fpu)
        self.current_instruction: str | None = None
        self.op1: str | None = None
        self.op1_size: int = 0  # size must be 0 if self.op1 = None
        self.op1_value: int = 0 # value must be 0 if self.op1 = None
        self.op1_address: int | None = None # address must be None if self.op1 is not a memory operand
        self.op1_type: str | None = None # type must be None if self.op1 = None, otherwise it must be either 'register'/'memory'/'constant'/'immediate'
        self.op2: str | None = None
        self.op2_size: int = 0  # size must be 0 if self.op2 = None
        self.op2_value: int = 0 # value must be 0 if self.op2 = None
        self.op2_address: int | None = None # address must be None if self.op2 is not a memory operand
        self.op2_type: str | None = None # type must be None if self.op2 = None, otherwise it must be either 'register'/'memory'/'constant'/'immediate'
        self.valid_instructions: dict[str, dict[str, int]] = Storage.read_valid_instructions(validation_file_name)

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
        # 1. Gets the instruction, operands and funtional unit in use and verifies it's compatibility it the operator count of the instruction
        self.fetch()
        # current_instruction will only be 'None' if rip points to a label in .text (which should be skiped)
        if self.curretent_instruction != None:
            # 2. Verifies if the instruction-operand set is valid
            self.interprete()
            # 3. Conducts execution to a correct F.U. and executes the operation 
            self.execute()
            # 4. Verifies if the execution generated any type of side effects of flags and halted state and updates them
            self.validate_execution_state()
            # 5. Increases rip 
        self.rip += 1

    def fetch(self) -> None:
        """
        Fetches the current instruction and its operands from the text section based on the instruction pointer (RIP).\n
        Sets the current instruction and current funtional unit in use and validates and sets the operands and its size.
        Raises a ValueError if the instruction is invalid or if the operands are invalid.        
        
        :raises ValueError: If the instruction is invalid or if the operands are invalid.
        :return: None
        :rtype: None
        """
        line: list[str] = self.text_section[self.rip]

        if len(line) == 1 and line[0] in self.labels:
            return 
        elif self.is_valid_instruction(line[0]):
            self.curretent_instruction = line[0]
            try:
                self.validate_operands(line)
            except ValueError as e:
                print(f"Error at line {self.rip}: {e}")
                self.curretent_instruction = None
                self.finished = True
                
            if self.valid_operand_count():
                return
            else:
                self.set_operand("both", None, 0)
                raise ValueError(f"INVALID OPERAND COUNT FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
        else:
            raise ValueError(f"INVALID INSTRUCTION AT LINE {self.rip}!")
    
    
    def is_valid_instruction(self, instruction: str) -> bool:
        """
        Verifies if a given instruction is supported by the program and if so sets the current funtional unit in use.

        :param instruction: Instruction in verification
        :type instruction: str
        :return: True if the instruction is present in the valid_instructions.json file
        :rtype: bool
        """
        for key in self.valid_instructions.keys():
            if instruction in self.valid_instructions[key]:
                self.current_fu = key
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
            try:
                self.set_operand("both", None, 0)
                self.set_operand_type("both", None)
                self.set_operand_value("both", 0)
                self.set_operand_address("both", None)
            except ValueError as e:
                raise ValueError(e)
            
        elif instruction_length == 2:
            self.set_operand("op2", None, 0)
            self.set_operand_value("op2", 0)
            self.set_operand_address("op2", None)
            try:
                operand_info: list[str] = self.get_operand(line[1])
                self.set_operand("op1", operand_info[0], int(operand_info[1]))
                self.set_operand_type("op1", operand_info[0])
                operand_value_and_address: list[int | None] = self.set_operand_value_and_address(operand_info[0], int(operand_info[1]))
                self.set_operand_value("op1", operand_value_and_address[0]) # type: ignore  - operand value is always int, but the function signature requires it to be int | None
                self.set_operand_address("op1", operand_value_and_address[1])
            except ValueError as e:
                self.set_operand("op1", None, 0)
                raise ValueError(e)
            
        elif instruction_length == 3:
            if line[1] in self.SIZE_DIRECTIVES.keys():
                self.set_operand("op2", None, 0)
                try:
                    operand_info: list[str] = self.get_operand(line[2])
                    self.set_operand("op1", operand_info[0], int(operand_info[1]))
                except ValueError as e:
                    self.set_operand("op1", None, 0)
                    raise ValueError(e)
            elif line[2] in self.SIZE_DIRECTIVES.keys():
                self.set_operand("both", None, 0)
                raise ValueError(f"INVALID OPERAND SET FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
            else:
                try:
                    operand2_info: list[str] = self.get_operand(line[1])
                    operand1_info: list[str] = self.get_operand(line[2])
                    self.set_operand("op1", operand1_info[0], int(operand1_info[1]))
                    self.set_operand("op2", operand2_info[0], int(operand2_info[1]))
                except ValueError as e:
                    self.set_operand("op1", None, 0)
                    self.set_operand("op2", None, 0)
                    raise ValueError(e)
                
        elif instruction_length == 4:
                if line[3] in self.SIZE_DIRECTIVES.keys() or line[1] in self.SIZE_DIRECTIVES.keys() and line[2] in self.SIZE_DIRECTIVES.keys():
                    self.set_operand("both", None, 0)
                    raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
                elif line[1] in self.SIZE_DIRECTIVES.keys():
                    if line[2] in self.SIZE_DIRECTIVES.keys():
                        self.set_operand("both", None, 0)
                        raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
                    else:
                        try:
                            operand2_info: list[str] = self.get_operand(line[2])
                            operand1_info: list[str] = self.get_operand(line[3])
                            self.set_operand("op1", operand1_info[0], int(operand1_info[1]))
                            self.set_operand("op2", operand2_info[0], self.SIZE_DIRECTIVES[line[1]])
                        except ValueError as e:
                            self.set_operand("op1", None, 0)
                            self.set_operand("op2", None, 0)
                            raise ValueError(e)
                elif line[2] in self.SIZE_DIRECTIVES.keys():
                    try:
                        operand1_info: list[str] = self.get_operand(line[3])
                        operand2_info: list[str] = self.get_operand(line[1])
                        self.set_operand("op1", operand1_info[0], self.SIZE_DIRECTIVES[line[2]])
                        self.set_operand("op2", operand2_info[0], int(operand2_info[1]))
                    except ValueError as e:
                        self.set_operand("op1", None, 0)
                        self.set_operand("op2", None, 0)
                        raise ValueError(e)
                else:
                    # Will never happen 
                    self.set_operand("both", None, 0)
                    raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
        elif instruction_length == 5:
            if line[1] in self.SIZE_DIRECTIVES.keys() and line[3] in self.SIZE_DIRECTIVES.keys():
                try:
                    operand2_info: list[str] = self.get_operand(line[2])
                    operand1_info: list[str] = self.get_operand(line[4])
                    self.set_operand("op1", operand1_info[0], self.SIZE_DIRECTIVES[line[3]])
                    self.set_operand("op2", operand2_info[0], self.SIZE_DIRECTIVES[line[1]])
                except ValueError as e:
                    self.set_operand("op1", None, 0)
                    self.set_operand("op2", None, 0)
                    raise ValueError(e)
            else:
                self.set_operand("both", None, 0)
                raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")
            
        else:
            self.set_operand("both", None, 0)
            raise ValueError(f"INVALID SYNTAX FOR INSTRUCTION {self.curretent_instruction} AT LINE {self.rip}!")


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

        
    

    def set_operand(self, operand: str, expression: str | None, size: int) -> None:
        """
        Attribute a value and size to the operand attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param expression: Unaltered expression used to refer to the operand
        :type expression: str | None
        :param size: Size of the operand (must be calculated)
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

    def set_operand_value(self, operand:str, value: int) -> None:
        """
        Attribute a value to the operand value attributes

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param value: Value of the operand (must be calculated)
        :type value: int
        :raises ValueError: If an invalid operand identifier is used
        """
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
        
    def set_operand_type(self, operand: str, operand_expression: str | None) -> None:
        """
        Attribute a type to the operand type attributes by verifying the operand expression type

        :param operand: Expression for the operand to update (both/op1/op2)
        :type operand: str
        :param operand_expression: Unaltered expression used to refer to the operand
        :type operand_expression: str
        :raises ValueError: If an invalid operand identifier is used or if the operand expression is invalid
        """
        type: str | None = None

        if operand_expression == None:
            type = None
        elif self.is_direct_memory_addressing(operand_expression):
            type = "direct memory"
        elif self.is_base_addessing(operand_expression):
            type = "base memory"
        elif self.is_indexed_addressing(operand_expression):
            type = "indexed memory"
        elif self.is_address(operand_expression):
            type = "address"
        elif self.is_register(operand_expression):
            type = "register"
        elif self.is_constant(operand_expression):
            type = "constant"
        elif self.is_immediate_value(operand_expression):
            type = "immediate"
        else:
            raise ValueError(f"INVALID OPERAND EXPRESSION {operand_expression} AT LINE {self.rip}!")
        
        if operand == "both":
            self.op1_type = type
            self.op2_type = type
        elif operand == "op1":
            self.op1_type = type
        elif operand == "op2":
            self.op2_type = type
        else:
            raise ValueError(f"INVALID OPERAND IDENTIFIER {operand} USED. IT SHOULD BE EITHER 'both'/'op1'/'op2'!")

        
    def set_operand_value_and_address(self, operand: str, expression: str, size: int) -> list[int | None]:
        """
        Retrieves the value and address of the operand based on its expression and size.\n
        Goes through all the possible operand types and verifies if the given operand matches any of them. Else will raise an error.
        Acts as a dispatcher to the specific operand type value and address retrievers.

        :param operand: Expression for the operand to retrieve 
        :type operand: str
        :param expression: Unaltered expression used to refer to the operand
        :type expression: str
        :param size: Size of the operand (must be calculated)
        :type size: int
        :return: List containing the operand value and address (None if not a memory operand) if valid, otherwise an empty list
        :rtype: list[int | None]
        :raises ValueError: If the operand is invalid or if an invalid label is found during retrieval
        """
        value: int = 0
        address: int | None = None

        if self.is_memory_addressing(expression):
            address: int = self.calculate_memory_address(expression)
            value: int = self.memory.read(address, size)
        elif self.is_address(expression):
            value: int = self.calculate_memory_address(expression)
        elif self.is_register(expression):
            value: int = self.registers[expression]
        elif self.is_constant(expression):
            value: int = self.constants[expression]
        elif self.is_immediate_value(expression):
            value: int = int(expression, 0)
        else:
            raise ValueError(f"INVALID OPERAND EXPRESSION {expression} AT LINE {self.rip}!")
        return [value, address]

    
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
            result: bool = self.is_direct_memory_addressing(expression) or self.is_base_addessing(expression) or self.is_indexed_addressing(expression)
        except ValueError as e:
            raise ValueError(e)
        return result
    
    def is_direct_memory_addressing(self, expression: str) -> bool:
        """
        Verifies if a given expression is a direct memory addressing mode

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a direct memory addressing mode
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        if re.match(self.DIRECT_AND_BASE_ADDRESSING_PATTERN, expression):
            labels: list[str] = self.get_labels(expression)
            if 'Invalid' in labels:
                raise ValueError(f"INVALID LABEL IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            if len(labels) > 1:
                return False
            return True
        return False
    
    
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
            elif Segment_Mapper.exists_in_section(item, self.data_section) or Segment_Mapper.exists_in_section(item, self.rodata_section) or Segment_Mapper.exists_in_section(item, self.bss_section):
                labels.append(item)
        return labels
    
    def is_base_addessing(self, expression: str) -> bool:
        """
        Verifies if a given expression is a base addressing mode

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is a base addressing mode
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        if re.match(self.DIRECT_AND_BASE_ADDRESSING_PATTERN, expression):
            labels: list[str] = self.get_labels(expression)
            registers_in_expression: list[str] = re.findall(self.REGISTER_PATTERN, expression)
            if 'Invalid' in labels:
                raise ValueError(f"INVALID LABEL IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            if len(labels) > 1:
                return False
            elif len(registers_in_expression) > 2:
                return False
            return True
        return False
    
    def is_indexed_addressing(self, expression: str) -> bool:
        """
        Verifies if a given expression is an indexed addressing mode

        :param expression: Expression in verification
        :type expression: str
        :return: True if the expression is an indexed addressing mode
        :rtype: bool
        :raises ValueError: If an invalid label is found in the expression
        """
        if re.match(self.INDIRECT_ADDRESSING_PATTERN, expression):
            labels: list[str] = self.get_labels(expression)
            registers_in_expression: list[str] = re.findall(self.REGISTER_PATTERN, expression)
            if 'Invalid' in labels:
                raise ValueError(f"INVALID LABEL IN MEMORY ADDRESSING MODE {expression} AT LINE {self.rip}!")
            if len(labels) > 1:
                return False
            elif len(registers_in_expression) > 2:
                return False
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
        if "[" in expression or "]" in expression:
            return False
        elif re.match(fr'^{self.CONSTANTS_AND_LABELS_PATTERN}$', expression):
            if not (Segment_Mapper.exists_in_section(expression, self.data_section) or Segment_Mapper.exists_in_section(expression, self.rodata_section) or Segment_Mapper.exists_in_section(expression, self.bss_section)):
                raise ValueError(f"INVALID LABEL {expression} AT LINE {self.rip}!")
            else:
                return True
        elif re.match(fr'^{self.IMMEDIATE_VALUE_PATTERN}$', expression):
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
    
    def calculate_memory_address(self, expression: str) -> int:
        ...
    
    def 
    
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
    
    def valid_operand_count(self) -> bool:
        """
        Verifies if the current operand count is valid for the current instruction

        :return: True if the current operand count is valid for the current instruction
        :rtype: bool
        """
        expected_operand_count: int = self.valid_instructions[self.current_fu][self.curretent_instruction]  # type: ignore
        actual_operand_count: int = 0
        if self.op1 != None:
            actual_operand_count += 1
        if self.op2 != None:
            actual_operand_count += 1
        return expected_operand_count == actual_operand_count    