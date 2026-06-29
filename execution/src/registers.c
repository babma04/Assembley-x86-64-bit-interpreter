#include "../include/registers.h"
#include <stdlib.h>
#include <stdio.h>
#include <stddef.h>

// Defines the structure of the 4 registers with high and low byte access
union x86_aliased_registers {
    uint64_t r64;
    uint32_t e32;
    uint16_t x16;
    struct{
        uint8_t l;
        uint8_t h;
    } r8;
};

struct x86_general_register_complex {
    x86_aliased_registers reg;
    uint8_t is_signed; // 0 = unsigned, 1 = signed
};

struct x86_64bit_standard_registers {
    uint64_t r64;
    uint8_t is_signed;
};

// Defines the general registers as a structure of the CPU as well as the flags register
struct CPURegs {
    x86_general_register_complex rax, rbx, rcx, rdx;
    x86_64bit_standard_registers rsi, rdi, rbp, rsp;
    x86_64bit_standard_registers r8, r9, r10, r11, r12, r13, r14, r15;
    uint32_t rflags; 
};

// Missing FPU register structure

// ---------------------------------------------------------------------------------------------------------

//-----------------------
// Initializer
//-----------------------

CPURegs* CPURegs_create()
{
    CPURegs *c = (CPURegs*)calloc(1, sizeof(CPURegs));
    
    // Memory allocation confirmation
    if (c == NULL)
    {
        printf("Fail allocating register memory. Aborting program\n");
        return NULL;
    }

    return c;
}

void CPURegs_free(CPURegs *c)
{
    if (c == NULL) return;
    free(c);
}

//-------------------------
// Pointers dispatcher
//-------------------------

/**
 * @brief Helper for getting the pointer to a given register.
 * * Returns the pointer to the start of the structure that holds the desired register given by its index.
 * 
 * @param current_state Holder of the register structures
 * @param reg_id Index of the desired register as in the CPURegs structure
 */
x86_aliased_registers* get_reg_ptr(CPURegs *current_state, uint8_t reg_id)
{
    switch(reg_id) {
        case 0: return &current_state->rax.reg;
        case 1: return &current_state->rbx.reg;
        case 2: return &current_state->rcx.reg;
        case 3: return &current_state->rdx.reg;
        // For standard regs, we cast them to the aliased union type 
        // so the write_reg logic works for all of them
        case 4: return (x86_aliased_registers*) &current_state->rsi;
        case 5: return (x86_aliased_registers*) &current_state->rdi;
        case 6: return (x86_aliased_registers*) &current_state->rbp;
        case 7: return (x86_aliased_registers*) &current_state->rsp;
        case 8: return (x86_aliased_registers*) &current_state->r8;
        case 9: return (x86_aliased_registers*) &current_state->r9;
        case 10: return (x86_aliased_registers*) &current_state->r10;
        case 11: return (x86_aliased_registers*) &current_state->r11;
        case 12: return (x86_aliased_registers*) &current_state->r12;
        case 13: return (x86_aliased_registers*) &current_state->r13;
        case 14: return (x86_aliased_registers*) &current_state->r14;
        case 15: return (x86_aliased_registers*) &current_state->r15;
        default: return NULL;
    }
}

//-------------------------
// Signing related functions
//-------------------------

void set_reg_sign (CPURegs *current_state, uint8_t reg_id, uint8_t is_signed)
{
    if (reg_id < 0 || reg_id > 15) return;
    uint8_t *tmp = (uint8_t*)get_reg_ptr(current_state, reg_id);
    *(tmp + 8) = is_signed;
}

int is_signed (CPURegs *current_state, uint8_t reg_id)
{
    if (reg_id < 0 || reg_id > 15) return -1;
    uint8_t *tmp = (uint8_t*)get_reg_ptr(current_state, reg_id);
    return *(tmp + 8);
}

//-------------------------
// Write related functions
//-------------------------

void write_reg(CPURegs *current_state, uint8_t reg_id, int64_t value, uint8_t size, uint8_t is_high)
{
    if (reg_id < 0 || reg_id > 15) return;

    // Pointer to the start of the register array for the first structure
    x86_aliased_registers *target = get_reg_ptr(current_state, reg_id);
    if (!target) return;

    // Handle the first 4 registers (RAX, RCX, RDX, RBX) which support splitting
    if (size == 8) target->r64 = value;
    else if (size == 4) target->e32 = (uint32_t)value;
    else if (size == 2) target->x16 = (uint16_t)value;
    else if (size == 1)
    {
        if (is_high && reg_id < 4) target->r8.h = (uint8_t)value;
        else target->r8.l = (uint8_t)value;
    }
}


//-------------------------
// Read related functions
//-------------------------

uint64_t read_8b_reg(CPURegs *current_state, uint8_t reg_id) {
    x86_aliased_registers *target = get_reg_ptr(current_state, reg_id);
    return target->r64;
}

uint32_t read_4b_reg(CPURegs *current_state, uint8_t reg_id) {
    x86_aliased_registers *target = get_reg_ptr(current_state, reg_id);
    return target->e32;
}

uint16_t read_2b_reg(CPURegs *current_state, uint8_t reg_id) {
    x86_aliased_registers *target = get_reg_ptr(current_state, reg_id);
    return target->x16;
}

uint8_t read_1b_reg(CPURegs *current_state, uint8_t reg_id, uint8_t is_high) {
    x86_aliased_registers *target = get_reg_ptr(current_state, reg_id);
    if (is_high && reg_id < 4) return target->r8.h;
    return target->r8.l;
}

// ------------------------------------
// Flag reading and writing functions
// ------------------------------------

uint32_t read_rflags(CPURegs *current_state)
{
    return current_state->rflags;
}

int read_trap_flag(CPURegs *current_state)
{
    return (current_state->rflags >> 8) & 0x1;
}

int read_carry_flag(CPURegs *current_state)
{
    return (current_state->rflags & 0x1);
}

int read_zero_flag(CPURegs *current_state)
{
    return (current_state->rflags >> 6) & 0x1;
}

int read_sign_flag(CPURegs *current_state)
{
    return (current_state->rflags >> 7) & 0x1;
}

int read_overflow_flag(CPURegs *current_state)
{
    return (current_state->rflags >> 11) & 0x1;
}

void write_rflags(CPURegs *current_state, uint32_t value)
{
    current_state->rflags = value;
}

void exch_rflag (CPURegs *current_state, uint8_t flag_id)
{
    // Verifies if the flag is valid
    if (flag_id < 0 || flag_id > 32) return;

    current_state->rflags ^= (1 << flag_id);
}

void set_trap_flag(CPURegs *current_state)
{
    current_state->rflags ^= (1 << 8);
}
