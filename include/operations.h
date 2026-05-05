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

// Operand management prototypes
Info* create_operand_state ();
void get_operand_info (Info *current_instruction_state, char *operand, long long address, long long value, char size, char *op_type, char visual_rep);
void set_instruction(Info *current_instruction_state, char *instruction);
void set_registers_ref (Info *current_state, CPURegs *r);
void set_result_info (Info *current_state);
int clean(Info *current_instruction_state);
void free_pointer (Info* ptr);

// Instruction dispatching prototypes
void dispatch(Info *current_instruction_state);

// Data Path functions prototypes
void exec_cmp(Info *s);

// ALU functions prototypes
void exec_add(Info *s);
void exec_adc(Info *s);
void exec_sub(Info *s);
void exec_sbb(Info *s);
void exec_inc(Info *s);
void exec_dec(Info *s);
void exec_and(Info *s);
void exec_or(Info *s);
void exec_xor(Info *s);
void exec_not(Info *s);
void exec_neg(Info *s);
void exec_xchg(Info *s);

// FPU functions prototypes
// (TODO)

#endif // OPERATIONS_H
