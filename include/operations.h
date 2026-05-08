#ifndef OPERATIONS_H
#define OPERATIONS_H

#include "../include/memory_eng.h"
#include "../include/registers.h"
#include <string.h>
#include <ctype.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

// Compilation: gcc -O3 -shared -o libops.so -fPIC operations.c


// --------------------------------------------------
// Structures
// --------------------------------------------------

// Operand info structures
typedef struct Operand Operand;

// Operations Info structure
typedef struct Info Info;

// Instruction Map structure
typedef struct InstructionMap InstructionMap;

// ---------------------------------------------------
// Aliases
// ---------------------------------------------------

// Standard instruction function signature alias
typedef void (*InstructionFunc)(Info *);


// ---------------------------------------------------
// Prototypes
// ---------------------------------------------------

// Pointer creation
Info* create_operand_state ();
// Pointer freeing


// Pointer freeing
void free_pointer (Info* ptr);

// Essential data structure setters
void set_registers_ref (Info *current_state, CPURegs *r);
void set_table_ref (Info *current_state, Table *t);

// Info setters 
void set_operand_info (Info *current_instruction_state, char *operand, long long address, long long value, uint8_t size, char *op_type, uint8_t visual_rep);
void set_instruction(Info *current_instruction_state, char *instruction);

// Infor cleaners
void clean(Info *current_instruction_state);

// Result getter
long long read_result(Info *current_instruction_state);

// Instruction dispatching prototypes
void dispatch(Info *current_instruction_state);

#endif // OPERATIONS_H
