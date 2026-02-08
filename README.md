# Assembly x84 64 bit python compiler
#### A simple assembly x84 64bit compiler with sequencial execution and error detector.


## About the Project
### This projects aims to simulate the behaviour of a cpu while executing simple Assembly x86 64bit code with Intel syntax.
### It is still in a very inicial state. It can only interprete and execute basic ALU aritmetic and logic instructions, with limited capabilities on memory addressing, supporting only 2nd operand memory addressing for the operations that support it. No 1st operand memory addressing and no other type of memory addressing basides direct memory addressing.
### In order to execute this projects goal, a cpu class was implemented simulating cpu components: general purpose registers, memory with no type of respective address, instruction pointer and a memory slot for the instruction, flag registers with the 4 basic operations flags, segments for each of the sections in a asm file, a simple fetch-decode/interprete-execute system and a load a store file system (Class Storage). To be able to use registers in their correct size a simple register system was also implemented (Class Register64).
### In order to detect if the correct operand type was passed or if it exists in the first place a specific method was implemented able to be used in scalling this program to enable any operand direct memory addressing, but still no other type of memory addressing.
### The program also has a method responsible for detecting syscalls and executing them correctly but currently only exit calls are working as expected.



## Usage
### This program can take up to one command-line argument providing a path to a asm file. If no file is detected or if an invalid file is detected the program will prompt for a valid file until the execution is haulted or untill one valid path is provided.

    ex:
    $py main.py example.asm 
    $py main.py "C:\Users\João Louro\Desktop\CPU simulator\example.asm"

## Code format and syntax references
### Operand syntax rules:

    - Operands writen with different components should have no spaces in between each component of the expression:
        ex.:
        - What to avoid: [rbx + 4 * 1] / CONSTANT + 4
        - Correct version: [rbx+4*1]   / CONSTANT+4
    - If an operand is an immidiate value it should always be simplified to the maximum extent possible avoiding complex nested paranteses expresions:
        ex.: 
        - What to avoid: ((4+3+1)*4 + 6 + (7 + 8)*2)
        - Correct version: 58


## Folder Structure
    project-folder/
    ├── main.py/
    ├── cpu.py/
    ├── storage.py/
    ├── register.py/
    └── README.md

## Roadmap
### Planned improvement
    - Implement FPU operations and logic operations not yet available (rotations and shifts);

    - Reforcing the syscalls supported by the program;

    - Enable any type of memory addressing inplementing a more robust memory system with usable addresses;

    - Implement a stack system and enable argument passing for the execution of the python program;

    - Implement a debugging execution type with gdb commands and one instruction at a time execution;


## Contributors
### - João Louro @FCUL comp. science year 1;