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
// Exposed Structures
// --------------------------------------------------

// Operation Info structure
typedef struct Info Info;

// ---------------------------------------------------
// Prototypes
// ---------------------------------------------------

// Pointer creation
/**
 * @brief Creates a pointer to the operand Info structure and returns it.
 */
Info* create_operand_state ();

// Pointer freeing
/**
 * @brief Frees up the pointer from memory.
 * * Mainly for integration with python
 * 
 * @param ptr Pointer to free
 */
void free_operand_state (Info* ptr);

// Essential data structure setters

/**
 * @brief Sets the register reference to use for operations.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 * @param r Register structure holding all register info 
 */ 
void set_registers_ref (Info *current_state, CPURegs *r);

/**
 * @brief Sets the table reference to use for memory access operations.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction result and registers info
 * @param t Table structure holding all paging info for memory access operations
 */
void set_table_ref (Info *current_state, Table *t);

// Info setters 
/**
 * @brief Sets the operand info in the structure.
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param operand Address for the sequence of characters that define the operand to update
 * @param address 64 bit long Address of the operand if any
 * @param value 64 bit long Value of the given operand
 * @param size Number of bytes that the operand take (number of bytes as a char)
 * @param type Address for the sequence of characters that define the data type of this operands value
 * @param visual_rep Visual representation it should have (0 for string representation, 1 for numerical representation)
 */
void set_operand_info (Info *current_instruction_state, char *operand, long long address, long long value, uint8_t size, char *op_type, uint8_t visual_rep);

/**
 * @brief Sets the current instruction in use.
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 * @param instruction Instruction to execute
 */
void set_instruction(Info *current_instruction_state, char *instruction);

// Infor cleaner
/**
 * @brief Resets all Operand fields and Instruction of the Info structure to their default values (NULL for pointers, 0 for numerical values).
 * 
 * @param current_instruction_state Pointer to the Info structure holding all operand, instruction, registers and results info
 */
void clean(Info *current_instruction_state);

// Instruction dispatching prototypes
/**
 * @brief Instruction dispatcher using the lookup table in InstructionMap.
 * * Calls the function associated to the instruction string.
 * 
 * @param current_state Pointer to the Info structure holding all operand, instruction and results info
 */ 
void dispatch(Info *current_instruction_state);

#endif // OPERATIONS_H
