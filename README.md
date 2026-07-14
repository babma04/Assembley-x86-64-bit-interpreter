# Assembly x84 64 bit python Interpreter
A simple assembly x84 64-bit interpreter with sequential execution and error detection.


## About the Project

This projects aims to simulate the behavior of a cpu while executing simple Assembly x86-64bit code with Intel syntax.
In order to execute this projects goal, cpu component classes were implemented simulating its behavior:

- registers: general purpose register, fpu registers and the flag register;
- manageable memory memory allocation interface built using the standard x86 paging system;
- an operation dispatcher that directs the execution flow the the desired operation

Python owns parsing and control flow. C owns the actual machine state and the raw execution of each operation. The two talk to each other through a thin ctypes bridge layer.

During the parsing stage of the execution there is a light checkup on syntax correctness trying to match expected syntax cases, code correctness like operand count or type.
During each interpretation execution more validation is run to make sure the current state is valid for the instruction being executed

This projects offers two main interfaces:

- A main.py script that run the code directly
- A class with similar behavior as main that enables you to get the state of the program from its object before shuting down

---

## Pipeline

```
 .asm file
     │
     ▼
┌─────────────────────────┐
│  segment_mapper.py      │   Phase 1 — mapping
│  parse → validate → map │   (runs once, before execution)
└─────────────────────────┘
     │  symbol table, memory layout
     ▼
┌─────────────────────────┐
│ control_unit.py         │  Phase 2 — execution loop
│fetch → decode → dispatch│ (runs until exit / last instruction)
└─────────────────────────┘
     │  decoded instruction + operands
     ▼
┌─────────────────────────┐
│ FUs/ (one class per     │
│ instruction)            │
└─────────────────────────┘
     │  calls into C
     ▼
┌─────────────────────────┐        ┌───────────────────────────┐
│ bridges/ (ctypes)       │───────>|   execution/ (C)          |
│ register_manager.py     │        │ registers.c / memory_eng.c│
│ data_memory.py          │        │ operations.c              │
└─────────────────────────┘        └───────────────────────────┘
     │
     ▼
 CPU state (registers, flags, memory) updated
```

## Project layout
 
```
CPU_SIMU/
├── parsing/
│   ├── segment_mapper.py     # Phase 1: parse, map to memory, validate
│   └── control_unit.py       # Phase 2: the execution loop
├── FUs/                      # One class per instruction/instruction family
├── bridges/
│   ├── register_manager.py   # ctypes -> libreg.so
│   └── data_memory.py        # ctypes -> libmmu.so
├── execution/
│   ├── include/              # registers.h, memory_eng.h, operations.h
│   └── src/                  # registers.c, memory_eng.c, operations.c
├── lib/                      # libreg.so, libmmu.so, liboperations.so (built)
├── build/                    # intermediate .o files (built)
├── tests/
|   ├── asm/                  # dir holding example asm file for testing  
│   ├── bridge/               # Python bridge test suite
│   │   ├── test_register_manager.py
│   │   ├── test_data_memory.py
│   │   └── test_integration.py
|   ├── storage_tests/        # Python storing system test suite
│   └── execution_tests/      # C-level tests
├── program_cache/            # dir holding processed json files being used
├── helpers/
├── conftest.py
├── Makefile
├── interpreter.py            # programs class with similar behavior as main
└── main.py
```

## Building
 
```bash
make          # builds lib/libreg.so, lib/libmmu.so, lib/liboperations.so
make test     # builds and runs the C-level test binaries
make clean    # removes build/, lib/, and test binaries
```
 
## Testing

Python-side tests, independent of whether the C libraries are built. In case they are needed and are not built will skip tests.
Execute from the root:

```bash
pytest tests/bridge/ -v
```

## Usage

This program can take up to one command-line argument providing a path to a asm file. If no file is detected or if an invalid file is detected the program will prompt for a valid file until the execution is halted or until one valid path is provided. Ex:
```bash
$py main.py tests/asm/example.asm 
```
---

## **Implementation and Decisions**

Interpreting a `.asm` file happens in two phases:
 
**1. Mapping (`parsing/segment_mapper.py`)**
Reads the assembly file once, before anything executes. It walks each
section, maps variables and instructions into simulated memory, builds the
label/symbol table, and validates that the file is well-formed — checking
syntax and instruction structure so that malformed input is caught up front
rather than failing mid-execution.
 
**2. Execution (`parsing/control_unit.py`)**
The actual execution loop. Starting from the beginning of the program, it
interprets one instruction at a time, running until it hits an exit call (or
the last executable instruction). For each instruction, it resolves operands,
dispatches to the matching Functional Unit, and lets the C side carry out the
real side effects — register writes, memory writes, flag updates — through
the bridge layer.  

