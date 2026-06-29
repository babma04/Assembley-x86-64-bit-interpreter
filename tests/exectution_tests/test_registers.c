#include "../../execution/include/registers.h"

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>

// Building (src must be built)
// gcc -O3 -shared -o libregisters.so -fPIC registers.c

// --- Test helpers ---

static int tests_run    = 0;
static int tests_passed = 0;

#define TEST(name) static void name(void)

#define RUN(name) \
    do { \
        printf("  %-55s", #name); \
        tests_run++; \
        name(); \
        tests_passed++; \
        printf("PASS\n"); \
    } while (0)

#define ASSERT(cond) \
    do { \
        if (!(cond)) { \
            printf("FAIL\n    Assertion failed: %s  (%s:%d)\n", \
                   #cond, __FILE__, __LINE__); \
            return; \
        } \
    } while (0)

// Arbitrary register IDs — adjust to match your implementation's enum/defines
#define REG_A  0
#define REG_B  1
#define REG_C  2

// -----------------------------------------------------------------------
// Tests — lifecycle
// -----------------------------------------------------------------------

// 1. CPURegs_c() (init) returns a non-NULL pointer
TEST(test_init_not_null)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);
    CPURegs_free(r);
}

// 2. CPURegs_free() doesn't crash on a fresh state
TEST(test_free_no_crash)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);
    CPURegs_free(r);   // must not crash / segfault
}

// -----------------------------------------------------------------------
// Tests — sign setters / getters
// -----------------------------------------------------------------------

// 3. Newly created register defaults to unsigned (is_signed == 0)
TEST(test_default_unsigned)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    // Registers should start unsigned
    ASSERT(is_signed(r, REG_A) == 0);

    CPURegs_free(r);
}

// 4. set_reg_sign(signed=1) → is_signed returns non-zero
TEST(test_set_signed)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    set_reg_sign(r, REG_A, /*is_signed=*/1);
    ASSERT(is_signed(r, REG_A) != 0);

    CPURegs_free(r);
}

// 5. set_reg_sign(signed=0) clears the signed flag
TEST(test_clear_signed)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    set_reg_sign(r, REG_A, 1);
    set_reg_sign(r, REG_A, 0);
    ASSERT(is_signed(r, REG_A) == 0);

    CPURegs_free(r);
}

// 6. Sign flag is per-register (setting REG_A doesn't affect REG_B)
TEST(test_sign_flag_per_register)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    set_reg_sign(r, REG_A, 1);
    ASSERT(is_signed(r, REG_B) == 0);

    CPURegs_free(r);
}

// -----------------------------------------------------------------------
// Tests — write_reg / read_Xb_reg
// -----------------------------------------------------------------------

// 7. Write 8-bit value, read back with read_1b_reg (low byte)
TEST(test_write_read_1b_low)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0xAB, /*size=*/1, /*is_high=*/0);
    uint8_t v = read_1b_reg(r, REG_A, /*is_high=*/0);
    ASSERT(v == 0xAB);

    CPURegs_free(r);
}

// 8. Write 8-bit value to the high byte, read it back
TEST(test_write_read_1b_high)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0xCD, /*size=*/1, /*is_high=*/1);
    uint8_t v = read_1b_reg(r, REG_A, /*is_high=*/1);
    ASSERT(v == 0xCD);

    CPURegs_free(r);
}

// 9. Write 16-bit value, read back with read_2b_reg
TEST(test_write_read_2b)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0x1234, /*size=*/2, /*is_high=*/0);
    uint16_t v = read_2b_reg(r, REG_A);
    ASSERT(v == 0x1234);

    CPURegs_free(r);
}

// 10. Write 32-bit value, read back with read_4b_reg
TEST(test_write_read_4b)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0xDEADBEEF, /*size=*/4, /*is_high=*/0);
    uint32_t v = read_4b_reg(r, REG_A);
    ASSERT(v == 0xDEADBEEF);

    CPURegs_free(r);
}

// 11. Write 64-bit value, read back with read_8b_reg
TEST(test_write_read_8b)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0x0123456789ABCDEFULL, /*size=*/8, /*is_high=*/0);
    uint64_t v = read_8b_reg(r, REG_A);
    ASSERT(v == 0x0123456789ABCDEFULL);

    CPURegs_free(r);
}

