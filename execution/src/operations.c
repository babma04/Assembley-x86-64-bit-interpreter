#include "../include/operations.h"


// --------------------------------------------------------------------------------
// Structures implementations
// --------------------------------------------------------------------------------

// Structure for each alu operand's necessary info
typedef struct Operand{
    long long address;
    long long value;
    uint8_t size; // 1,2,4,8
    char *op_type;
    uint8_t visual_rep; // 1 for text, 0 for numerical
} Operand;

// To be implemented a fpu operand struct

// Structure for all necessary instruction info
struct Info {
    char *instruction;
    Operand op1;
    Operand op2;
    CPURegs *registers;
    Table* table;
    Operand result;
};

// --------------------------------------------------------------------------------
// Prototypes
// --------------------------------------------------------------------------------
static void exec_cmp(Info *s); 
static void exec_add(Info *s); 
static void exec_adc(Info *s);
static void exec_sub(Info *s); 
static void exec_sbb(Info *s); 
static void exec_inc(Info *s);
static void exec_dec(Info *s); 
static void exec_and(Info *s); static void exec_or(Info *s);
static void exec_xor(Info *s); 
static void exec_not(Info *s); 
static void exec_neg(Info *s);
static void exec_xchg(Info *s);
static void set_result_info(Info *current_state);
static void commit_operand (Info* current_instruction_state, Operand* op, long long value);

// --------------------------------------------------------------------------------
// Lookup Table
// --------------------------------------------------------------------------------

// Standard instruction function signature alias
typedef void (*InstructionFunc)(Info *);

// Instructions link struct
typedef struct InstructionMap {
    char *instruction;
    InstructionFunc func;
} InstructionMap;

// Lookup table to match string instructions with c functions
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
// Operand fetching, setting and cleaning functions
// --------------------------------------------------------------------------------

// -------------------
// Operand state init
// -------------------

Info* create_operand_state ()
{
    Info *op_state = (Info*)calloc(1, sizeof(Info));

    if (op_state == NULL)
    {
        printf("operand table creation error. NULL pointer was achieved!\n");
        return NULL;
    }
    return op_state;
}

void free_operand_state (Info* s)
{
    if (s) free(s);
}

// ----------------------------
// Info setters
// ----------------------------

void set_operand_info (Info *current_instruction_state, char *operand, long long address, long long value, uint8_t size, char *op_type, uint8_t visual_rep)
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

void set_instruction (Info *current_instruction_state, char *instruction)
{
    current_instruction_state->instruction = instruction;
}

void set_registers_ref (Info *current_state, CPURegs *r)
{
    current_state->registers = r;
}

void set_table_ref (Info *current_state, Table *t)
{
    current_state->table = t;
}

/**
 * @brief Commits the result of an operation to the appropriate destination (memory or register) based on the operand type.
 * * This function is called after an operation has been executed and the result is ready to be stored.
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param op Pointer to the Operand structure that holds the destination information (address, type, size, etc.)
 * @param value The result value to be committed to the destination
 * @warning This function assumes that the operand type is either "memory" or "register". If the operand type is unknown, an error message will be printed.
 */
static void commit_operand (Info* current_instruction_state, Operand* op, long long value)
{
    if (strcmp(op->op_type, "memory") == 0) {
        write_mem(current_instruction_state->table, op->address, (uint8_t*)&value, op->size, 1);
    } else if (strcmp(op->op_type, "register") == 0) {
        uint8_t is_high = (op->address <= 3 && op->size == 1);
        write_reg(current_instruction_state->registers, op->address, value, op->size, is_high);
    }
    else
    {
        printf("Error: Unknown operand type %s\n", op->op_type);
    }
}

// -------------------
// Cleaners
// -------------------


void clean(Info *s) {
    memset(&s->op1, 0, sizeof(Operand));
    memset(&s->op2, 0, sizeof(Operand));
    memset(&s->result, 0, sizeof(Operand));
    s->instruction = NULL;
}

//--------------------------------
// Instruction execution functions
//--------------------------------

void dispatch(Info *current_instruction_state)
{
    if (!current_instruction_state->instruction) return;

    set_result_info(current_instruction_state);
    
    for (int i = 0; i < TABLE_SIZE; i++) {
        if (strcmp(current_instruction_state->instruction, dispatch_table[i].instruction) == 0) {
            int is_xchg = (strcmp(current_instruction_state->instruction, "xchg") == 0);
            dispatch_table[i].func(current_instruction_state);
            if (!is_xchg) {
                commit_operand(current_instruction_state, &current_instruction_state->result, current_instruction_state->result.value);
            }
            clean(current_instruction_state);
            return;
        }
    }
    // Should never be reached as in this point the instruction has already been validated
    printf("Error: Unknown instruction %s\n", current_instruction_state->instruction);
    // Safety for if an operation ends in an error
    clean(current_instruction_state);
}

