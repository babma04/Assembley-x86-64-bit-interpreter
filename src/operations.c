#include "../include/operations.h"

// --------------------------------------------------------------------------------
// Structures implementations
// --------------------------------------------------------------------------------

// Structure for each alu operand's necessary info
struct Operand{
    int address;
    int value;
    int size; // 1,2,4,8
    char *op_type;
};

// To be implemented a fpu operand struct

// Structure for all necessaryu instruction info
struct Info {
    char *instruction;
    Operand op1;
    Operand op2;
    Operand result;
};

// Instructions link struct
struct InstructionMap {
    char *instruction;
    InstructionFunc func;
};

// --------------------------------------------------------------------------------
// Lookup Table
// --------------------------------------------------------------------------------

// Lookup table to match string instructions with c funtions
InstructionMap dispatch_table[] = {
    // Data Path
    {"cmp",  exec_cmp},  {"jmp",  exec_jmp},  {"jb",   exec_jb},
    {"jl",   exec_jl},   {"ja",   exec_ja},   {"jg",   exec_jg},
    {"je",   exec_je},   {"jne",  exec_jne},  {"jz",   exec_jz},
    {"js",   exec_js},   {"jc",   exec_jc},   {"jo",   exec_jo},

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

// --------------------------------------------------------------------------------
// Operand fetching, setting and cleaning funtions
// --------------------------------------------------------------------------------

/**
 * Creates a pointer to the operand Info structure and returns it
 */
Info* create_operand_state ()
{
    Info *op_state = malloc (sizeof(Info));

    if (op_state == NULL)
    {
        printf("operand table creation error. NULL pointer was achieved!\n");
        return NULL;
    }
    return op_state;
}

/**
 * Sets the operand info in the structurer
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction and results info
 * @param operand Address for the sequence of charaters that define the operand to update
 * @param address Address of the operand if any
 * @param value Value of the given operand
 * @param size Number of bytes that the operand take
 * @param type Address for the sequence of characters that define the data type of this operands value
 */
void get_operand_info(Info *current_instruction_state, char *operand, int address, int value, int size, char *op_type)
{
    if (operand != NULL && strcmp(operand, "op1") == 0 )
    {
        current_instruction_state->op1.address = address;
        current_instruction_state->op1.value = value;
        current_instruction_state->op1.size = size;
        current_instruction_state->op1.op_type = op_type;
    } else
    {
        current_instruction_state->op2.address = address;
        current_instruction_state->op2.value = value;
        current_instruction_state->op2.size = size;
        current_instruction_state->op2.op_type = op_type;
    }
}

/**
 * Sets the current instruction in use
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction and results info
 * @param instruction Instruction to execute
 */
void set_instruction(Info *current_instruction_state, char *instruction)
{
    current_instruction_state->instruction = instruction;
}

/**
 * Resets all values in the structure to 0's
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction and results info
 */
void clean(Info *current_instruction_state)
{
    Info *tmp = malloc(sizeof(Info));
    free(current_instruction_state);
    current_instruction_state = tmp;
}

/**
 * Frees up the pointer from memory
 * Mainly for integration with python
 * @param ptr Pointer to free
 */
void free_pointer (Info* ptr)
{
    free(ptr);
}

//--------------------------------
// Instruction execution funtions
//--------------------------------

/**
 * Instruction dispatcher using the lookup table in InstructionMap.
 * Calls the funtion associated to the instruction string.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction and results info
 */
void dispatch(Info *current_instruction_state)
{
    if (!current_instruction_state->instruction) return;
    
    for (int i = 0; i < TABLE_SIZE; i++) {
        if (strcmp(current_instruction_state->instruction, dispatch_table[i].instruction) == 0) {
            dispatch_table[i].func(current_instruction_state);
            return;
        }
    }
    // Should never be reached as in this point the instruction has already been validated
    printf("Error: Unknown instruction %s\n", current_instruction_state->instruction);
}

// ---------------------------
// Result management funtions
// ---------------------------

/**
 * Reads the result of the current instruction execution and returns it if it's a register, otherwise returns -1
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction and results info
 * @return int Result of the instruction execution if it's a register, otherwise -1
 */
int read_result(Info *current_instruction_state)
{
    if (strcmp(current_instruction_state->result.op_type, "register") == 0)
    {
        return current_instruction_state->result.value;
    }
    clean(current_instruction_state);
    return -1;
}

/**
 * Writes the result of the current instruction execution if it's a memory address and cleans the current instruction state structure
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction and results info
 * @warning If the result is not a memory address does nothing
 * @warning After writing the result on memory cleans the current instruction state structure
 */
void set_result(Info *current_instruction_state)
{
    if (strcmp(current_instruction_state->result.op_type, "memory") == 0)
    {
        write_mem(current_instruction_state->result.address, (uint8_t*)&current_instruction_state->result.value, current_instruction_state->result.size, 1);
    }
    clean(current_instruction_state);
}

//----------------------
// Data Path Functions
//----------------------

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


