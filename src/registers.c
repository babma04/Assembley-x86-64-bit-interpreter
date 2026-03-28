#include <stdint.h>
#include <stddef.h>

// Compilation command: gcc -O3 -shared -o libreg.so -fPIC registers.c

// Defines the structure of the 4 registers with high and low byte access
typedef union{
    uint64_t r64;
    uint32_t e32;
    uint16_t x16;
    struct{
        uint8_t l;
        uint8_t h;
    } r8;
}x86_aliased_registers;

typedef struct {
    x86_aliased_registers reg;
    uint8_t is_signed; // 0 = unsingned, 1 = signed
}x86_general_register_complex;

typedef struct {
    uint64_t r64;
    uint8_t is_signed;
}x86_64bit_standard_register;

// Defines the general registers as a structure of the CPU as well as the flags register
typedef struct {
    x86_general_register_complex rax, rbx, rcx, rdx;
    x86_64bit_standard_register rsi, rdi, rbp, rsp;
    x86_64bit_standard_register r8, r9, r10, r11, r12, r13, r14, r15;
    uint32_t rflags; 
}CPURegs;

// Missing FPU register structure

CPURegs current_state = {0};


/**
 * Returns the address to the structure in memory that holds the current state of the registers in the execution
 * @return Address value of the structure defined in this file in memory
 */
CPURegs *get_cpu_state()
{
    return &current_state;
}

//-------------------------
// Pointers dispatcher
//-------------------------

/**
 * Helper for getting the pointer to a given register.
 * Returns the pointer to the start of the structure that holds the desired register given by its index.
 * @param reg_id Index of the desired register as in the CPURegs structure
 */
static x86_aliased_registers* get_reg_ptr(int reg_id)
{
    switch(reg_id) {
        case 0: return &current_state.rax.reg;
        case 1: return &current_state.rbx.reg;
        case 2: return &current_state.rcx.reg;
        case 3: return &current_state.rdx.reg;
        // For standard regs, we cast them to the aliased union type 
        // so the write_reg logic works for all of them
        case 4: return (x86_aliased_registers*)&current_state.rsi;
        case 5: return (x86_aliased_registers*)&current_state.rdi;
        case 6: return (x86_aliased_registers*)&current_state.rbp;
        case 7: return (x86_aliased_registers*)&current_state.rsp;
        case 8: return (x86_aliased_registers*)&current_state.r8;
        case 9: return (x86_aliased_registers*)&current_state.r9;
        case 10: return (x86_aliased_registers*)&current_state.r10;
        case 11: return (x86_aliased_registers*)&current_state.r11;
        case 12: return (x86_aliased_registers*)&current_state.r12;
        case 13: return (x86_aliased_registers*)&current_state.r13;
        case 14: return (x86_aliased_registers*)&current_state.r14;
        case 15: return (x86_aliased_registers*)&current_state.r15;
        default: return NULL;
    }
}

//-------------------------
// Signing related funtions
//-------------------------

/**
 * Sets the sign flag for a register
 * @param reg_id Index of the register in as defined by the order of initialization in the CPURegs struct
 * @param is_signed 0 = unsigned , 1 = signed
 */
void set_reg_sign(int reg_id, uint8_t is_signed)
{
    if (reg_id < 0 || reg_id > 15) return;
    uint8_t *base = (uint8_t*)get_reg_ptr(reg_id);
    *(base + 8) = is_signed;
}

/**
 * Returns the value of the sign status of a given register. If the given index is incorrect returns -1
 * @param reg_id Index of the register in as defined by the order of initialization in the CPURegs struct
 */
int is_signed(int reg_id)
{
    if (reg_id < 0 || reg_id > 15) return -1;
    uint8_t *base = (uint8_t*)get_reg_ptr(reg_id);
    return *(base + 8);
}

//-------------------------
// Write related funtions
//-------------------------

/**
 * write_reg: Hardware Dispatcher for register values.
 * @param reg_id Index of the register in as defined by the order of initialization in the CPURegs struct
 * @param value  The 64-bit value to write
 * @param size   Number of bytes to write (1, 2, 4, 8)
 * @param is_high: Boolean (1 if accessing AH/BH/CH/DH)
 */