**Functional Units (`FUs/`)**
Each instruction (`add`, `mov`, `cmp`, `xor`, ...) has a corresponding FU
class. The control unit resolves which FU handles a given instruction and
hands it the decoded operands; the FU is responsible for reading its inputs,
invoking the correct C operation, and writing the result back.
**The bridge layer (`bridges/`)**
Python can't touch raw CPU state directly, so every register read/write and
every memory access goes through `ctypes` into compiled C:

- `register_manager.py` → `lib/libreg.so` — register file, sub-register
  resolution (`rax`/`eax`/`ax`/`al`/`ah`, etc.), flags.
- `data_memory.py` → `lib/libmmu.so` — a 4-level page table for virtual
  memory, plus stack push/pop.
Both are deliberately thin: they translate calls and manage types, the actual
logic lives in C.

### Data handling

#### Data normalization occurs in two stages:

1. **Caller Level**: During the data parsing phase the data size is found and the data itself is parsed to a python bytes type for easier pre-validation.

2. **Definitive Level**: The Data_Memory class ensures the bytes object perfectly match the requires hardware size before the write occurs and calls on the c write operation to the data buffer created with the specific size.

#### Structure of processed values to be written:

- **Initial Value:**
    - int 0x1234 (Size: 4 bytes)
- **Byte Conversion:**
    - b'\34\12' (Length: 2)
- **Final Processed Data:**
    - b'\34\12\00\00' (Length: 4)

#### Little endian implementation:
Byte writing will change the order by which values appear in the variable to be able to write them in a little endian format at the bytarray. In this format, and following the given example, the byte b'\34' will be written first at the base address and the following bytes of the processed data will be written in higher level addresses in a sequential order.

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

Reading will always take a start address and a number of bytes to read. This method then will start reading bytes at the given address and stop only when the number of bytes above that address is met or a null value is found.

---

## Code format and syntax references

### Allowed declarations

All type of allowed declarations for a standard compiler for the .rodata, .data and .bss sections are allowed.

Constants declarations are a bit more nuanced. Allowed declarations include:

        - Standard declarations:

            - <constant_uppercased_label> equ: <integer_value>;
            - <constant_uppercased_label> equ: <string_size_calculation>;
        
        - String declarations:

            - <constant_uppercased_label> equ: '<character_value>';
            - <constant_uppercased_label> equ: "<string_value>";

        - Standard c constant definitions:
            - #define <constant_uppercased_label> <value>

### Operand syntax rules

    - Operands written with different components should have no spaces in between each component of the expression:

        ex.:
        - What to avoid: [rbx + 4 * 1] or CONSTANT + 4
        - Correct version: [rbx+4*1]   or CONSTANT+4

    - If an operand is an immediate value it should always be simplified to the maximum extent possible avoiding complex nested parentheses expression:

        ex.: 
        - What to avoid: ((4+3+1)*4 + 6 + (7 + 8)*2)
        - Correct version: 58

    - All immediate values should be integer values (not decimal point values)

        ex.:
        - What to avoid: mov eax, 3.14
        - Correct version: mov eax, 3

---

### Exit codes status reference

Valid exit codes:

    code: 0
        - status: successful exit
    code: 109101  (aka "me" in ascii)
        - status: unsuccessful exit due to a software bug
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

## Contributions

**Adding a new instruction**

1. Implement the operation and its flag-update logic in
   `execution/src/operations.c`.
2. Add or extend a Functional Unit in `FUs/` to decode the instruction's
   operands and call into the new operation.
3. Register the instruction in `helper/storage.Storage.initialize_instructions()` so it dispatches to
   the right FU.
4. Add coverage: a C-level test under `tests/exectuation_tests/`, and a
   Python-level test under `tests/<specific folder>/`

**Changing registers or memory internals**

1. Update the corresponding header in `execution/include/`.
2. Rebuild with `make clean && make`.
3. Re-implement and run the test suites for the all c Level implementations as they are interconnected.
4. Re-run `pytest tests/bridge/ -v` — a signature change that isn't mirrored
   in the Python `ctypes` bindings will show up here rather than as a silent
   runtime bug.

**General expectations**

- Keep C changes and their Python bindings in sync in the same change —
  a mismatch between the two is the most common source of bugs in this
  project so far.
- New behavior should come with a test at the layer it lives in: C-level
  logic gets a C test, bridge/ctypes plumbing gets a Python bridge test.
- Different tasks in the interpreter should be kept separate at separate folders and well integrated to the core parsing and execution loops.

---

## Roadmap

### Planned improvement

- Implement FPU operations and logic operations not yet available (rotations and shifts);

- Reforcing the syscalls supported by the program;

- Optimize the operands dispatch through an index array of operations instead of a loopup table

- Implement a debugging execution type with gdb commands and one instruction at a time execution using the trap flag mechanism already implemented;

---

## Contributors

### - João Louro @FCUL comp. science year 1
