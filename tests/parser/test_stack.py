import pytest
import sys
from unittest.mock import MagicMock
from parsing.segment_mapper import Segment_Mapper 

# --- FIXTURES ---

@pytest.fixture
def dummy_mapper():
    """
    Creates a Segment_Mapper instance bypassing the __init__ constructor.
    This means it NEVER tries to open 'dummy.asm' or any JSON files,
    allowing us to strictly unit test the stack methods.
    """
    mapper = Segment_Mapper.__new__(Segment_Mapper)
    mapper.registers = MagicMock()
    mapper.memory = MagicMock()
    
    # Setup mock register behaviors
    mapper.mock_rsp = 0x7fffffffe000
    
    def read_reg_mock(reg):
        if reg == "rsp":
            return mapper.mock_rsp
        return 0
        
    def write_reg_mock(reg, val, update_flags=False):
        if reg == "rsp":
            mapper.mock_rsp = val

    mapper.registers.read_reg.side_effect = read_reg_mock
    mapper.registers.write_reg.side_effect = write_reg_mock
    
    # Mock memory push to decrement the mock rsp by the size of the push
    def push_mock(data: bytes):
        mapper.mock_rsp -= len(data)
        
    mapper.memory.push.side_effect = push_mock
    return mapper

# --- TESTS ---

class TestStackInitialization:

    def test_full_stack_setup_integration(self, dummy_mapper):
        """
        Verifies the entire stack initialization process (strings -> pointers -> NULL -> argc -> alignment).
        No dummy files required!
        """
        argv = ["./prog", "-arg"]
        start_rsp = 0x7fffffffe000
        
        # Act
        dummy_mapper.initialize_stack(
            argvcount=2,
            argv=argv,
            memory=dummy_mapper.memory,
            stack_limit=0x7fff00000000,
            stack_start=start_rsp
        )
        
        # Assert memory was utilized
        assert dummy_mapper.memory.push.called
        
        # Assert rsp was moved down (stack grew)
        assert dummy_mapper.mock_rsp < start_rsp
        
        # Assert the stack is perfectly 16-byte aligned at the end of setup
        assert dummy_mapper.mock_rsp % 16 == 0

        # Validate the specific sequence of pushes for the System V AMD64 ABI layout
        push_calls = dummy_mapper.memory.push.call_args_list
        
        # The 2nd to last push should be the NULL pointer separating argv from envp/argc
        second_to_last_push = push_calls[-2][0][0]
        assert second_to_last_push == (0).to_bytes(8, "little"), "Missing NULL pointer before argc"
        
        # The final push should be argc
        final_push = push_calls[-1][0][0]
        assert final_push == (2).to_bytes(8, "little"), "argc was not pushed correctly"

    def test_push_arguments_pointer_accuracy(self, dummy_mapper):
        """Tests that strings are pushed backwards and pointers are captured correctly."""
        argv = ["./prog", "arg1"]
        
        # Act
        pointers = dummy_mapper.push_arguments(argv)
        
        # Assert
        assert len(pointers) == 2
        assert dummy_mapper.memory.push.called
        assert dummy_mapper.mock_rsp < 0x7fffffffe000

    def test_initialize_stack_no_args(self, dummy_mapper):
        """Tests stack setup when argv is empty or None."""
        dummy_mapper.initialize_stack(
            argvcount=0, 
            argv=None, 
            memory=dummy_mapper.memory, 
            stack_limit=0x7fff00000000, 
            stack_start=0x7fffffffe000
        )
        
        # Should push NULL and argc=0
        push_calls = dummy_mapper.memory.push.call_args_list
        assert push_calls[-2][0][0] == (0).to_bytes(8, "little") # NULL pointer
        assert push_calls[-1][0][0] == (0).to_bytes(8, "little") # argc = 0


class TestStackLimitsAndAlignment:

    def test_align_stack_already_aligned(self, dummy_mapper):
        """Tests that alignment does nothing if already 16-byte aligned."""
        dummy_mapper.mock_rsp = 0x7fffffffe000 # Ends in 0, modulo 16 is 0
        
        dummy_mapper.align_stack(dummy_mapper.memory, 0x0)
        
        assert dummy_mapper.mock_rsp == 0x7fffffffe000

    def test_align_stack_misaligned(self, dummy_mapper):
        """Tests that alignment correctly shifts down to the nearest 16-byte boundary."""
        dummy_mapper.mock_rsp = 0x7fffffffdff8 # Modulo 16 is 8
        
        dummy_mapper.align_stack(dummy_mapper.memory, 0x0)
        
        assert dummy_mapper.mock_rsp == 0x7fffffffdff0

    def test_align_stack_causes_overflow(self, dummy_mapper):
        """Tests if the alignment subtraction pushes the stack out of bounds."""
        dummy_mapper.mock_rsp = 0x1008
        stack_limit = 0x1001 # Set limit slightly higher so alignment forces it below
        
        with pytest.raises(SystemExit) as excinfo:
            dummy_mapper.align_stack(dummy_mapper.memory, stack_limit)
        
        assert excinfo.value.code == 16

    def test_check_stack_limit_overflow(self, dummy_mapper):
        """Tests direct stack overflow exception."""
        with pytest.raises(OverflowError, match="Stack overflow"):
            dummy_mapper.check_stack_limit(0x999, 0x1000)


class TestStaticHelpers:

    def test_is_constant(self):
        assert Segment_Mapper.is_constant(["MY_CONST", "equ", "10"]) is True
        assert Segment_Mapper.is_constant(["#define", "MACRO", "5"]) is True
        assert Segment_Mapper.is_constant(["mov", "rax", "1"]) is False

    def test_valid_size_specifier(self):
        assert Segment_Mapper.valid_size_specifier("resb", "bss", 1) is True
        assert Segment_Mapper.valid_size_specifier("db", "bss", 1) is False
        assert Segment_Mapper.valid_size_specifier("dd", "data", 1) is True
        assert Segment_Mapper.valid_size_specifier("resd", "rodata", 1) is False

    def test_valid_variable_name(self):
        assert Segment_Mapper.valid_variable_name("valid_var") is True
        assert Segment_Mapper.valid_variable_name("_valid2") is True
        assert Segment_Mapper.valid_variable_name("2invalid") is False
        assert Segment_Mapper.valid_variable_name("invalid-name") is False

    def test_write_section_to_memory_string_padding(self, dummy_mapper):
        """Tests string truncation and padding based on specifier size."""
        # Using a 2-byte specifier (dw) but passing a 5-char string
        Segment_Mapper.write_section_to_memory(
            memory=dummy_mapper.memory,
            times=1,
            specifier=2,
            addresses=[0x600000],
            current_rip=0x600000,
            value="Hello"
        )
        
        # Should be truncated to "He" (2 bytes)
        dummy_mapper.memory.write_bytes.assert_called_with(0x600000, b'He', 2)

        # Using an 8-byte specifier (dq) but passing a 3-char string
        Segment_Mapper.write_section_to_memory(
            memory=dummy_mapper.memory,
            times=1,
            specifier=8,
            addresses=[0x600000],
            current_rip=0x600000,
            value="Hi"
        )
        
        # Should be padded with 6 null bytes
        expected_bytes = b'Hi\x00\x00\x00\x00\x00\x00'
        dummy_mapper.memory.write_bytes.assert_called_with(0x600000, expected_bytes, 8)