from data_memory import Data_Memory
from storage import Storage
import sys

### NOT IN USE

class Process_Loader:

    """
    TODO
    """

    TEXT_BASE = 0x400000
    RODATA_BASE = 0x500000
    DATA_BASE = 0x600000
    BSS_BASE = 0x700000
    STACK_START = 0x7fffffffe000

    def __init__(self, file_name: str, argvcount: int=0, argv: list[str] | None =None, stack_limit: int=0x7fff00000000):
        self.stack_limit :int = stack_limit

        # Memory used in the execution of the program
        # Will start at the start label
        self.memory_list :list[list[str]]= []

        #Should only store addresses as actually memory values are stored in Data_Memory class
        self.rodata_segment :dict[str, str] = {}
        self.data_segment :dict[str, str]= {}
        self.bss_segment :dict[str, dict[str, int | list[int]]]= {}
        self.labels :dict[str, int]= {}

        # Stores constant values
        self.constants :dict[str, int]= {}

        # Will be changed later when the start label is found
        self.pc = 0

        self.file_name :str = Storage.convert_to_json(file_name)
        self.stack_pointer :int = self.initialize_stack(argvcount, argv)
        self.memory :Data_Memory = self.load_program(self.file_name)
        self._parse_sections()


    # -----------------------
    # PROGRAM LOADING
    # -----------------------
    def load_program(self, file_name: str) -> Data_Memory:
        program_lines :list[str]= Storage.load_file_lines(file_name)
        program : list[list[str]]= []
        for line in program_lines:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if ";" in line:
                line = line.split(";")[0]
            instruction :list[str] | str= line.replace(",", " ").split()
            program.append(instruction)     #Ignorable typeError
        self.memory_list = program
        Storage.save_file(file_name, program)
        # Initialize memory with exact size
        print("[DEBBUG]: attributed a memory object to this insance of the class")
        return  Data_Memory(Process_Loader.RODATA_BASE, stack_start=self.STACK_START)
        

    def _parse_sections(self):
        pc :int= 0
        while pc < len(self.memory_list):
            # REMOVER
            print(f"ENTROU NO LOOP {pc}\n")
            if self.memory_list[pc][0] == "section" and self.memory_list[pc][1] == ".rodata":
                pc += 1
                address :int= Process_Loader.RODATA_BASE
                while pc < len(self.memory_list) and self.memory_list[pc][1] not in (".data", ".bss", ".text"):
                    address = self.allocate_segments(self.rodata_segment, pc, address)
                    pc += 1

            elif self.memory_list[pc][0] == "section" and self.memory_list[pc][1] == ".data":
                pc += 1
                address = Process_Loader.DATA_BASE
                while pc < len(self.memory_list) and self.memory_list[pc][1] not in (".rodata", ".bss", ".text"):
                    address = self.allocate_segments(self.data_segment, pc, address)
                    pc += 1

            elif self.memory_list[pc][0] == "section" and self.memory_list[pc][1] == ".bss":
                pc += 1
                address = Process_Loader.BSS_BASE
                while pc < len(self.memory_list) and self.memory_list[pc][1] not in (".data", ".rodata", ".text"):
                    tokens :list[str]= self.memory_list[pc]
                    variable :str= tokens[0].rstrip(":")
                    size :str | int= tokens[1]
                    try:
                        quantity :int= int(tokens[2].strip())
                    except ValueError:
                        raise ValueError(f"Invalid quantity specifier '{tokens[2]}' for variable '{variable}' in bss segment.")
                    size = size.strip(" ")
                    if (size not in ["resb","resw","resd","resq"]):
                        raise ValueError(f"Invalid size specifier '{size}' for variable '{variable}' in bss segment.")
                    size = self._unit_size(size)
                    addresses = [address + i * size for i in range(quantity)]
                    self.bss_segment[variable] = {'size': size, 'address': addresses}  #initializes the variable with quantity of 0s
                    for addr in addresses:
                        self.memory.write_bytes(addr, size, (0).to_bytes(size, "little"))      #Unknown error raised, ignorable
                    pc += 1
                    address += size * quantity


            elif self.memory_list[pc][0] == "section" and self.memory_list[pc][1] == ".text":
                if (self.memory_list[pc + 1][0] != "global" and self.memory_list[pc + 1][1] != "_start"):
                    print("MISSING 'global _start' DECLARATION ON TEXT SEGMENT!\nRaising SyntaxError...\n") #verify that the program has a global _start declaration (necessary for execution start)
                    print("Program forced exit on a SyntaxError.")
                    sys.exit(-1)
                pc += 1                            
                while pc < len(self.memory_list):
                    if (self.memory_list[pc][0].endswith(":") and len(self.memory_list[pc]) == 1):  #detect labels (which start with _ )
                        label = self.memory_list[pc][0].strip(":").strip(" ")
                        if label == "_start":
                            # REMOVER 
                            print("\nENCONTROU UM START")
                            self.pc = pc
                            # REMOVER
                            print(f"self.pc setted for {pc + 1}\n")
                        if label in self.labels:
                            print(f"DUPLICATE LABEL FOUND: {label}\nRaising SyntaxError...\n")
                            print("Program forced exit on a SyntaxError.") 
                            sys.exit(-1)
                        else:
                            self.labels[label] = pc 
                    pc += 1
        # REMOVER
        print(f"\nMEMORIA COMPLETA. pc:{pc + 1}\n")

    def allocate_segments(self, section: dict[str, str], pc: int, address: int) -> int:
        # For the Process_Loader address instances
        if "equ" in self.memory_list[pc]:
            if "times" in self.memory_list[pc]:
                print(f"Invalid variable '{self.memory_list[pc][0]}' inicialization.\nHaulting execution.")
                print("Program forced exit on a SyntaxError.")
                sys.exit(-1)
            tokens :list[str]= self.memory_list[pc]
            variable :str= tokens[0].rstrip(":")
            value :str= tokens[2]
            number_values = 1
            size = None
            if value.startswith("$-"):   #if the value calculated string length or any other type of calculation
                value = value.strip("$-").strip(" ")  #assuming the format is always $-variable,     the $- part
                
                value_size = section[value]['size'] #get the length of the variable in rodata segment
                length = len(value)
                if isinstance(value, int):
                    value = value_size
                else:
                    value = length*value_size
                self.constants[variable] = {'value': value, 'pc': pc}
            else:
                value = value.strip(" ")
                self.constants[variable] = {'value': value, 'pc': pc}
        else:
            if "times" in self.memory_list[pc]:
                tokens = self.memory_list[pc]
                variable = tokens[0].rstrip(":")
                if tokens[1] != "times":
                    print(f"Invalid variable '{self.memory_list[pc][0]}' inicialization.\nHaulting execution.")
                    print("Program forced exit on a SyntaxError.")
                    sys.exit(-1)
                number_values = tokens[2]
                if (tokens[3] not in ["db","dw","dd","dq"]):
                    raise ValueError(f"Invalid size specifier '{tokens[1]}' for variable '{variable}' in rodata segment.")
                size = self._unit_size(tokens[3]) * 8   #size in bits
                value = [tokens[4]]*number_values
            else:
                tokens = self.memory_list[pc]
                variable = tokens[0].rstrip(":")
                value = tokens[2:].split(",")
                number_values = len(value)
                if (tokens[1] not in ["db","dw","dd","dq"]):
                    raise ValueError(f"Invalid size specifier '{tokens[1]}' for variable '{variable}' in rodata segment.")
                size = self._unit_size(tokens[1]) * 8   #size in bits
            if number_values > 1:
                # List comprehention for all addresses of all elements of the vector
                addresses = [address + i * size for i, _ in enumerate(value)]
                section[variable] = {'size': size, 'address': addresses}
            else:
                section[variable] = {'size': size, 'address': address}

            # For the Data_Memory value instances
            if number_values == 1:
                if isinstance(value, int):
                    data_bytes = value.to_bytes(section[variable]['size'], 'little')
                elif isinstance(value, str):
                    data_bytes = value.encode('utf-8') + b'\x00'
            else:                        
                for i,val in enumerate(value):
                    data_bytes = int(val).to_bytes(section[variable]['size'], 'little')
                    self.memory.write_bytes(section[variable]['address'][i], size, data_bytes)
            address += number_values*size
        return address
    

    def _unit_size(self, size_str: str) -> int:
        if size_str in ['resb', 'db']: return 1
        elif size_str in ['resw', 'dw']: return 2
        elif size_str in ['resd', 'dd']: return 4
        elif size_str in ['resq', 'dq']: return 8
        else: 
            print("Invalid sized passed. Raising InvalidSizeException...\n  Program exited on InvalidSizeException")
            sys.exit(-1)

    # --------------------
    # STACK INITIALIZATION
    # --------------------
    def initialize_stack(self, argvcount: int, argv: list[str] | None, env: list[str] | None = None, stack_start: int=STACK_START) -> int:
        """
        Build the initial process stack.
        As of right now it's ignoring environmets
        Stack layout (top to bottom):
            [argument strings]
            [0]
            [argv pointers]
            [0]
            [argc]
        """
        self.memory.stack_pointer = stack_start
        # Step 1: push argument strings
        argv_addrs = self.push_arguments(argv)
        

        # Step 2: push argument pointers
        for addr in argv_addrs:
            self.memory.push(addr.to_bytes(8, "little"))

        # Step 3: push argc
        self.memory.push((0).to_bytes(8, "little"))     # Rever se devo manter
        self.memory.push(argvcount.to_bytes(8, "little"))

        # Step 4: align the stack and verify its size
        self.align_stack()
        self.check_stack_limit()

        return self.memory.stack_pointer

    def push_arguments(self, argv: list[str] | None) -> list[int]:
        """
        Push argument strings onto the stack.
        Returns list of addresses where each arg begins.
        """
        if not argv:
            return []
        
        addresses :list[int] = []
        for arg in reversed(argv):
            data:bytes = arg.encode('utf-8') + b'\x00'
            size = ((len(data)+7) // 8) * 8     # Directly pass it as a valid multiple of the stack's cell size
            self.memory.stack_pointer -= size
            addr = self.memory.stack_pointer
            self.memory.write_bytes(addr, size, data)
            addresses.append(addr)

        self.memory.push((0).to_bytes(8, "little"))
        return addresses

    #def push_environment(self, env: list[int] | None) -> list[int]:
        """
        Push environment strings onto the stack
        Returns list of addresses for each env variable.
        """
        addresses :list[int] = []
        for entry in reversed(env):
            data = entry.encode('utf-8') + b'\x00'
            size = ((len(data)+7) // 8) * 8     # Directly pass it as a valid multiple of the stack's cell size
            self.memory.stack_pointer -= size
            addr = self.memory.stack_pointer
            self.memory.write_bytes(addr, size, data)
            addresses.append(addr)
            self.memory.push(0)
        return addresses
    
    def align_stack(self) -> None:
        """
        Align stack pointer to 16 bytes.
        """
        misalignment = self.memory.stack_pointer % 16
        if misalignment != 0:
            self.memory.stack_pointer -= misalignment
            self.check_stack_limit()

    def check_stack_limit(self) -> None:
        """
        Check if the current stack pointer is below the minimum allowed.
        Raises an exception if stack overflow occurs.
        """
        if self.memory.stack_pointer < self.stack_limit:
            raise OverflowError(
                f"Stack overflow: stack pointer {hex(self.memory.stack_pointer)} "
                f"below minimum allowed {hex(self.stack_limit)}"
            )
    
    # --------------------
    # HELPERS
    # --------------------


    
