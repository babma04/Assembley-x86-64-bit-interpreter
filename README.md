# Assembly x84 64 bit python Interpreter
A simple assembly x84 64-bit interpreter with sequencial execution and error detection.


## About the Project

This projects aims to simulate the behaviour of a cpu while executing simple Assembly x86 64bit code with Intel syntax.

It is still in a very inicial state. It can only interprete and execute basic ALU aritmetic and logic instructions
In order to execute this projects goal, a cpu class was implemented simulating cpu components: general purpose registers, memory with no type of respective address, instruction pointer and a memory slot for the instruction, flag registers with the 4 basic operations flags, segments for each of the sections in a asm file, a simple fetch-decode/interprete-execute system and a load a store file system (Class Storage). To be able to use registers in their correct size a simple register system was also implemented (Class Register64).

In order to detect if the correct operand type was passed or if it exists in the first place a specific method was implemented able to be used in scalling this program to enable any operand direct memory addressing, but still no other type of memory addressing.

The program also has a method responsible for detecting syscalls and executing them correctly but currently only exit calls are working as expected.

---

## **Implementation and Decisions**

## **C support files implementation**

Each of this files is composed by strutures that define core data holder for the methods inside them. Each of those should be stored in a pointer given by its specific method.  
The memory_eng.c and registers.c file should never replace pointers, but operations.c can replace or clean its pointer.

---

### **Operations**

This file defines the structure that holds each operand information, result information and Instruction information.  

#### Operand struct

This struct holds all usefull operand info for the operation in place. It takes a 64 bit `address`, if any, for maximum representability of the addressing space, a 64 bit `value`, for the same reason, an `operand type` identifier that should be either **memory**, **register**, or **imidiate** and will affect the handelying of such value. It also takes a `size` as a single char that should represent the size of the operand in place: 1, 2, 4, or 8; and it also takes a `visual representation` identifier as a char for the way this operand should be represented visualy in a print statement: 0 for numerical representation, 1 for textual (UTF8) representation.  

#### Other important structs

This file also defines an `Info` struct that takes a char list for the operation, two `Operand` structs for each operand, a `CPURegs` struct for the registers in use, and an `Operand` struct for the result.  

#### Dispatcher

Aside from all the getters and setters for the Info needed for the instruction to be executed, written in memtoy or in the result struct, there is also a lookup table used in the `dispatch` method to decide what execution method to call for the given instruction char*. This is very helpfull since it eliminates the need for multiple if-else statements to call the correct method and **improves scalability** for future potencial supported instructions.

---

### **Registers**

This file defines each struct for register types all joint in a single register struct, `CPURegs` by the given order:  

* RAX, RBX, RCX, RDX (as unions of aliased u_int64_t to u_int8_t low and high values to simulate the last 2 bytes accessibility pattern);
* RSI, RDI, RBP, RSP (remaining union aliased registers without the last 2 byte discriminate access);
* R8-15;
* RFLAGS (32 bit flags register);

A whole set of getters and setters methods are provided both for the general purpose registers as well as for the flags register, allowing to change individual flag values, set the trap flag for the debbuger, and read or write the flags manually.

---

### **Memory**

This file defines the `paging-like struture` that holds memory values addresses to real virtual memory, allowing for page criation if needed, page criation blocking for safe read/write operations.  

This mechanism works as a simulated virtual memory in this paging system, attributing to a given address a decoded address to this struct. Because all write/read calls run first through a private address decoder, an given address will always correspond to the same decoded address what enables to store data more efficintly without saving this decoded addresses. This way only virtualized addresses are in need to be stored/calculated and its value will be written onto this paging struct keeping data stored more efficintly.

---

### Main parser and executer

**TODO**


## Sections Parsing
(TODO)

## Memory handelying:
### Writing Memory:
Memory writing is handeled by the Data_Memory class. This class encapsulates the bytearray structure the system RAM and is used throughout the execution context to fetch and write values.  

#### Data normalization occurs in two stages:
1. **Caller Level**: The initial class determines the target size and parsed the desired data to bytes.

2. **Definitive Level**: The Data_Memory class ensures the bytes object perfectly match the requires hardware size before the write occurs.

#### Structure of processed values to be written: 
- **Initial Value:**
    - int 0x1234 (Size: 4 bytes)
- **Byte Conversion:**
    - b'\34\12' (Length: 2)
- **Final Processed Data:**
    - b'\34\12\00\00' (Length: 4)

