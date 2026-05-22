import sys
from helpers.storage import Storage
from bridges.data_memory import Data_Memory
from bridges.register_manager import Registers_Interface
from helpers.my_types import DataSectionInfo, BssSectionInfo, LabelMap, ConstantMap, Address
import re

class Segment_Mapper:
    """
    Class responsible for mapping program segments into memory.\n
    Parses the assembly file to identify sections, labels, constants, and initializes memory segments accordingly.
    Does validation of segment declarations and manages stack initialization.\n
    Uses Data_Memory class to handle memory operations.\n
    Provides methods to load program sections (.text, .data, .rodata, .bss) and constants.
    Initializes the stack with argc and argv values.\n
    If any syntax errors or critical issues are found during parsing, the program exits gracefully with appropriate error messages.\n
    All segment addresses are stored in respective dictionaries for easy access during execution. Actual values are stored in Data_Memory object on appropriate addresses.\n
    Author: João Carilho Louro

    :param file_name: Path to the assembly file
    :type file_name: str
    :param argvcount: Number of command line arguments
    :type argvcount: int
    :param argv: List of command line arguments
    :type argv: list[str] | None
    :param stack_limit: Minimum allowed value for the stack pointer
    :type stack_limit: int
    :return: None
    """

    # Memory footprint optimization 
    __slots__ = (
        'stack_limit', 'memory_list', 'rodata_segment', 'data_segment', 
        'bss_segment', 'labels', 'constants', 'file_name', 
        'memory', 'stack_pointer', 'valid_start', 'rip', 'registers'
    )

    # Directives for size identification and memory allocation verification
    SIZE_DIRECTIVES = {
        'db': (1, True), 'dw': (2, True), 'dd': (4, True), 'dq': (8, True),
        'resb': (1, False), 'resw': (2, False), 'resd': (4, False), 'resq': (8, False)
    }

    MASKS_DIRECTIVES = {
        'byte': 0xFF, 'word': 0xFFFF, 'dword': 0xFFFFFFFF, 'qword': 0xFFFFFFFFFFFFFFFF
    }

    # Architecture Constants for sections start and memory allocation
    TEXT_BASE = 0x400000
    RODATA_BASE = 0x500000
    DATA_BASE = 0x600000
    BSS_BASE = 0x700000
    STACK_START = 0x7fffffffe000


    TOKENS_PATTERN = r"""(?x)
        ".*?"|'.*?'|                  # Strings
        \[.*?\]|                      # Memory access
        \(.*?\)|                      # Parenthesized expressions
        0x[\da-fA-F]+|                # Hex Prefix
        \d+[\da-fA-F]*[hH]|           # Hex Suffix
        [01]+[bB]|                    # Binary
        [a-zA-Z_]\w*|                 # Instructions / Registers / Labels
        [-+]?\d+                      # Signed Decimals
    """

    ELEMENTS_TO_SKIP = r'^[,\s]+$'  # Commas and whitespace to skip during parsing

    
    # -----------------------------
    # Pattern-Matching Expressions
    # -----------------------------

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
    


    def __init__(self, file_name: str, argvcount: int = 0, argv: list[str] | None = None, validation_file_name: str = "valid_instructions.json", stack_limit: int = 0x7fff00000000) -> None:
        """
        Initializes the Segment_Mapper by loading the assembly file, parsing its sections, and setting up memory segments and stack.

        :param file_name: Path to the assembly file
        :type file_name: str
        :param argvcount: Number of command line arguments
        :type argvcount: int
        :param argv: List of command line arguments
        :type argv: list[str] | None
        :param stack_limit: Minimum allowed value for the stack pointer
        :type stack_limit: int
        :return: None
        """
        # ------------------------
        # Constraints definitions 
        # ------------------------

        # Stack limit setting
        self.stack_limit :int = stack_limit
        # Requires a 'start' label to be changed or will quit the program
        self.valid_start: str = Storage.read_valid_start(validation_file_name)


        # ---------------
        # Info holders
        # ---------------

        # File name holder (After conversion to a parsable json file)
        self.file_name: str = Storage.convert_to_json(file_name)
        # Value will be changed while parsing .text section
        self.rip: int = -1 # default invalid value
        # Memory used in the execution of the program
        self.memory_list :list[list[str]]= []
        
        # ---------------------------------------
        #(CURRENT UPDATE WILL MAKE THIS OBSOLETE)
        # Should only store addresses as actually memory values are stored in Data_Memory class
        self.rodata_segment: DataSectionInfo = {}
        self.data_segment: DataSectionInfo = {}
        self.bss_segment: BssSectionInfo = {}
        # ---------------------------------------

        self.labels: LabelMap = {}
        self.constants: ConstantMap = {}     # Stores constant values

        # Register handler class instance
        self.registers: Registers_Interface = Registers_Interface()
        # Memory handler class instance 
        self.memory: Data_Memory = Data_Memory(self.registers, self.RODATA_BASE)
        
        self.load_program(self.file_name)
        
        # Writes the stack in memory (Currently also uses the paging system but might be changed in to a stack system)
        self.stack_pointer: int = self.initialize_stack(argvcount, argv, self.memory, self.stack_limit)
        self.parse_section()

    # -----------------------
    # PROGRAM LOADING
    # -----------------------
    def load_program(self, file_name: str) -> None:
        """
        Loads the program into 'usable memory' and loads
        a json file with each line of relevant code properly separated
        into tokens of a list.
        
        :param file_name: name of the file to load
        :type file_name: str
        :return: Data_Memory object used to hold contents of labels 
        :rtype: Data_Memory
        """
        program_lines: list[str] = Storage.load_file_lines(file_name)
        # List for usable memory initialization
        self.memory_list = []
        for line in program_lines:
            code_part: str = line.split(";")[0].strip()
            tokens: list[str] = re.findall(self.TOKENS_PATTERN, code_part)
            tokens = [token for token in tokens if not re.match(self.ELEMENTS_TO_SKIP, token)]
            self.memory_list.append(tokens)
        
        Storage.save_file(file_name, self.memory_list)
        
    

    def parse_section(self) -> None:
        """
        TODO
        """
        # Pointers for lines of usable memory and address at use from a Data_memory object
        index: int = 0
        current_rip: Address = Segment_Mapper.RODATA_BASE
        while index < len(self.memory_list):
            tokens = self.memory_list[index]

            # Just for prevention
            if not tokens:
                index += 1
                continue

            if tokens[0] == "section":
                section_name: str = tokens[1]
                if section_name.lstrip(".") == "rodata" or section_name.lstrip(".") == "data":
                    if section_name.lstrip(".") == "rodata":
                        current_rip = Segment_Mapper.RODATA_BASE
                    else :
                        current_rip = Segment_Mapper.DATA_BASE
                    current_rip = self.load_data(current_rip, index, section_name.lstrip("."))
                elif section_name.lstrip(".") == "bss":
                    current_rip = Segment_Mapper.BSS_BASE
                    current_rip = self.load_bss(current_rip, index)
                elif section_name.lstrip(".") == "text":
                    self.load_text(current_rip, index)          # <<current_rip>> is passed if i decide to also start storing instructions in memory, for now IS INACTIVE!!!

            elif (Segment_Mapper.is_constant(tokens)):
                self.load_constant(tokens, index)
                index += 1


    # Schematics for each element of program sections:
        # |_variable name
        # |_'size': (number of bytes allocated)
        # |_'addresses': (address list from Data Memory objet)
    
    # Schematics for labels storage:
        # |_label name
        # |_'line': (index counter of load_text)
    

    # Schematics for constant storage:
        # |_constant name
        # |_'line': (index counter of load_text)
        # |_'value': (integer value)
    
    # ------------------------------------------
    # sections .data and .rodata related methods
    # ------------------------------------------


    def load_data(self, current_rip: Address, index: int, section: str) -> Address:
        """
        Takes care of .data and .rodata components parsing as well as validation of the declarations format.

        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :param index: number of the line being parsed
        :param section: name of the section being parsed ('.data' or '.rodata')
        :param is_rodata: flag indicating if the section is .rodata
        :return: updated pointer to the Address in use to store values in the Data_memory object after loading the section
        :rtype: Address
        """
        index += 1
        while(self.memory_list[index][0] != "section" or index >= len(self.memory_list)):
            tokens: list[str] = self.memory_list[index]
            if not self.data_format_validation(tokens, index, section):
                sys.exit(-1)
            elif "times" in tokens:
                current_rip = self.load_timed_data(tokens, index, section, current_rip)
            elif len(tokens) >= 3:
                current_rip = self.load_multiple_data(tokens, index, section, current_rip)
            else:
                current_rip = self.load_single_data(tokens, index, section, current_rip)
            index += 1
            
        return current_rip

    def data_format_validation(self, line: list[str], index: int, section: str) -> bool:
        """
        Validates the format of a .data or .rodata declaration line.

        :param line: full line of code that has a .data or .rodata declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :param section: name of the section being parsed ('.data' or '.rodata')
        :type section: str
        :return: True if the line is a valid .data or .rodata declaration, False otherwise
        :rtype: bool
        """
        if "times" in line and (len(line) != 5 or line[3] != "times" or not re.match(r'^\d+$', line[4]) or not re.match(r'^\d+$', line[2])) or "times" not in line and len(line) < 3:
            print(f"INVALID {section.upper()} DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        elif (Segment_Mapper.exists_in_section(line[0].strip(":"), self.rodata_segment) or Segment_Mapper.exists_in_section(line[0], self.data_segment) or Segment_Mapper.exists_in_section(line[0], self.bss_segment)):
            print(f"Variable {line[0]} already declared. Exiting program on a SyntaxError...")
            return False
        elif not Segment_Mapper.valid_variable_name(line[0]):
            print(f"INVALID VARIABLE NAME {line[0]} AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        elif not Segment_Mapper.valid_size_specifier(line[1], section.lstrip("."), index):
            print(f"INVALID {section.upper()} SIZE SPECIFIER AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        elif "times" not in line and len(line) >= 3:
            for value in line[2:]:
                if not re.match(r'^\d+$', value):
                    print(f"INVALID {section.upper()} VALUE DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
                    return False
        return True
    
    def load_timed_data(self, line: list[str], index: int, section: str, current_rip: Address) -> Address:
        """
        Loads a timed data declaration into memory.

        :param line: full line of code that has a .data or .rodata timed declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :param section: name of the section being parsed ('.data' or '.rodata')
        :type section: str
        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :type current_rip: Address
        :return: updated pointer to the Address in use to store values in the Data_memory object
        :rtype: Address
        """
        times: int = int(line[2])
        number_of_bytes: int = self.SIZE_DIRECTIVES[line[3]][0]
        size: int = number_of_bytes * times
        addresses: list[Address] = []

        if section == "data":
            self.data_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.data_segment[line[0]]['addresses'] = addresses
        else:
            self.rodata_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.rodata_segment[line[0]]['addresses'] = addresses
        Segment_Mapper.write_section_to_memory(self.memory, times, number_of_bytes, addresses, current_rip, value=line[4])
        current_rip += size
        return current_rip  

    def load_multiple_data(self, line: list[str], index: int, section: str, current_rip: Address) -> Address:
        """
        Loads a multiple data declaration into memory.

        :param line: full line of code that has a .data or .rodata multiple declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :param section: name of the section being parsed ('.data' or '.rodata')
        :type section: str
        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :type current_rip: Address
        :return: updated pointer to the Address in use to store values in the Data_memory object
        :rtype: Address
        """
        number_of_bytes: int = self.SIZE_DIRECTIVES[line[1]][0]
        size: int = number_of_bytes * (len(line) - 2)
        addresses: list[Address] = []

        if section == "data":
            self.data_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.data_segment[line[0]]['addresses'] = addresses
        else:
            self.rodata_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.rodata_segment[line[0]]['addresses'] = addresses

        for i in range(2, len(line)):
            Segment_Mapper.write_section_to_memory(self.memory, 1, number_of_bytes, [current_rip], current_rip, value=line[i])
            current_rip += number_of_bytes
        return current_rip 
    
    def load_single_data(self, line: list[str], index: int, section: str, current_rip: Address) -> Address:
        """
        Loads a single data declaration into memory.

        :param line: full line of code that has a .data or .rodata single declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :param section: name of the section being parsed ('.data' or '.rodata')
        :type section: str
        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :type current_rip: Address
        :return: updated pointer to the Address in use to store values in the Data_memory object
        :rtype: Address
        """
        number_of_bytes: int = self.SIZE_DIRECTIVES[line[1]][0]
        size: int = number_of_bytes
        addresses: list[Address] = []

        if section == "data":
            self.data_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.data_segment[line[0]]['addresses'] = addresses
        else:
            self.rodata_segment[line[0]]['size'] = size
            for i in range(size):
                addresses.append(current_rip + i)
            self.rodata_segment[line[0]]['addresses'] = addresses

        Segment_Mapper.write_section_to_memory(self.memory, 1, number_of_bytes, addresses, current_rip, value=line[2])
        current_rip += size
        return current_rip


    # ------------------------------
    # section .bss related methods
    # ------------------------------

    def load_bss(self, current_rip: Address, index: int) -> Address:
        index += 1
        while(self.memory_list[index][0] != "section" or index >= len(self.memory_list)):
            tokens: list[str] = self.memory_list[index]
            if not self.bss_format_validation(tokens, index):
                sys.exit(-2)
            times: int = int(tokens[2])
            number_of_bytes: int = self.SIZE_DIRECTIVES[tokens[1]][0]    
            size: int = number_of_bytes * times
            self.bss_segment[tokens[0]]['size'] = size

            addresses: list[Address] = []
            for i in range(size):
                addresses.append(current_rip + i)

            self.bss_segment[tokens[0]]['addresses'] = addresses
            Segment_Mapper.write_section_to_memory(self.memory, times, number_of_bytes, addresses, current_rip)   # BSS is always uninitialized (0)
            current_rip += size
            index += 1
        return current_rip

    def bss_format_validation(self, line: list[str], index: int) -> bool:
        """
        Validates the format of a .bss declaration line.

        :param line: full line of code that has a .bss declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :return: True if the line is a valid .bss declaration, False otherwise
        :rtype: bool
        """

        if len(line) != 3:
            print(f"INVALID BSS DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        elif (Segment_Mapper.exists_in_section(line[0].strip(":"), self.rodata_segment) or Segment_Mapper.exists_in_section(line[0], self.data_segment) or Segment_Mapper.exists_in_section(line[0], self.bss_segment)):
            print(f"Variable {line[0]} already declared. Exiting program on a SyntaxError...")
            return False
        elif not Segment_Mapper.valid_variable_name(line[0]):
            print(f"INVALID VARIABLE NAME {line[0]} AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        elif not Segment_Mapper.valid_size_specifier(line[1], "bss", index):
            print(f"INVALID BSS SIZE SPECIFIER AT LINE {index}. Exiting program on a SyntaxError...")
            return False 
        elif not re.match(r'^\d+$', line[2]):
            print(f"INVALID BSS SIZE DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        return True      
        

    # ------------------------------
    # section .text related methods
    # ------------------------------

    def load_text(self, current_rip: Address ,index: int) -> None:               
        """
        Takes care of .text components (methods labels and constants) parsing as well as validation of the start declaration
        
        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :type current_rip: Address
        :param index: index to the line of code 
        :type index: int
        """
        index += 1
        tokens: list[str] = self.memory_list[index]
        validity: int = self.find_start(tokens, self.memory_list[index + 1])
        if (validity == 1 or validity == -1):
            print(f"NO VALID GLOBAL {self.valid_start} DECLARATION FOUND. Exiting program...")
            sys.exit(1)
        index += 1 # Move index to the line after the start declaration
        self.rip = index # Set instruction pointer to the line after the start declaration
        self.fetch_labels(index)
        # Exit validation is verified while running
    
    def find_start(self, line: list[str], next_line: list[str]) -> int:
        """
        Validates the existence of a valid start declaration

        :param line: List of words of a line of code where a start declaration is expected
        :type line: list[str]
        :param next_line: List of words of the line of code following the expected start declaration
        :type next_line: list[str]
        :return: 0 if a valid start declaration is found, 1 if no valid start declaration is found, -1 if no global declaration is found
        :rtype: int
        """
        if line[0] != "global":
            return -1   # Partial error (meaning no global found and possibly wrong line was passed)
        elif line[1] != self.valid_start or next_line[0] != self.valid_start + ":":
            return 1    # Complete error (no valid start passed)
        else: return 0
        
    def fetch_labels(self, index: int) -> None:

        """
        Takes care of the label initialization with all labels present in the code passed to the execution.\n
        Also verifies if any of the lines is a constant declaration and redirects the execution to the appropriate method

        :param index: starting line (Must have a global start declaration)
        :type index: int
        """

        while index < len(self.memory_list):
            line: list[str] = self.memory_list[index]
            if (Segment_Mapper.is_constant(line)):
                self.load_constant(line, index)
                index += 1
                continue
            elif len(line) == 1 and line[0].endswith(":"):
                if (Segment_Mapper.exists_in_section(line[0], self.labels)):
                    print(f"Label {line[0]} is duplicate on line {index}. Exiting program on a SyntaxError...")
                    sys.exit(2)
                else:
                    self.labels[line[0]] = index
            index += 1




    # ------------------------
    # Constant related methods
    # ------------------------
    
    def is_valid_constant_declaration(self, line: list[str], index: int) -> bool:
        """
        Verifies if a constant declaration is valid.
        
        :param line: full line of code that has a constant declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :return: True if the constant declaration is valid, False otherwise
        :rtype: bool
        """
        # allowed formats:
            # <label> equ/EQU <value>
            # <label> equ/EQU $-<data/rodata label>     # it's important to not leave spaces between $ and -
        
        if len(line) < 3 or line[1] != "equ" and line[1] != "EQU":
            print(f"INVALID CONSTANT DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        
        elif len(line) > 3:
            print(f"INVALID CONSTANT DECLARATION AT LINE {index}.\n Please dont leave extra spaces between components. Size declarations should not have spaces between '$', '-' and the label.\n Exiting program on a SyntaxError...")
            return False
        
        elif Segment_Mapper.exists_in_section(line[0], self.data_segment) or Segment_Mapper.exists_in_section(line[0], self.rodata_segment) or Segment_Mapper.exists_in_section(line[0], self.bss_segment) or Segment_Mapper.exists_in_section(line[0], self.constants):
            print(f"INVALID CONSTANT DECLARATION AT LINE {index}. Label {line[0]} already in use. Exiting program on a SyntaxError...")
            return False
        elif not Segment_Mapper.valid_variable_name(line[0]):
            print(f"INVALID CONSTANT NAME {line[0]} AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        
        elif Segment_Mapper.has_size_calculation(line) and not self.valid_size_calculation(line, index):
            return False
        elif not re.match(fr'^{Segment_Mapper.IMMEDIATE_VALUE_PATTERN}$', line[2]) and not Segment_Mapper.has_size_calculation(line):
            print(f"INVALID CONSTANT DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        return True
    
    def valid_size_calculation(self, line: list[str], index: int) -> bool:
        """
        Verifies that the size calculation is valid.
        
        :param line: full line of code that has a constant declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        :return: True if the size calculation is valid, False otherwise
        :rtype: bool
        """
        if not re.match(r'^\$-\w+$', line[2]):
            print(f"INVALID CONSTANT DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")
            return False
        label = line[2][2:]  # Extract label after '$-'
        if not (Segment_Mapper.exists_in_section(label, self.data_segment) or Segment_Mapper.exists_in_section(label, self.rodata_segment)):
            print(f"Invalid label used in {line[0]} declaration at line {index}. {label} is not a usable label. Exiting program on a SyntaxError...\n")
            return False
        return True        
                

    def load_constant(self, line: list[str], index: int) -> None:
        """
        Takes care of constant storing
        
        :param line: full line of code that has a constant declaration
        :type line: list[str]
        :param index: number of that line of the code
        :type index: int
        """
        if not self.is_valid_constant_declaration(line, index):
            sys.exit(-3)
        self.constants[line[0]]['line'] = index
        if Segment_Mapper.has_size_calculation(line):
            variable: str = line[len(line)-1]
            value: int | str = self.get_size_constant_value(variable, index, line[0])
        else:
            try:
                value: int | str = self.get_constant_value(line[2], index)
            except ValueError as e:
                print(e)
                sys.exit(-3)
        self.constants[line[0]]['value'] = value    # Only values not passed as bytes

    def get_size_constant_value(self, variable: str, index: int, label: str) -> int | str:
        """
        Gets the number of addresses used to define the variable used to declare a constant.\n
        Should be used to get the value of size constant declarations
        
        :param variable: label of a variable to search for
        :type variable: str
        :param index: index of the declaration of the constant
        :type index: int
        :param label: label used to declare the constant
        :type label: str
        :return: number of byte addresses used in the variable declaration
        :rtype: int
        """
        if (Segment_Mapper.exists_in_section(variable, self.data_segment)):
            return int(self.data_segment[variable]['size'])  # type: ignore  (is always int)
        return int(self.rodata_segment[variable]['size'])    # type: ignore  (is always int)
    

    def get_constant_value(self, value: str, index: int) -> int | str:
        """
        Gets the value of a constant that is not declared using a size calculation of a string.
        
        :param value: value of the constant to be parsed
        :type value: str
        :return: value of the constant (int or str)
        :rtype: int | str
        :raises ValueError: If an invalid constant declaration is detected
        """
        if re.match(r'^\d+$', value):
            return int(value)
        elif re.match(r"^'.'$", value, re.DOTALL) or re.match(r'^".*"$', value):
            return value[1:-1]   # Remove quotes
        else:
            raise ValueError(f"INVALID CONSTANT DECLARATION AT LINE {index}. Exiting program on a SyntaxError...")

    # --------------------
    # STACK INITIALIZATION
    # --------------------

    # Stack layout (top to bottom):
        # |_[argument strings]
        # |_[0]
        # |_[argv pointers]
        # |_[0]
        # |_[argc] <--- stack pointer at initialize_stack return

    def initialize_stack(self, argvcount: int, argv: list[str] | None, memory: Data_Memory, stack_limit: int, stack_start: int=STACK_START) -> int:
        """
        Initializes the stack with argc and argv values as well as argument strings.

        :param argvcount: argument counter
        :type argvcount: int
        :param argv: vector of argument strings
        :type argv: list[str] | None
        :param memory: Data_Memory object used to hold the program's memory
        :type memory: Data_Memory
        :param stack_limit: maximum value the stack pointer can reach
        :type stack_limit: int
        :param stack_start: initial value of the stack pointer
        :type stack_start: int
        :return: final value of the sack pointer after the initializations
        :rtype: int
        """
        memory.stack_pointer = stack_start
        # Step 1: push argument strings
        if argv is not None:
            argv_addrs = self.push_arguments(argv)
            # Step 2: push argument pointers
            for addr in argv_addrs:
                self.memory.push(addr.to_bytes(8, "little"))
            # Step 3: push argc
            memory.push((0).to_bytes(8, "little")) 
        memory.push(argvcount.to_bytes(8, "little"))
        # Step 4: align the stack and verify its size
        self.align_stack(memory, stack_limit)
        self.check_stack_limit(memory, stack_limit)
        return memory.stack_pointer

    def push_arguments(self, argv: list[str]) -> list[int]:
        """
        Push argument strings into the stack.\n
        Returns list of addresses where each arg begins.

        :param argv: vector of argument strings
        :type argv: list[str]
        :return: list of addresses where each argument string begins
        :rtype: list[int]
        """
        addresses :list[int] = []
        for arg in reversed(argv):
            data: bytes = arg.encode('utf-8') + b'\x00'
            size: int = ((len(data)+7) // 8) * 8     # Directly pass it as a valid multiple of the stack's cell size
            self.memory.stack_pointer -= size
            addr: int = self.memory.stack_pointer
            self.memory.write_bytes(addr, size, data)
            addresses.append(addr)

        self.memory.push((0).to_bytes(8, "little"))
        return addresses

    def align_stack(self, memory: Data_Memory, stack_limit: int) -> None:
        """
        Align stack pointer to 16 bits.

        :param memory: Data_Memory object used to hold the program's memory
        :type memory: Data_Memory
        :param stack_limit: maximum value the stack pointer can reach
        :type stack_limit: int
        """
        misalignment: int = memory.stack_pointer % 16
        if misalignment != 0:
            memory.stack_pointer -= misalignment
            try:
                self.check_stack_limit(memory, stack_limit)
            except OverflowError as e:
                    print(e)
                    sys.exit(16)

    def check_stack_limit(self, memory: Data_Memory, stack_limit: int) -> None:
        """
        Check if the current stack pointer is below the minimum allowed.\n
        Raises an exception if stack overflow occurs.

        :param memory: Data_Memory object used to hold the program's memory
        :type memory: Data_Memory
        :param stack_limit: maximum value the stack pointer can reach
        :type stack_limit: int
        :raises OverflowError: if stack overflow occurs
        """
        if memory.stack_pointer < stack_limit:
            raise OverflowError(
                f"Stack overflow: stack pointer {hex(memory.stack_pointer)} "
                f"below minimum allowed {hex(stack_limit)}"
            )


    # -----------------------
    # STATIC HELPERS (might be moved onto a different file)
    # -----------------------

    @staticmethod
    def is_constant(line: list[str]) -> bool:
        """
        Verifies if a given line declares a constant

        :param line: full line of code in execution
        :type line: list[str]
        :return: True if the line defines a constant, False if it doesn't
        :rtype: bool
        """
        return "equ" in line or "EQU" in line
        
    @staticmethod
    def has_size_calculation(line: list[str]) -> bool:
        """
        Verifies if a size calculation is present in a constant declaration line   

        :param line: full line of code in execution
        :type line: list[str]
        :return: True if the line has a size calculation formula, False if it doesn't
        :rtype: bool
        """
        for kword in line:
            if "$" in kword:
                return True
        return False
    
    @staticmethod
    def exists_in_section(variable: str, section: DataSectionInfo | BssSectionInfo | LabelMap | ConstantMap) -> bool:
        """
        Verifies if a variable label matches one existing in a given section
        
        :param variable: label of a variable to search for
        :type variable: str
        :param section: section where to look for 
        :type section: DataSectionInfo | BssSectionInfo | LabelMap | ConstantMap
        :return: true if a match was found, false if it wasn't
        :rtype: bool
        """
        return variable in section
    
    @staticmethod
    def valid_size_specifier(specifier: str, section: str, index: int) -> bool:
        """
        Validates if a size specifier is valid for a given section.

        :param specifier: size specifier string for a given section
        :type specifier: str
        :param section: section name where the size specifier is used
        :type section: str
        :param index: number of that line of the code
        :type index: int
        :return: True if the size specifier is valid, False otherwise
        :rtype: bool
        """
        if specifier not in ['resb', 'resw', 'resd', 'resq'] and section == "bss":
            return False
        elif specifier not in ['db', 'dw', 'dd', 'dq'] and section in ["data", "rodata"]:
            return False
        return True
    
    @staticmethod
    def write_section_to_memory(memory: Data_Memory, times: int, specifier: int, addresses: list[Address], current_rip: Address, value: int | str=0) -> None:
        """
        Writes a section to memory with a given initial value.

        :param memory: Data_Memory object used to hold the program's memory
        :type memory: Data_Memory
        :param times: number of times to write the section
        :type times: int
        :param specifier: size specifier for the section (1,2,4,8)
        :type specifier: int
        :param addresses: list of addresses where to write the section
        :type addresses: list[Address]
        :param current_rip: pointer to the Address in use to store values in the Data_memory object
        :type current_rip: Address
        :param value: initial value to write into the section
        :type value: int | str
        """
        if isinstance(value, str):
            encoded_value: bytes = (value.encode())[:specifier].ljust(specifier, b'\x00')
            for i in range(times):
                memory.write_bytes(current_rip + i*specifier, specifier, encoded_value)
        else:
            byte_value: bytes = value.to_bytes(specifier, "little")
            for i in range(times):
                memory.write_bytes(current_rip + i*specifier, specifier, byte_value)

    
    @staticmethod
    def valid_variable_name(name: str) -> bool:
        """
        Validates if a variable name is valid.

        :param name: variable name to validate
        :type name: str
        :param index: number of that line of the code
        :type index: int
        :return: True if the variable name is valid, False otherwise
        :rtype: bool
        """
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name.strip(":")):
            return False
        return True