// --------------
// Result setter
// --------------

/**
 * @brief Sets the information about the result based on the operators info.
 * * Leaves the result value non altered to be set by the operation called.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 */
static void set_result_info (Info *current_state)
{
    current_state->result.op_type = current_state->op1.op_type;
    current_state->result.size = current_state->op1.size;
    current_state->result.address = current_state->op1.address;
    current_state->result.visual_rep = (current_state->op1.visual_rep || current_state->op2.visual_rep);
}


//----------------------
// Data Path Functions
//----------------------

/**
 * @brief Universal function to update the flags after an operation based on the result of the operation and the operands info.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @param result The result of the operation of the two operands, used to set the flags
 */
static void flags_update(Info *s, unsigned long long result)
{
    int bit_count = 8 * s->op1.size;
    int msb_mask = bit_count - 1;
    unsigned long long bits_mask = (1ULL << bit_count) - 1;
    unsigned long long res_msb = result & bits_mask;

    // Arithmetic flags
    uint8_t zero = (uint8_t) (res_msb == 0);
    uint8_t sign = (uint8_t) ((res_msb >> (bit_count - 1)) & 1);

    // Logical flags
    uint8_t carry = (uint8_t) ((result >> bit_count) & 1);
    uint8_t overflow = (uint8_t) (((s->op1.value ^ result) & (s->op2.value ^ result)) >> msb_mask & 1);

    // More flags can be later implemented as needed

    // Preserving the state of the trap flag as it is not affected by the operations
    uint8_t trap = (uint8_t) read_trap_flag(s->registers);

    uint32_t rflags_value = (carry << 0) | (zero << 6) | (sign << 7) | (overflow << 11) | (trap << 8);
    write_rflags(s->registers, rflags_value);
}

// ----------------------------
// Main Flux Control function
// ----------------------------

/**
 * @brief Executes the compare instruction, which is a subtraction that only updates the flags and does not store the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is not stored, only the flags are updated based on the result of the operation
 */
static void exec_cmp(Info *s)
{
    // Need cmp syntax rules check
    unsigned long long result = (unsigned long long) s->op1.value - s->op2.value;
    // Sets flags based on the result
    flags_update(s, result);
}

//----------------------
// ALU Functions
//----------------------

/**
 * @brief Executes non carried addition
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the addition is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_add(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value + s->op2.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes carried addition 
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the addition is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_adc(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value + s->op2.value + read_carry_flag(s->registers);
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes non carried subtraction
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_sub(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value - s->op2.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes carried subtraction
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the subtraction is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_sbb(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value - s->op2.value - read_carry_flag(s->registers);
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the increment instruction, which adds 1 to the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the increment is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_inc(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value + 1;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the decrement instruction, which subtracts 1 from the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the decrement is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_dec(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value - 1;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the bitwise AND instruction, which performs a bitwise AND operation between the two operands and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the AND operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_and(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value & s->op2.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the bitwise OR instruction, which performs a bitwise OR operation between the two operands and updates the flags based on the result.
 *  
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the OR operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_or(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value | s->op2.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the bitwise XOR instruction, which performs a bitwise XOR operation between the two operands and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the XOR operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_xor(Info *s)
{
    unsigned long long result = (unsigned long long) s->op1.value ^ s->op2.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the bitwise NOT instruction, which performs a bitwise NOT operation on the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the NOT operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_not(Info *s)
{
    unsigned long long result = (unsigned long long) ~s->op1.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the NEG instruction, which negates the operand and updates the flags based on the result.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the NEG operation is stored in the result field of the Info structure and the flags are updated based on the result of the operation
 */
static void exec_neg(Info *s)
{
    unsigned long long result = (unsigned long long) -s->op1.value;
    flags_update(s, result);
    s->result.value = (long long) result;
}

/**
 * @brief Executes the XCHG instruction, which exchanges the values of the two operands without updating the flags.
 * 
 * @param s Pointer to the Info structure holding all operand, instruction and results info
 * @warning The result of the XCHG operation is stored in the op1 and op2 fields of the Info structure and the flags are not updated based on the result of the operation
 */
static void exec_xchg(Info *s)
{
    // Fetches each value
    long long val1 = s->op1.value;
    long long val2 = s->op2.value;
    // commits each value
    commit_operand(s, &s->op1, val2);
    commit_operand(s, &s->op2, val1);
}