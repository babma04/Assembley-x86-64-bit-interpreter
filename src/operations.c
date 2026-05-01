#include "../include/operations.h"

// --------------------------------------------------------------------------------
// Structures implementations
// --------------------------------------------------------------------------------

// Structure for each alu operand's necessary info
struct Operand{
    long long address;
    long long value;
    char size; // 1,2,4,8
    char *op_type;
    char visual_rep; // 1 for text, 0 for numerical
};

// To be implemented a fpu operand struct

// Structure for all necessaryu instruction info
struct Info {
    char *instruction;
    Operand op1;
    Operand op2;
    CPURegs *registers;
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
    // Data Path (compare)
    {"cmp",  exec_cmp},

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
 * @brief Creates a pointer to the operand Info structure and returns it.
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
 * @brief Sets the operand info in the structurer.
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param operand Address for the sequence of charaters that define the operand to update
 * @param address 64 bit long Address of the operand if any
 * @param value 64 bit long Value of the given operand
 * @param size Number of bytes that the operand take (number of bytes as a char)
 * @param type Address for the sequence of characters that define the data type of this operands value
 * @param visual_rep Visual representation it should have (0 for string representation, 1 for numerial representation)
 */
void get_operand_info (Info *current_instruction_state, char *operand, long long address, long long value, char size, char *op_type, char visual_rep)
{
    if (operand != NULL && strcmp(operand, "op1") == 0 )
    {
        current_instruction_state->op1.address = address;
        current_instruction_state->op1.value = value;
        current_instruction_state->op1.size = size;
        current_instruction_state->op1.op_type = op_type;
        current_instruction_state->op1.visual_rep = visual_rep;
    } else
    {
        current_instruction_state->op2.address = address;
        current_instruction_state->op2.value = value;
        current_instruction_state->op2.size = size;
        current_instruction_state->op2.op_type = op_type;
        current_instruction_state->op2.visual_rep = visual_rep;

    }
}

/**
 * @brief Sets the current instruction in use.
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param instruction Instruction to execute
 */
void set_instruction (Info *current_instruction_state, char *instruction)
{
    current_instruction_state->instruction = instruction;
}

/**
 * @brief Sets the register reference to use for operations.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 * @param r Register structure holding all register info 
 */ 
void set_registers_ref (Info *current_state, CPURegs *r)
{
    current_state->registers = r;
}

/**
 * @brief Sets the information about the result based on the operators info.
 * * Leaves the result value non alterated to be set by the operation called.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 */
void set_result_info (Info *current_state)
{
    current_state->result.op_type = current_state->op1.op_type;
    current_state->result.size = current_state->op1.size;
    current_state->result.address = current_state->op1.address;
    current_state->result.visual_rep = (current_state->op1.visual_rep || current_state->op2.visual_rep);
}

/**
 * @brief Resets all values in the structure to 0's.
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @return -1 if a memory allocation failed, 0 as a successful exit code
 */
int clean(Info *current_instruction_state)
{
    Info *tmp = malloc(sizeof(Info));
    if (tmp == NULL)
    {
        printf ("Memory allocation error");
        return -1;
    }
    free(current_instruction_state);
    current_instruction_state = tmp;
    return 0;
}

/**
 * @brief Frees up the pointer from memory.
 * * Mainly for integration with python
 * 
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
 * @brief Instruction dispatcher using the lookup table in InstructionMap.
 * * Calls the funtion associated to the instruction string.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction and results info
 */
void dispatch(Info *current_instruction_state)
{
    if (!current_instruction_state->instruction) return;

    set_result_info(current_instruction_state);
    
    for (int i = 0; i < TABLE_SIZE; i++) {
        if (strcmp(current_instruction_state->instruction, dispatch_table[i].instruction) == 0) {
            dispatch_table[i].func(current_instruction_state);
            return;
        }
    }
    // Should never be reached as in this point the instruction has already been validated
    printf("Error: Unknown instruction %s\n", current_instruction_state->instruction);
    // Safety for if an operation is ends in an error
    clean(current_instruction_state);
}

// ---------------------------
// Result management funtions
// ---------------------------

/**
 * @brief Reads the result of the current instruction execution and returns it if it's a register, otherwise returns -1.
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
 * @brief Writes the result of the current instruction execution if it's a memory address and cleans the current instruction state structure.
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
    // Need cmp syntax rules check

    s->result.value = s->op1.value - s->op2.value;
}

//----------------------
// ALU Functions
//----------------------

/**
 * Executes addition
 */
void exec_add(Info *s)
{
    // Needs additions imolementation rules

    s->result.value = s->op1.value + s->op2.value;
}

/**
 * Executes carried addition
 */
void exec_adc(Info *s)
{
    exec_add(s);
    s->result.value += read_carry_flag(s->registers);
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