// 12. Two different registers hold independent values
TEST(test_registers_independent)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0x11, 1, 0);
    write_reg(r, REG_B, 0x22, 1, 0);

    ASSERT(read_1b_reg(r, REG_A, 0) == 0x11);
    ASSERT(read_1b_reg(r, REG_B, 0) == 0x22);

    CPURegs_free(r);
}

// 13. Overwriting a register reflects the latest value
TEST(test_overwrite_register)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_reg(r, REG_A, 0xAA, 1, 0);
    write_reg(r, REG_A, 0xBB, 1, 0);
    ASSERT(read_1b_reg(r, REG_A, 0) == 0xBB);

    CPURegs_free(r);
}

// -----------------------------------------------------------------------
// Tests — flags
// -----------------------------------------------------------------------

// 14. Fresh state: rflags readable (just check it doesn't crash)
TEST(test_read_rflags_no_crash)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    (void)read_rflags(r);   // must not crash

    CPURegs_free(r);
}

// 15. write_rflags / read_rflags roundtrip
TEST(test_write_read_rflags)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    write_rflags(r, 0b00000101);   // set CF and PF
    uint32_t flags = read_rflags(r);
    ASSERT((flags & 0b00000101) == 0b00000101);

    CPURegs_free(r);
}

// 16. Carry flag: write then read
TEST(test_carry_flag)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    // Set CF (bit 0 in rflags)
    write_rflags(r, read_rflags(r) | 0x1);
    ASSERT(read_carry_flag(r) != 0);

    // Clear CF
    write_rflags(r, read_rflags(r) & ~0x1);
    ASSERT(read_carry_flag(r) == 0);

    CPURegs_free(r);
}

// 17. Zero flag: write then read
TEST(test_zero_flag)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    // ZF is bit 6 in rflags
    write_rflags(r, read_rflags(r) | 0x40);
    ASSERT(read_zero_flag(r) != 0);

    write_rflags(r, read_rflags(r) & ~0x40);
    ASSERT(read_zero_flag(r) == 0);

    CPURegs_free(r);
}

// 18. Sign flag: write then read
TEST(test_sign_flag)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    // SF is bit 7 in rflags
    write_rflags(r, read_rflags(r) | 0x80);
    ASSERT(read_sign_flag(r) != 0);

    write_rflags(r, read_rflags(r) & ~0x80);
    ASSERT(read_sign_flag(r) == 0);

    CPURegs_free(r);
}

// 19. Overflow flag: write then read
TEST(test_overflow_flag)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    // OF is bit 11 in rflags
    write_rflags(r, read_rflags(r) | 0x800);
    ASSERT(read_overflow_flag(r) != 0);

    write_rflags(r, read_rflags(r) & ~0x800);
    ASSERT(read_overflow_flag(r) == 0);

    CPURegs_free(r);
}

// 20. Trap flag: set_trap_flag sets it, read_trap_flag confirms
TEST(test_trap_flag)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    set_trap_flag(r);
    ASSERT(read_trap_flag(r) != 0);

    CPURegs_free(r);
}

// 21. exch_rflag toggles a flag bit
TEST(test_exch_rflag_toggle)
{
    CPURegs *r = CPURegs_c();
    ASSERT(r != NULL);

    uint32_t before = read_rflags(r);
    exch_rflag(r, /*flag_id=*/0);   // toggle bit 0 (CF)
    uint32_t after = read_rflags(r);
    ASSERT((before & 0x1) != (after & 0x1));

    CPURegs_free(r);
}

// -----------------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------------

int main(void)
{
    printf("=== registers tests ===\n\n");

    // Lifecycle
    RUN(test_init_not_null);
    RUN(test_free_no_crash);

    // Sign setters/getters
    RUN(test_default_unsigned);
    RUN(test_set_signed);
    RUN(test_clear_signed);
    RUN(test_sign_flag_per_register);

    // write_reg / read_Xb_reg
    RUN(test_write_read_1b_low);
    RUN(test_write_read_1b_high);
    RUN(test_write_read_2b);
    RUN(test_write_read_4b);
    RUN(test_write_read_8b);
    RUN(test_registers_independent);
    RUN(test_overwrite_register);

    // Flags
    RUN(test_read_rflags_no_crash);
    RUN(test_write_read_rflags);
    RUN(test_carry_flag);
    RUN(test_zero_flag);
    RUN(test_sign_flag);
    RUN(test_overflow_flag);
    RUN(test_trap_flag);
    RUN(test_exch_rflag_toggle);

    printf("\n%d / %d tests passed.\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}