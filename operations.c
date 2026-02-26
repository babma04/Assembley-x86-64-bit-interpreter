#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>

// Compilation: 


// Structure for each operand's necessary info
typedef struct{
    int address;
    int value;
    int size; // 1,2,4,8
    char *type; //(str, int, ...)
} Operand;
// Structure for all necessaryu instruction info
typedef struct{
    char *instruction;
    Operand op1;
    Operand op2;
} Info;

Info current_instruction_state = {0};

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
 * 
 */
void get_operand_info(char *operand, int address, int value, int size, char *type)
{
    if (strcmp(*operand, "op1") == 0 )
    {
        current_instruction_state.op1.address = address;
        current_instruction_state.op1.value = value;
        current_instruction_state.op1.size = size;
        current_instruction_state.op1.type = type;
    } else
    {
        current_instruction_state.op2.address = address;
        current_instruction_state.op2.value = value;
        current_instruction_state.op2.size = size;
        current_instruction_state.op2.type = type;
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
    memset(&current_instruction_state, 0, sizeof(Info));
}

