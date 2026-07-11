#include "../../execution/include/operations.h"
#include "../../execution/include/memory_eng.h"
#include "../../execution/include/registers.h"

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>

// Building with C17 standard, so we can use static_assert (src must be built)
// gcc -std=c17 -Wall -Wextra -Werror -o test_operations test_operations.c ../../execution/src/operations.c ../../execution/src/memory_eng.c ../../execution/src/registers.c

// --- Test helpers ---

static int tests_run    = 0;
static int tests_passed = 0;

#define TEST(name) static void name(void)

#define RUN(name) \
    do { \
        printf("  %-60s", #name); \
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

// ---------------------------------------------------------------------------
// Shared fixture helpers
// ---------------------------------------------------------------------------

// Build a fully wired-up Info* ready for dispatch tests.
// Caller is responsible for freeing info, regs, and table.
static Info *make_info(CPURegs **out_regs, Table **out_table)
{
    Info    *info  = create_operand_state();
    CPURegs *regs  = CPURegs_create();
    Table   *table = table_init();

    if (!info || !regs || !table) return NULL;

    set_registers_ref(info, regs);
    set_table_ref(info, table);

    if (out_regs)  *out_regs  = regs;
    if (out_table) *out_table = table;
    return info;
}

static void destroy_info(Info *info, CPURegs *regs, Table *table)
{
    free_operand_state(info);
    CPURegs_free(regs);
    free_table(table);
}

// Register IDs — adjust to match your enum/defines
#define REG_A  0
#define REG_B  1
#define REG_C  2

// -----------------------------------------------------------------------
// Tests — lifecycle
// -----------------------------------------------------------------------

// 1. create_operand_state() returns non-NULL
TEST(test_create_operand_state_not_null)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    free_operand_state(info);
}

// 2. free_operand_state() doesn't crash
TEST(test_free_operand_state_no_crash)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    free_operand_state(info);
}

// -----------------------------------------------------------------------
// Tests — set_registers_ref / set_table_ref (must not crash)
// -----------------------------------------------------------------------

// 3. Attaching a register file doesn't crash
TEST(test_set_registers_ref_no_crash)
{
    Info    *info = create_operand_state();
    CPURegs *regs = CPURegs_create();
    ASSERT(info && regs);

    set_registers_ref(info, regs);   // must not crash

    free_operand_state(info);
    CPURegs_free(regs);
}

// 4. Attaching a memory table doesn't crash
TEST(test_set_table_ref_no_crash)
{
    Info  *info  = create_operand_state();
    Table *table = table_init();
    ASSERT(info && table);

    set_table_ref(info, table);   // must not crash

    free_operand_state(info);
    free_table(table);
}

// -----------------------------------------------------------------------
// Tests — set_instruction / set_operand_info / clean
// -----------------------------------------------------------------------

// 5. set_instruction doesn't crash for a known mnemonic
TEST(test_set_instruction_no_crash)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);

    set_instruction(info, "add");   // must not crash

    free_operand_state(info);
}

// 6. set_operand_info doesn't crash with valid arguments
TEST(test_set_operand_info_no_crash)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);

    // operand string, address=0, value=42, size hint=8
    set_operand_info(info, "rax", 0LL, 42LL, 8, "int", 1);

    free_operand_state(info);
}

// 7. clean() resets state without crashing
TEST(test_clean_no_crash)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);

    set_instruction(info, "add");
    clean(info);   // must not crash

    free_operand_state(info);
}

// 8. After clean(), a second instruction can be set without issues
TEST(test_reuse_after_clean)
{
    Info *info = create_operand_state();
    ASSERT(info != NULL);

    set_instruction(info, "add");
    clean(info);
    set_instruction(info, "sub");   // must not crash

    free_operand_state(info);
}

// -----------------------------------------------------------------------
// Tests — dispatch with ALU operations
// All tests below follow the pattern:
//   1. Prime registers with known values
//   2. Build an Info* describing the operation
//   3. Call dispatch()
//   4. Read the result register and assert correctness
// -----------------------------------------------------------------------

// Helper: set a 64-bit register value
static void set64(CPURegs *r, uint8_t reg, uint64_t v)
{
    write_reg(r, reg, (int64_t)v, 8, 0);
}
static uint64_t get64(CPURegs *r, uint8_t reg)
{
    return read_8b_reg(r, reg);
}

// 9. ADD — dispatch "ADD rax, rbx" and verify rax = rax + rbx
TEST(test_dispatch_add)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 10);
    set64(regs, REG_B, 32);

    set_instruction(info, "add");
    set_operand_info(info, "rax", 0LL, 10LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 32LL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);

    destroy_info(info, regs, table);
}

