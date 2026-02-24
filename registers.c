#include <stdint.h>

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
} x86_general_registers;

// Defines the general registers as a structure of the CPU as well as the flags register
typedef struct{
    x86_general_registers rax;
    x86_general_registers rbx;
    x86_general_registers rcx;
    x86_general_registers rdx;

    uint64_t rsi, rdi, rbp, rsp;
    uint64_t r8, r9, r10, r11, r12, r13, r14, r15;
    uint32_t rflags;
} CPURegs;

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

/**
 * write_reg: Hardware Dispatcher for register values.
 * @param reg_id: Index of the register in as defined by the order of initialization in the CPURegs struct
 * @param value:  The 64-bit value to write
 * @param size:   Number of bytes to write (1, 2, 4, 8)
 * @param is_high: Boolean (1 if accessing AH/BH/CH/DH)
 */
void write_reg(int reg_id, uint64_t value, int size, int is_high)
{
    if (reg_id < 0 | reg_id > 15) return;

    // Pointer to the start of the register array for the first structure
    x86_general_registers *gpr = (x86_general_registers*)&current_state;

    // Handle the first 4 registers (RAX, RCX, RDX, RBX) which support splitting
    if (reg_id < 4)
    {
        if (size == 8)
        {
            gpr[reg_id].r64 = value;
        } else if (size == 4)
        {
            gpr[reg_id].r64 = (uint32_t) value; 
        } else if (size == 2)
        {
            gpr[reg_id].x16 = (uint16_t) value;
        } else if (size == 1)
        {
            if (is_high) gpr[reg_id].r8.h = (uint8_t) value;
            else         gpr[reg_id].r8.l = (uint8_t) value;
        }
    } 
    // Handle the remaining registers (RSI through R15)
    else if (reg_id < 16) {
        uint64_t *gpr2 = (uint64_t*) &current_state;
        if (size == 8)
        {
            gpr2[reg_id] = value;
        } else if (size == 4)
        {
            gpr2[reg_id] = (uint32_t) value;
        } else if (size == 2)
        {
            gpr2[reg_id] = (uint16_t) value;
        } else if (size == 1)
        {
            gpr2[reg_id] = (uint8_t) value;
        }
    }
}



uint64_t read_8b_reg(int reg_id)
{
    if (reg_id < 4)
    {
        // Pointer to the start of the register array for the first structure
        x86_general_registers *gpr = (x86_general_registers*) &current_state;
        return gpr[reg_id].r64;
    } else
    {
        uint64_t *gpr2 = (uint64_t*) &current_state;
        return gpr2[reg_id];
    }
}

uint32_t read_4b_reg(int reg_id)
{
    if (reg_id < 4)
    {
        // Pointer to the start of the register array for the first structure
        x86_general_registers *gpr = (x86_general_registers*) &current_state;
        return (uint32_t) gpr[reg_id].e32;
    } else
    {
        uint64_t *gpr2 = (uint64_t*) &current_state;
        return (uint32_t) gpr2[reg_id];
    }
}

uint16_t read_2b_reg(int reg_id)
{
    if (reg_id < 4)
    {
        // Pointer to the start of the register array for the first structure
        x86_general_registers *gpr = (x86_general_registers*) &current_state;
        return (uint16_t) gpr[reg_id].x16;
    } else
    {
        uint64_t *gpr2 = (uint64_t*) &current_state;
        return (uint16_t) gpr2[reg_id];
    }
}

uint8_t read_1b_reg(int reg_id, int is_high)
{
    if (reg_id < 4)
    {
        // Pointer to the start of the register array for the first structure
        x86_general_registers *gpr = (x86_general_registers*) &current_state;
        if (is_high) return (uint8_t) gpr[reg_id].r8.h;
        else return (uint8_t) (uint8_t) gpr[reg_id].r8.l;
    } else
    {
        uint64_t *gpr2 = (uint64_t*) &current_state;
        return (uint8_t) gpr2[reg_id];
    }
}