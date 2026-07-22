#include "../../execution/include/operations.h"
#include "../../execution/include/memory_eng.h"
#include "../../execution/include/registers.h"

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>

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

#define REG_A  0
#define REG_B  1
#define REG_C  2

static void set64(CPURegs *r, uint8_t reg, uint64_t v) {
    write_reg(r, reg, (int64_t)v, 8, 0);
}

static uint64_t get64(CPURegs *r, uint8_t reg) {
    return read_8b_reg(r, reg);
}

// -----------------------------------------------------------------------
// Tests — lifecycle & state management
// -----------------------------------------------------------------------

TEST(test_create_operand_state_not_null) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    free_operand_state(info);
}

TEST(test_free_operand_state_no_crash) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    free_operand_state(info);
}

TEST(test_set_registers_ref_no_crash) {
    Info    *info = create_operand_state();
    CPURegs *regs = CPURegs_create();
    ASSERT(info && regs);
    set_registers_ref(info, regs);
    free_operand_state(info);
    CPURegs_free(regs);
}

TEST(test_set_table_ref_no_crash) {
    Info  *info  = create_operand_state();
    Table *table = table_init();
    ASSERT(info && table);
    set_table_ref(info, table);
    free_operand_state(info);
    free_table(table);
}

TEST(test_set_instruction_no_crash) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    set_instruction(info, OP_ADD);
    free_operand_state(info);
}

TEST(test_set_operand_info_no_crash) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    // Updated: matches set_operand_info signature with OpType enum and is_signed parameter
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    free_operand_state(info);
}

TEST(test_clean_no_crash) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    set_instruction(info, OP_ADD);
    clean(info);
    free_operand_state(info);
}

TEST(test_reuse_after_clean) {
    Info *info = create_operand_state();
    ASSERT(info != NULL);
    set_instruction(info, OP_ADD);
    clean(info);
    set_instruction(info, OP_SUB);
    free_operand_state(info);
}

// -----------------------------------------------------------------------
// Tests — dispatch with ALU operations
// -----------------------------------------------------------------------

TEST(test_dispatch_add) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 10);
    set64(regs, REG_B, 32);

    set_instruction(info, OP_ADD);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_sub) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 100);
    set64(regs, REG_B, 58);

    set_instruction(info, OP_SUB);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_and) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xFF);
    set64(regs, REG_B, 0x0F);

    set_instruction(info, OP_AND);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0x0F);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_or) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xF0);
    set64(regs, REG_B, 0x0F);

    set_instruction(info, OP_OR);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0xFF);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_xor_self) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0xDEADBEEF);

    set_instruction(info, OP_XOR);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_A, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_xchg) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0x1111);
    set64(regs, REG_B, 0x9999);

    set_instruction(info, OP_XCHG);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0x9999);
    ASSERT(get64(regs, REG_B) == 0x1111);

    destroy_info(info, regs, table);
}

TEST(test_dispatch_inc) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 41);

    set_instruction(info, OP_INC);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_dec) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 43);

    set_instruction(info, OP_DEC);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 42);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_not) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 0x00000000FFFFFFFFULL);

    set_instruction(info, OP_NOT);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(get64(regs, REG_A) == 0xFFFFFFFF00000000ULL);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_neg) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 5);

    set_instruction(info, OP_NEG);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 1);

    dispatch(info);

    ASSERT((int64_t)get64(regs, REG_A) == -5);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_add_sets_zero_flag) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, (uint64_t)-1LL); 
    set64(regs, REG_B, 1);

    set_instruction(info, OP_ADD);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(read_zero_flag(regs) != 0);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_sub_sets_zero_flag) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 77);
    set64(regs, REG_B, 77);

    set_instruction(info, OP_SUB);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);

    dispatch(info);

    ASSERT(read_zero_flag(regs) != 0);
    destroy_info(info, regs, table);
}

TEST(test_dispatch_clean_between_instructions) {
    CPURegs *regs; Table *table;
    Info *info = make_info(&regs, &table);
    ASSERT(info != NULL);

    set64(regs, REG_A, 5);
    set64(regs, REG_B, 3);
    set_instruction(info, OP_ADD);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_B, 8, OP_REGISTER, 0, 0);
    dispatch(info);
    ASSERT(get64(regs, REG_A) == 8);

    clean(info);

    set64(regs, REG_A, 99);
    set_instruction(info, OP_XOR);
    set_operand_info(info, "op1", REG_A, 8, OP_REGISTER, 0, 0);
    set_operand_info(info, "op2", REG_A, 8, OP_REGISTER, 0, 0);
    dispatch(info);
    ASSERT(get64(regs, REG_A) == 0);

    destroy_info(info, regs, table);
}

// -----------------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------------

int main(void)
{
    printf("=== operand / dispatch tests ===\n\n");

    RUN(test_create_operand_state_not_null);
    RUN(test_free_operand_state_no_crash);
    RUN(test_set_registers_ref_no_crash);
    RUN(test_set_table_ref_no_crash);
    RUN(test_set_instruction_no_crash);
    RUN(test_set_operand_info_no_crash);
    RUN(test_clean_no_crash);
    RUN(test_reuse_after_clean);

    RUN(test_dispatch_add);
    RUN(test_dispatch_sub);
    RUN(test_dispatch_and);
    RUN(test_dispatch_or);
    RUN(test_dispatch_xor_self);
    RUN(test_dispatch_xchg);
    RUN(test_dispatch_inc);
    RUN(test_dispatch_dec);
    RUN(test_dispatch_not);
    RUN(test_dispatch_neg);
    RUN(test_dispatch_add_sets_zero_flag);
    RUN(test_dispatch_sub_sets_zero_flag);
    RUN(test_dispatch_clean_between_instructions);

    printf("\n%d / %d tests passed.\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}