void write_reg(int reg_id, int64_t value, int size, int is_high)
{
    if (reg_id < 0 | reg_id > 15) return;

    // Pointer to the start of the register array for the first structure
    x86_aliased_registers *target = get_reg_ptr(reg_id);
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
// Read related funtions
//-------------------------

/**
 * read_8b_reg: Hardware Dispatcher fo 8 byte registers.
 * @param reg_id Index of the register as defined by the order of initialization in the CPURegs sructure
 * @return The 64-bit value of the given register
 * @warning The index must be valid for a correct result
 */
uint64_t read_8b_reg(int reg_id) {
    x86_aliased_registers *target = get_reg_ptr(reg_id);
    return target->r64;
}

/**
 * read_4b_reg: Hardware Dispatcher fo 4 byte registers.
 * @param reg_id Index of the register as defined by the order of initialization in the CPURegs sructure
 * @return The 32-bit value of the given register
 * @warning The index must be valid for a correct result
 */
uint32_t read_4b_reg(int reg_id) {
    x86_aliased_registers *target = get_reg_ptr(reg_id);
    return target->e32;
}

/**
 * read_2b_reg: Hardware Dispatcher fo 2 byte registers.
 * @param reg_id Index of the register as defined by the order of initialization in the CPURegs sructure
 * @return The 16-bit value of the given register
 * @warning The index must be valid for a correct result
 */
uint16_t read_2b_reg(int reg_id) {
    x86_aliased_registers *target = get_reg_ptr(reg_id);
    return target->x16;
}

/**
 * read_1b_reg: Hardware Dispatcher fo 1 byte registers.
 * @param reg_id Index of the register as defined by the order of initialization in the CPURegs sructure
 * @param is_high Boolean (1 if accessing AH/BH/CH/DH)
 * @return The 8-bit value of the given register
 * @warning The index must be valid for a correct result
 */
uint8_t read_1b_reg(int reg_id, int is_high) {
    x86_aliased_registers *target = get_reg_ptr(reg_id);
    if (is_high && reg_id < 4) return target->r8.h;
    return target->r8.l;
}

// ------------------------------------
// Flag reading and writing funtions
// ------------------------------------

/**
 * read_rflags: Returns the value of the rflags register
 * @return The 32-bit value of the rflags register
 */
uint32_t read_rflags()
{
    return current_state.rflags;
}

/**
 * read_parity_flag: Returns the value of the parity flag (PF) in the rflags register
 * @return 1 if the parity flag is set, 0 otherwise
 */
int read_trap_flag()
{
    return (current_state.rflags >> 8) & 0x1;
}

/**
 * read_carry_flag: Returns the value of the carry flag (CF) in the rflags register
 * @return 1 if the carry flag is set, 0 otherwise
 */
int read_carry_flag()
{
    return (current_state.rflags & 0x1);
}

/**
 * read_zero_flag: Returns the value of the zero flag (ZF) in the rflags register
 * @return 1 if the zero flag is set, 0 otherwise
 */
int read_zero_flag()
{
    return (current_state.rflags >> 6) & 0x1;
}

/**
 * read_sign_flag: Returns the value of the sign flag (SF) in the rflags register
 * @return 1 if the sign flag is set, 0 otherwise
 */
int read_sign_flag()
{
    return (current_state.rflags >> 7) & 0x1;
}

/**
 * read_overflow_flag: Returns the value of the overflow flag (OF) in the rflags register
 * @return 1 if the overflow flag is set, 0 otherwise
 */
int read_overflow_flag()
{
    return (current_state.rflags >> 11) & 0x1;
}

/**
 * write_rflags: Writes a value to the rflags register
 * @param value The 32-bit value to write to the rflags register
 */
void write_rflags(uint32_t value)
{
    current_state.rflags = value;
}

/**
 * set_trap_flag: Toggles the value of the trap flag (TF) in the rflags register
 * @warning This function toggles the value of the trap flag, so if it is currently set it will be cleared, and if it is currently cleared it will be set
 */
void set_trap_flag()
{
    current_state.rflags ^= (1 << 8);
}
