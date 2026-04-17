#ifndef OPERATIONS_H
#define OPERATIONS_H

#include "../include/memory_eng.h"
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

// Standard instruction funtion signature alias
typedef void (*InstructionFunc)(Info *);


// ---------------------------------------------------
// Prototypes
// ---------------------------------------------------

// Operand management prototypes
Info* create_operand_state ();
void get_operand_info(Info *current_instruction_state, char *operand, int address, int value, int size, char *op_type);
void set_instruction(Info *current_instruction_state, char *instruction);
void clean(Info *current_instruction_state);
void free_pointer (Info* ptr);
// Instruction dispatching prototypes
void dispatch(Info *current_instruction_state);
// Data Path funtions prototypes
void exec_cmp(Info *s);
void exec_jmp(Info *s);
void exec_jb(Info *s);
void exec_jl(Info *s);
void exec_ja(Info *s);
void exec_jg(Info *s);
void exec_je(Info *s);
void exec_jne(Info *s);
void exec_jz(Info *s);
void exec_js(Info *s);
void exec_jc(Info *s);
void exec_jo(Info *s);
// ALU funtions prototypes
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
// FPU funtions prototypes
// (TODO)



#endif // OPERATIONS_H
