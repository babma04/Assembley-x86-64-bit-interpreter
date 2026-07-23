"""
Unit tests for FUs/data_path.py

Strategy
--------
Data_Path has no ctypes/.so dependency -- it's pure Python operating on
Registers_Interface and Data_Memory. We hand it MagicMock(spec=...) for
both (same pattern as test_data_manager.py) so we can control read_reg /
read_zero / read_carry / etc. return values and assert on write calls,
without needing real register/memory internals.

Focus is the execution side: each execute_j* condition, execute_mov's
type-driven read/write branches, execute_lea, and the validate_* /
execute() dispatch and error-wrapping behavior.

Run with: pytest tests/FUs/test_data_path.py -v
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from _src.FUs.data_path import Data_Path, DATA_PATH_OPCODES


def make_op(address=0, type_=1, size=4, is_high=0, is_signed=0, expression="rax", valid=True):
    """
    Fake Operand. type_ follows the project convention seen in
    validate_lea_conditions / validate_mov_conditions:
      1 = REGISTER, 2 = MEMORY, 3 = IMMEDIATE
    """
    op = SimpleNamespace(
        address=address, type=type_, size=size,
        is_high=is_high, is_signed=is_signed, expression=expression,
    )
    op.is_valid = lambda: valid
    return op


INVALID_OP = make_op(valid=False)


@pytest.fixture
def mock_registers():
    return MagicMock()


@pytest.fixture
def mock_memory():
    return MagicMock()


@pytest.fixture
def labels():
    return {"loop_start": 42, "end": 100}


@pytest.fixture
def dp(mock_registers, mock_memory, labels):
    return Data_Path(registers=mock_registers, memory=mock_memory, labels=labels)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_stores_registers_memory_and_labels(self, mock_registers, mock_memory, labels):
        instance = Data_Path(registers=mock_registers, memory=mock_memory, labels=labels)
        assert instance.registers is mock_registers
        assert instance.memory is mock_memory
        assert instance.labels is labels

    def test_execute_map_has_one_entry_per_opcode(self, dp):
        # lea, mov, jmp + 30 conditional jump entries (with aliases) = 33
        assert len(dp._execute_data_path_map) == 33

    def test_execute_map_entries_are_bound_to_instance(self, dp):
        assert dp._execute_data_path_map[0] == dp.execute_lea
        assert dp._execute_data_path_map[1] == dp.execute_mov
        assert dp._execute_data_path_map[2] == dp.execute_jmp


# ---------------------------------------------------------------------------
# load_values
# ---------------------------------------------------------------------------

class TestLoadValues:
    def test_sets_opcode_from_instruction_name(self, dp):
        dp.load_values("mov", make_op(), make_op())
        assert dp.opcode == DATA_PATH_OPCODES["mov"]

    def test_stores_valid_operands(self, dp):
        op1 = make_op(expression="rax")
        op2 = make_op(expression="rbx")
        dp.load_values("mov", op1, op2)
        assert dp.op1 is op1
        assert dp.op2 is op2

    def test_invalid_op1_is_not_stored(self, dp):
        dp.op1 = "sentinel"
        dp.load_values("jmp", INVALID_OP, make_op())
        assert dp.op1 == "sentinel"  # untouched, not overwritten

    def test_invalid_op2_is_not_stored(self, dp):
        dp.op2 = "sentinel"
        dp.load_values("jmp", make_op(), INVALID_OP)
        assert dp.op2 == "sentinel"

    def test_none_operands_are_not_stored(self, dp):
        dp.op1 = "sentinel1"
        dp.op2 = "sentinel2"
        dp.load_values("jmp", None, None)
        assert dp.op1 == "sentinel1"
        assert dp.op2 == "sentinel2"


# ---------------------------------------------------------------------------
# get_opcode
# ---------------------------------------------------------------------------

class TestGetOpcode:
    def test_known_instruction_returns_table_index(self):
        assert Data_Path.get_opcode("mov") == DATA_PATH_OPCODES["mov"]

    def test_lookup_is_case_insensitive(self):
        assert Data_Path.get_opcode("MOV") == DATA_PATH_OPCODES["mov"]
        assert Data_Path.get_opcode("Jmp") == DATA_PATH_OPCODES["jmp"]

    def test_unknown_instruction_returns_minus_one(self):
        assert Data_Path.get_opcode("not_a_real_instruction") == -1


# ---------------------------------------------------------------------------
# validate_data_path_instruction (dispatch to the right validator)
# ---------------------------------------------------------------------------

class TestValidateDispatch:
    def test_opcode_0_routes_to_lea_validation(self, dp):
        dp.opcode = 0
        dp.op1 = make_op(type_=1)
        dp.op2 = make_op(type_=2)
        dp.validate_data_path_instruction()  # should not raise

    def test_opcode_1_routes_to_mov_validation(self, dp):
        dp.opcode = 1
        dp.op1 = make_op(type_=1, size=4)
        dp.op2 = make_op(type_=3, size=4)
        dp.validate_data_path_instruction()  # should not raise

    @pytest.mark.parametrize("opcode", [2, 12, 17, 25, 32])
    def test_jump_opcodes_across_full_range_route_to_jump_validation(self, dp, opcode):
        dp.opcode = opcode
        dp.op1 = make_op(valid=True)
        dp.op2 = INVALID_OP
        dp.validate_data_path_instruction()  # should not raise

    def test_opcode_above_map_length_raises_not_implemented(self, dp):
        dp.opcode = len(dp._execute_data_path_map)  # one past the last valid index
        with pytest.raises(NotImplementedError):
            dp.validate_data_path_instruction()

    def test_negative_opcode_raises_not_implemented(self, dp):
        dp.opcode = -1
        with pytest.raises(NotImplementedError):
            dp.validate_data_path_instruction()


# ---------------------------------------------------------------------------
# validate_lea_conditions
# ---------------------------------------------------------------------------

class TestValidateLea:
    def test_valid_register_dest_and_memory_source_passes(self, dp):
        dp.op1 = make_op(type_=1)
        dp.op2 = make_op(type_=2)
        dp.validate_lea_conditions()  # should not raise

    def test_invalid_op1_raises(self, dp):
        dp.op1 = INVALID_OP
        dp.op2 = make_op(type_=2)
        with pytest.raises(SyntaxError):
            dp.validate_lea_conditions()

    def test_invalid_op2_raises(self, dp):
        dp.op1 = make_op(type_=1)
        dp.op2 = INVALID_OP
        with pytest.raises(SyntaxError):
            dp.validate_lea_conditions()

    def test_non_register_destination_raises(self, dp):
        dp.op1 = make_op(type_=2)  # memory, not register
        dp.op2 = make_op(type_=2)
        with pytest.raises(SyntaxError):
            dp.validate_lea_conditions()

    def test_non_memory_source_raises(self, dp):
        dp.op1 = make_op(type_=1)
        dp.op2 = make_op(type_=1)  # register, not memory expression
        with pytest.raises(SyntaxError):
            dp.validate_lea_conditions()


# ---------------------------------------------------------------------------
# validate_mov_conditions
# ---------------------------------------------------------------------------

class TestValidateMov:
    def test_register_to_register_passes(self, dp):
        dp.op1 = make_op(type_=1, size=4)
        dp.op2 = make_op(type_=1, size=4)
        dp.validate_mov_conditions()  # should not raise

    def test_immediate_to_register_passes(self, dp):
        dp.op1 = make_op(type_=1, size=4)
        dp.op2 = make_op(type_=3, size=4)
        dp.validate_mov_conditions()  # should not raise

    def test_invalid_operands_raise(self, dp):
        dp.op1 = INVALID_OP
        dp.op2 = make_op()
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_immediate_destination_raises(self, dp):
        dp.op1 = make_op(type_=3)
        dp.op2 = make_op(type_=1)
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_writing_to_rodata_address_raises(self, dp):
        dp.op1 = make_op(type_=2, address=0x1000, size=4)  # below 0x600000
        dp.op2 = make_op(type_=1, size=4)
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_writing_to_writable_memory_address_passes(self, dp):
        dp.op1 = make_op(type_=2, address=0x700000, size=4)
        dp.op2 = make_op(type_=1, size=4)
        dp.validate_mov_conditions()  # should not raise

    def test_memory_to_memory_raises(self, dp):
        dp.op1 = make_op(type_=2, address=0x700000, size=4)
        dp.op2 = make_op(type_=2, size=4)
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_size_mismatch_raises(self, dp):
        dp.op1 = make_op(type_=1, size=4)
        dp.op2 = make_op(type_=1, size=8)
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_size_mismatch_ignored_for_immediate_source(self, dp):
        # rule 5 explicitly skips the size check when op2 is immediate (type 3)
        dp.op1 = make_op(type_=1, size=4)
        dp.op2 = make_op(type_=3, size=8)
        dp.validate_mov_conditions()  # should not raise

    def test_high_byte_register_mixed_with_64bit_raises(self, dp):
        dp.op1 = make_op(type_=1, size=1, is_high=1)
        dp.op2 = make_op(type_=1, size=8, is_high=0)
        with pytest.raises(SyntaxError):
            dp.validate_mov_conditions()

    def test_high_byte_register_mixed_with_matching_high_passes(self, dp):
        dp.op1 = make_op(type_=1, size=1, is_high=1)
        dp.op2 = make_op(type_=1, size=1, is_high=1)
        dp.validate_mov_conditions()  # should not raise


# ---------------------------------------------------------------------------
# validate_jump_conditions
# ---------------------------------------------------------------------------

class TestValidateJump:
    def test_single_valid_operand_passes(self, dp):
        dp.op1 = make_op(valid=True)
        dp.op2 = INVALID_OP
        dp.validate_jump_conditions()  # should not raise

    def test_missing_destination_raises(self, dp):
        dp.op1 = INVALID_OP
        dp.op2 = INVALID_OP
        with pytest.raises(SyntaxError):
            dp.validate_jump_conditions()

    def test_extra_second_operand_raises(self, dp):
        dp.op1 = make_op(valid=True)
        dp.op2 = make_op(valid=True)
        with pytest.raises(SyntaxError):
            dp.validate_jump_conditions()


# ---------------------------------------------------------------------------
# execute_lea
# ---------------------------------------------------------------------------

class TestExecuteLea:
    def test_writes_op2_address_into_op1_register(self, dp, mock_registers):
        dp.op1 = make_op(type_=1, expression="rax")
        dp.op2 = make_op(type_=2, address=0xABCD)

        dp.execute_lea()

        mock_registers.write_reg.assert_called_once_with("rax", 0xABCD)

    def test_does_not_touch_memory(self, dp, mock_memory):
        dp.op1 = make_op(type_=1, expression="rax")
        dp.op2 = make_op(type_=2, address=0xABCD)

        dp.execute_lea()

        mock_memory.read_bytes.assert_not_called()
        mock_memory.write_bytes.assert_not_called()


# ---------------------------------------------------------------------------
# execute_mov
# ---------------------------------------------------------------------------

class TestExecuteMov:
    def test_immediate_to_register(self, dp, mock_registers):
        dp.op1 = make_op(type_=1, expression="rax", size=4)
        dp.op2 = make_op(type_=3, address=42)

        dp.execute_mov()

        mock_registers.write_reg.assert_called_once_with("rax", 42)

    def test_register_to_register(self, dp, mock_registers):
        mock_registers.read_reg.return_value = 99
        dp.op1 = make_op(type_=1, expression="rax", size=4)
        dp.op2 = make_op(type_=1, expression="rbx", size=4)

        dp.execute_mov()

        mock_registers.read_reg.assert_called_once_with("rbx")
        mock_registers.write_reg.assert_called_once_with("rax", 99)

    def test_memory_to_register(self, dp, mock_registers, mock_memory):
        mock_memory.read_bytes.return_value = (7).to_bytes(4, "little")
        dp.op1 = make_op(type_=1, expression="rax", size=4)
        dp.op2 = make_op(type_=2, address=0x2000, size=4)

        dp.execute_mov()

        mock_memory.read_bytes.assert_called_once_with(0x2000, 4)
        mock_registers.write_reg.assert_called_once_with("rax", 7)

    def test_register_to_memory(self, dp, mock_registers, mock_memory):
        mock_registers.read_reg.return_value = 0x11
        dp.op1 = make_op(type_=2, address=0x3000, size=4)
        dp.op2 = make_op(type_=1, expression="rax", size=4)

        dp.execute_mov()

        write_args = mock_memory.write_bytes.call_args[0]
        assert write_args[0] == 0x3000
        assert write_args[1] == (0x11).to_bytes(4, "little")
        assert write_args[2] == 4

    def test_immediate_to_memory_masks_to_destination_size(self, dp, mock_memory):
        dp.op1 = make_op(type_=2, address=0x3000, size=1)
        dp.op2 = make_op(type_=3, address=0x1FF)  # 511, doesn't fit in 1 byte

        dp.execute_mov()

        write_args = mock_memory.write_bytes.call_args[0]
        assert write_args[1] == (0x1FF & 0xFF).to_bytes(1, "little")

    def test_memory_to_memory_writes_raw_bytes_unmodified(self, dp, mock_memory):
        raw = (55).to_bytes(4, "little")
        mock_memory.read_bytes.return_value = raw
        dp.op1 = make_op(type_=2, address=0x4000, size=4)
        dp.op2 = make_op(type_=2, address=0x5000, size=4)

        dp.execute_mov()

        write_args = mock_memory.write_bytes.call_args[0]
        assert write_args[1] == raw


# ---------------------------------------------------------------------------
# execute_jmp
# ---------------------------------------------------------------------------

class TestExecuteJmp:
    def test_known_label_returns_its_index(self, dp, labels):
        dp.op1 = make_op(expression="loop_start")
        assert dp.execute_jmp() == labels["loop_start"]

    def test_unknown_label_returns_minus_one(self, dp):
        dp.op1 = make_op(expression="nonexistent_label")
        assert dp.execute_jmp() == -1


# ---------------------------------------------------------------------------
# Conditional jump wrappers
#
# Each wrapper's own return value is discarded by design (the control unit
# elsewhere re-derives the target from execute_jmp's return through a
# separate call path outside this class), so what's observable -- and
# what these test -- is whether execute_jmp gets invoked given the flag
# state, not what it returns from inside the wrapper.
# ---------------------------------------------------------------------------

class TestConditionalJumps:
    def test_je_jumps_when_zero_flag_set(self, dp, mock_registers):
        mock_registers.read_zero.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_je()
            jmp.assert_called_once()

    def test_je_does_not_jump_when_zero_flag_clear(self, dp, mock_registers):
        mock_registers.read_zero.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_je()
            jmp.assert_not_called()

    def test_jne_jumps_when_zero_flag_clear(self, dp, mock_registers):
        mock_registers.read_zero.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jne()
            jmp.assert_called_once()

    def test_jne_does_not_jump_when_zero_flag_set(self, dp, mock_registers):
        mock_registers.read_zero.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jne()
            jmp.assert_not_called()

    def test_jb_jumps_when_carry_flag_set(self, dp, mock_registers):
        mock_registers.read_carry.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jb()
            jmp.assert_called_once()

    def test_jb_does_not_jump_when_carry_flag_clear(self, dp, mock_registers):
        mock_registers.read_carry.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jb()
            jmp.assert_not_called()

    def test_jnb_jumps_when_carry_flag_clear(self, dp, mock_registers):
        mock_registers.read_carry.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jnb()
            jmp.assert_called_once()

    def test_jnb_does_not_jump_when_carry_flag_set(self, dp, mock_registers):
        mock_registers.read_carry.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jnb()
            jmp.assert_not_called()

    @pytest.mark.parametrize("carry,zero,should_jump", [
        (False, False, True),
        (True, False, False),
        (False, True, False),
        (True, True, False),
    ])
    def test_ja_jumps_only_when_carry_and_zero_both_clear(self, dp, mock_registers, carry, zero, should_jump):
        mock_registers.read_carry.return_value = carry
        mock_registers.read_zero.return_value = zero
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_ja()
            assert jmp.called is should_jump

    @pytest.mark.parametrize("carry,zero,should_jump", [
        (True, False, True),
        (False, True, True),
        (True, True, True),
        (False, False, False),
    ])
    def test_jbe_jumps_when_carry_or_zero_set(self, dp, mock_registers, carry, zero, should_jump):
        mock_registers.read_carry.return_value = carry
        mock_registers.read_zero.return_value = zero
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jbe()
            assert jmp.called is should_jump

    @pytest.mark.parametrize("sf,of,should_jump", [
        (True, False, True),
        (False, True, True),
        (True, True, False),
        (False, False, False),
    ])
    def test_jl_jumps_when_sign_and_overflow_differ(self, dp, mock_registers, sf, of, should_jump):
        mock_registers.read_sign.return_value = sf
        mock_registers.read_overflow.return_value = of
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jl()
            assert jmp.called is should_jump

    @pytest.mark.parametrize("zf,sf,of,should_jump", [
        (False, True, True, True),
        (False, False, False, True),
        (True, True, True, False),
        (False, True, False, False),
    ])
    def test_jg_jumps_when_not_zero_and_sign_equals_overflow(self, dp, mock_registers, zf, sf, of, should_jump):
        mock_registers.read_zero.return_value = zf
        mock_registers.read_sign.return_value = sf
        mock_registers.read_overflow.return_value = of
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jg()
            assert jmp.called is should_jump

    @pytest.mark.parametrize("sf,of,should_jump", [
        (True, True, True),
        (False, False, True),
        (True, False, False),
        (False, True, False),
    ])
    def test_jge_jumps_when_sign_equals_overflow(self, dp, mock_registers, sf, of, should_jump):
        mock_registers.read_sign.return_value = sf
        mock_registers.read_overflow.return_value = of
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jge()
            assert jmp.called is should_jump

    @pytest.mark.parametrize("zf,sf,of,should_jump", [
        (True, True, True, True),
        (False, True, False, True),
        (False, True, True, False),
        (False, False, False, False),
    ])
    def test_jle_jumps_when_zero_or_sign_differs_from_overflow(self, dp, mock_registers, zf, sf, of, should_jump):
        mock_registers.read_zero.return_value = zf
        mock_registers.read_sign.return_value = sf
        mock_registers.read_overflow.return_value = of
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jle()
            assert jmp.called is should_jump

    def test_js_jumps_when_sign_flag_set(self, dp, mock_registers):
        mock_registers.read_sign.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_js()
            jmp.assert_called_once()

    def test_js_does_not_jump_when_sign_flag_clear(self, dp, mock_registers):
        mock_registers.read_sign.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_js()
            jmp.assert_not_called()

    def test_jns_jumps_when_sign_flag_clear(self, dp, mock_registers):
        mock_registers.read_sign.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jns()
            jmp.assert_called_once()

    def test_jns_does_not_jump_when_sign_flag_set(self, dp, mock_registers):
        mock_registers.read_sign.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jns()
            jmp.assert_not_called()

    def test_jo_jumps_when_overflow_flag_set(self, dp, mock_registers):
        mock_registers.read_overflow.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jo()
            jmp.assert_called_once()

    def test_jo_does_not_jump_when_overflow_flag_clear(self, dp, mock_registers):
        mock_registers.read_overflow.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jo()
            jmp.assert_not_called()

    def test_jno_jumps_when_overflow_flag_clear(self, dp, mock_registers):
        mock_registers.read_overflow.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jno()
            jmp.assert_called_once()

    def test_jno_does_not_jump_when_overflow_flag_set(self, dp, mock_registers):
        mock_registers.read_overflow.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jno()
            jmp.assert_not_called()

    def test_jp_jumps_when_parity_flag_set(self, dp, mock_registers):
        mock_registers.read_parity.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jp()
            jmp.assert_called_once()

    def test_jp_does_not_jump_when_parity_flag_clear(self, dp, mock_registers):
        mock_registers.read_parity.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jp()
            jmp.assert_not_called()

    def test_jnp_jumps_when_parity_flag_clear(self, dp, mock_registers):
        mock_registers.read_parity.return_value = False
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jnp()
            jmp.assert_called_once()

    def test_jnp_does_not_jump_when_parity_flag_set(self, dp, mock_registers):
        mock_registers.read_parity.return_value = True
        with patch.object(type(dp), "execute_jmp") as jmp:
            dp.execute_jnp()
            jmp.assert_not_called()


# ---------------------------------------------------------------------------
# execute() -- full dispatch + error wrapping
# ---------------------------------------------------------------------------

class TestExecuteDispatch:
    def test_valid_mov_runs_without_raising(self, dp, mock_registers):
        dp.opcode = DATA_PATH_OPCODES["mov"]
        dp.op1 = make_op(type_=1, expression="rax", size=4)
        dp.op2 = make_op(type_=3, address=5)

        dp.execute()

        mock_registers.write_reg.assert_called_once_with("rax", 5)

    def test_invalid_operands_raise_runtime_error(self, dp):
        dp.opcode = DATA_PATH_OPCODES["mov"]
        dp.op1 = INVALID_OP
        dp.op2 = make_op()

        with pytest.raises(RuntimeError):
            dp.execute()

    def test_unimplemented_opcode_raises_runtime_error(self, dp):
        dp.opcode = -1

        with pytest.raises(RuntimeError):
            dp.execute()

    def test_syntax_error_is_reraised_as_runtime_error(self, dp, capsys):
        dp.opcode = DATA_PATH_OPCODES["lea"]
        dp.op1 = make_op(type_=2)  # wrong: LEA dest must be a register
        dp.op2 = make_op(type_=2)

        with pytest.raises(RuntimeError):
            dp.execute()

    def test_dispatches_to_correct_handler_by_opcode(self, dp, mock_registers):
        dp.opcode = DATA_PATH_OPCODES["lea"]
        dp.op1 = make_op(type_=1, expression="rbx")
        dp.op2 = make_op(type_=2, address=0x9999)

        dp.execute()

        mock_registers.write_reg.assert_called_once_with("rbx", 0x9999)