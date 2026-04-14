#ifndef REGISTERS_H
#define REGISTERS_H

#include <stdint.h>


// Specific register types
// high and low byte accessible regs---------------------------------------------
typedef union x86_aliased_registers x86_aliased_registers;
// same but with unsigned/signed flag
typedef struct x86_general_register_complex x86_general_register_complex;
//-----------------------------------------------------------------------------------
// Other gen purpose regs
typedef struct x86_64bit_standard_registers x86_64bit_standard_registers;

// General register type
typedef struct CPURegs CPURegs;


// Prototypes
// Register getters
CPURegs* CPURegs_create ();
x86_aliased_registers* get_reg_ptr (CPURegs *current_state, int reg_id);

//sign setters
void set_reg_sign (CPURegs *current_state, int reg_id, uint8_t is_signed);
int is_signed (CPURegs *current_state, int reg_id);

// writing
void write_reg (CPURegs *current_state, int reg_id, int64_t value, int size, int is_high);

// Read
uint64_t read_8b_reg (CPURegs *current_state, int reg_id);
uint32_t read_4b_reg (CPURegs *current_state, int reg_id);
uint16_t read_2b_reg (CPURegs *current_state, int reg_id);
uint8_t read_1b_reg (CPURegs *current_state, int reg_id, int is_high);

// Flags
uint32_t read_rflags (CPURegs *current_state);
int read_trap_flag (CPURegs *current_state);
int read_carry_flag (CPURegs *current_state);
int read_zero_flag (CPURegs *current_state);
int read_sign_flag (CPURegs *current_state);
int read_overflow_flag (CPURegs *current_state);
void write_rflags (CPURegs *current_state, uint32_t value);
void exch_rflag (CPURegs *current_state, int flag_id);
void set_trap_flag (CPURegs *current_state);

#endif