#### Little endian implementation:
    Byte writing will change the order by which values appear in the variable to be able to write them in a little endian format at the bytarray. In this format, and following the given example, the byte b'\34' will be written first at the base address and the following bytes of the processed data will be written in higher level addresses in a sequencial order.

### Reading Memory:
Memory reading will follow the same structure of the writing, returning the first value read at the first position of the bytes variable.

#### Structure of read values:
- **Address to Read and Number of Bytes**:
    - 0x4001 (Size: 4 bytes)
- **Value Returned:**
    - b'\34\12\00\00'
- **Real Value:**
    - 0x1234

#### Reading Logic:
    Reading will always take a start address and a number of bytes to read. This method then will start reading bytes at the given address and stop only when the number of bytes above that address is met.

---

## Code format and syntax references

### Allowed declarations

All type of allowed declarations for a standard compiler for the .rodata, .data and .bss sections are allowed.

Constants declarations are a bit more nuanced:

    - Allowed declarations include:

        - Standard declarations:

            - <constant_uppercased_label> equ: <integer_value>;
            - <constant_uppercased_label> equ: <string_size_calculation>;
        
        - String declarations:

            - <constant_uppercased_label> equ: '<character_value>';
            - <constant_uppercased_label> equ: "<string_value>";

### Operand syntax rules

    - Operands writen with different components should have no spaces in between each component of the expression:

        ex.:
        - What to avoid: [rbx + 4 * 1] or CONSTANT + 4
        - Correct version: [rbx+4*1]   or CONSTANT+4

    - If an operand is an immidiate value it should always be simplified to the maximum extent possible avoiding complex nested paranteses expresions:

        ex.: 
        - What to avoid: ((4+3+1)*4 + 6 + (7 + 8)*2)
        - Correct version: 58

    - All immidiate values should be integer values (not decimal point values)

        ex.:
        - What to avoid: mov eax, 3.14
        - Correct version: mov eax, 3

---

### Exit codes status reference

Valid exit codes:

    code: 0
        - status: successful exit
    code: 109101  (aka "me" in ascii)
        - status: unsuccessful exit due to a sofware bug
    code: 1
        - status: unsuccessful exit due to not finding an entry point to the program in .text parsing
    code: 2
        - status: unsuccessful exit due to finding a duplicated label declaration in .text parsing
    code: 16
        - status: unsuccessful exit due to stack overflow is detected (stack exceeds its allowed size)
    code: -1
        - status: unsuccessful exit due to incorrect .data/.rodata  format detected in parsing phase
    code: -2
        - status: unsuccessful exit due to incorrect .bss format detected in parsing phase
    code: -3
        - status: unsuccessful exit due to incorrect constant declaration format detected

---

## Folder Structure

    CPU_SIMULATOR/
    |
    |-- bridges/            # Bridges between the c files and the python classes
    |    |-- __init__.py
    |    |-- data_memory.py
    |    |-- register_manager.py
    |-- helpers/            # Helpers for storage and types definition in python
    |    |-- __init__.py
    |    |-- my_types.py
    |    |-- storage.py
    |-- include/            # c headers
    |    |-- memory_eng.h
    |    |-- registers.h
    |    |-- operations.h
    |-- src/                # c implementations
    |    |-- memory_eng.c
    |    |-- registers.c
    |    |-- operations.c
    |-- tests/              # tests (TODO)
    |-- alu.py
    |-- control_unit.py
    |-- data_path.py
    |-- fpu.py
    |-- segment_mapper.py
    |-- main.py
    |-- .gitignore
    |-- Makefile
    |-- README.md

---

## Usage

This program can take up to one command-line argument providing a path to a asm file. If no file is detected or if an invalid file is detected the program will prompt for a valid file until the execution is haulted or untill one valid path is provided.

    ex:
    $py main.py example.asm 
    $py main.py "~/user-name/remaining_folders/example.asm"

---

## Roadmap

### Planned improvement

    - Implement FPU operations and logic operations not yet available (rotations and shifts);

    - Reforcing the syscalls supported by the program;

    - Enable any type of memory addressing inplementing a more robust memory system with usable addresses;

    - Implement a stack system and enable argument passing for the execution of the python program;

    - Implement a debugging execution type with gdb commands and one instruction at a time execution using the trap flag mechanism already implemented;


## Contributors

### - João Louro @FCUL comp. science year 1
