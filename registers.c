#include <stdint.h>

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