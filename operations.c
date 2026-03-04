#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include "memory_eng.c"

// Compilation: gcc -O3 -shared -o libops.so -fPIC operations.c

// Structure for each alu operand's necessary info
typedef struct{
    int address;
    int value;
    int size; // 1,2,4,8
    char *op_type;
} Operand;

// To be implemented a fpu operand struct

// Structure for all necessaryu instruction info
typedef struct{
    char *instruction;
    Operand op1;
    Operand op2;
    Operand result;
} Info;
Info current_instruction_state = {0};

/**
 * Gets the pointer to the structure with the instruction info
 */
Info *get_current_state()
{
    return &current_instruction_state;
}

// Prototypes
// Operand management prototypes
void get_operand_info(char *operand, int address, int value, int size, char *op_type);
void set_instruction(char *instruction);
void clean();
// Instruction dispatching prototypes
void dispatch();
// Data Path funtions prototypes
void exec_mov(Info *s);
void exec_halt(Info *s);
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

// Standard instruction funtion signature alias
typedef void (*InstructionFunc)(Info *);
// Instructions link struct
typedef struct{
    char *instruction;
    InstructionFunc func;
} InstructionMap;
// Lookup table to match string instructions with c funtions
InstructionMap dispatch_table[] = {
    // Data Path
    {"mov",  exec_mov},  {"halt", exec_halt}, {"cmp",  exec_cmp},
    {"jmp",  exec_jmp},  {"jb",   exec_jb},   {"jl",   exec_jl},
    {"ja",   exec_ja},   {"jg",   exec_jg},   {"je",   exec_je},
    {"jne",  exec_jne},  {"jz",   exec_jz},   {"js",   exec_js},
    {"jc",   exec_jc},   {"jo",   exec_jo},

    // ALU
    {"add",  exec_add},  {"adc",  exec_adc},  {"sub",  exec_sub},
    {"sbb",  exec_sbb},  {"inc",  exec_inc},  {"dec",  exec_dec},
    {"and",  exec_and},  {"or",   exec_or},   {"xor",  exec_xor},
    {"not",  exec_not},  {"neg",  exec_neg},  {"xchg", exec_xchg}

    //FPU
    // To be completed
};
// Table size constant
#define TABLE_SIZE (sizeof(dispatch_table) / sizeof(InstructionMap))

//----------------------------------------
// Operand fetching and cleaning funtions
//----------------------------------------

/**
 * Sets the operand info in the structurer
 * 
 * @param operand Address for the sequence of charaters that define the operand to update
 * @param address Address of the operand if any
 * @param value Value of the given operand
 * @param size Number of bytes that the operand take
 * @param type Address for the sequence of characters that define the data type of this operands value
 */
void get_operand_info(char *operand, int address, int value, int size, char *op_type)
{
    if (operand != NULL && strcmp(operand, "op1") == 0 )
    {
        current_instruction_state.op1.address = address;
        current_instruction_state.op1.value = value;
        current_instruction_state.op1.size = size;
        current_instruction_state.op1.op_type = op_type;
    } else
    {
        current_instruction_state.op2.address = address;
        current_instruction_state.op2.value = value;
        current_instruction_state.op2.size = size;
        current_instruction_state.op1.op_type = op_type;
    }
}

/**
 * Sets the current instruction in use
 * @param instruction Instruction to execute
 */
void set_instruction(char *instruction)
{
    current_instruction_state.instruction = instruction;
}

/**
 * Resets all values in the structure to 0's
 */
void clean()
{
    current_instruction_state = (Info){0};
}

//--------------------------------
// Instruction execution funtions
//--------------------------------

/**
 * Instruction dispatcher using the lookup table in InstructionMap.
 * Calls the funtion associated to the instruction string.
 */
void dispatch()
{
    Info *current_state = (Info*) get_current_state();
    if (!current_state->instruction) return;
    
    for (int i = 0; i < TABLE_SIZE; i++) {
        if (strcmp(current_state->instruction, dispatch_table[i].instruction) == 0) {
            dispatch_table[i].func(current_state);
            return;
        }
    }
    // Should never be reached as in this point the instruction has already been validated
    printf("Error: Unknown instruction %s\n", current_state->instruction);
}

//----------------------
// Data Path Functions
//----------------------

void exec_mov(Info *s)
{
    ;
}

void exec_halt(Info *s)
{
    return;
}

void exec_cmp(Info *s)
{
    return;
}

void exec_jmp(Info *s)
{
    return;
}

void exec_jb(Info *s)
{
    return;
}

void exec_jl(Info *s)
{
    return;
}

void exec_ja(Info *s)
{
    return;
}

void exec_jg(Info *s)
{
    return;
}

void exec_je(Info *s)
{
    return;
}

void exec_jne(Info *s)
{
    return;
}

void exec_jz(Info *s)
{
    return;
}

void exec_js(Info *s)
{
    return;
}

void exec_jc(Info *s)
{
    return;
}

void exec_jo(Info *s)
{
    return;
}

//----------------------
// ALU Functions
//----------------------
void exec_add(Info *s)
{
    return;
}

void exec_adc(Info *s)
{
    return;
}

void exec_sub(Info *s)
{
    return;
}

void exec_sbb(Info *s)
{
    return;
}

void exec_inc(Info *s)
{
    return;
}

void exec_dec(Info *s)
{
    return;
}

void exec_and(Info *s)
{
    return;
}

void exec_or(Info *s)
{
    return;
}

void exec_xor(Info *s)
{
    return;
}

void exec_not(Info *s)
{
    return;
}

void exec_neg(Info *s)
{
    return;
}

void exec_xchg(Info *s)
{
    return;
}