// 10. SUB — dispatch "SUB rax, rbx" and verify rax = rax - rbx
TEST(test_dispatch_sub)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 100);
    set64(regs, REG_B, 58);

    set_instruction(info, "sub");
    set_operand_info(info, "rax", 0LL, 100LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 58LL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);

    destroy_info(info, regs, table);
}

// 11. AND — dispatch "AND rax, rbx"
TEST(test_dispatch_and)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xFF);
    set64(regs, REG_B, 0x0F);

    set_instruction(info, "and");
    set_operand_info(info, "rax", 0LL, 0xFFLL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 0x0FLL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0x0F);

    destroy_info(info, regs, table);
}

// 12. OR — dispatch "OR rax, rbx"
TEST(test_dispatch_or)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xF0);
    set64(regs, REG_B, 0x0F);

    set_instruction(info, "or");
    set_operand_info(info, "rax", 0LL, 0xF0LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 0x0FLL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0xFF);

    destroy_info(info, regs, table);
}

// 13. XOR — dispatch "XOR rax, rax" (self-XOR zeroes the register)
TEST(test_dispatch_xor_self)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xDEADBEEF);

    set_instruction(info, "xor");
    set_operand_info(info, "rax", 0LL, 0xDEADBEEFLL, 8, "int", 1);
    set_operand_info(info, "rax", 0LL, 0xDEADBEEFLL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0);

    destroy_info(info, regs, table);
}

// 14. MOV — dispatch "MOV rax, rbx" copies value
TEST(test_dispatch_mov)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0);
    set64(regs, REG_B, 0x1234567890ABCDEFULL);

    set_instruction(info, "mov");
    set_operand_info(info, "rax", 0LL, 0LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 0x1234567890ABCDEFLL, 8, "int", 1);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0x1234567890ABCDEFULL);

    destroy_info(info, regs, table);
}

// 15. ADD sets zero flag when result is 0
TEST(test_dispatch_add_sets_zero_flag)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, (uint64_t)-1LL);  // 0xFFFF...
    set64(regs, REG_B, 1);

    set_instruction(info, "add");
    set_operand_info(info, "rax", 0LL, (long long)-1LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 1LL, 8, "int", 1);

    dispatch(info);

    // Result wraps to 0 → ZF should be set
    ASSERT(read_zero_flag(regs) != 0);

    destroy_info(info, regs, table);
}

// 16. SUB sets zero flag when operands are equal
TEST(test_dispatch_sub_sets_zero_flag)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 77);
    set64(regs, REG_B, 77);

    set_instruction(info, "sub");
    set_operand_info(info, "rax", 0LL, 77LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 77LL, 8, "int", 1);

    dispatch(info);

    ASSERT(read_zero_flag(regs) != 0);

    destroy_info(info, regs, table);
}

// 17. clean() between dispatches — state doesn't bleed across instructions
TEST(test_dispatch_clean_between_instructions)
{
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    // First instruction: ADD rax=5, rbx=3 → rax=8
    set64(regs, REG_A, 5);
    set64(regs, REG_B, 3);
    set_instruction(info, "add");
    set_operand_info(info, "rax", 0LL, 5LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 3LL, 8, "int", 1);
    dispatch(info);
    ASSERT(get64(regs, REG_A) == 8);

    clean(info);

    // Second instruction: MOV rax=0, rbx=99 → rax=99
    set64(regs, REG_B, 99);
    set_instruction(info, "mov");
    set_operand_info(info, "rax", 0LL, 0LL, 8, "int", 1);
    set_operand_info(info, "rbx", 0LL, 99LL, 8, "int", 1);
    dispatch(info);
    ASSERT(get64(regs, REG_A) == 99);

    destroy_info(info, regs, table);
}

// -----------------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------------

int main(void)
{
    printf("=== operand / dispatch tests ===\n\n");

    // Lifecycle
    RUN(test_create_operand_state_not_null);
    RUN(test_free_operand_state_no_crash);

    // Ref setters
    RUN(test_set_registers_ref_no_crash);
    RUN(test_set_table_ref_no_crash);

    // Info setters / clean
    RUN(test_set_instruction_no_crash);
    RUN(test_set_operand_info_no_crash);
    RUN(test_clean_no_crash);
    RUN(test_reuse_after_clean);

    // ALU dispatch
    RUN(test_dispatch_add);
    RUN(test_dispatch_sub);
    RUN(test_dispatch_and);
    RUN(test_dispatch_or);
    RUN(test_dispatch_xor_self);
    RUN(test_dispatch_mov);
    RUN(test_dispatch_add_sets_zero_flag);
    RUN(test_dispatch_sub_sets_zero_flag);
    RUN(test_dispatch_clean_between_instructions);

    printf("\n%d / %d tests passed.\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}