import unittest
from unittest.mock import patch, MagicMock
import sys

from parsing.segment_mapper import Segment_Mapper

class TestStackInitialization(unittest.TestCase):

    # Patching Storage exactly where it is used in segment_mapper.py
    @patch('parsing.segment_mapper.Storage')
    def setUp(self, MockStorage):
        # 1. Update the valid start string based on program_cache/valid_instructions.json
        MockStorage.read_valid_start.return_value = "_start"
        MockStorage.convert_to_json.return_value = "dummy.json"
        
        # 2. Update the dummy assembly to use _start
        MockStorage.load_file_lines.return_value = ["global _start", "_start:"]
        
        # Instantiate mapper
        self.mapper = Segment_Mapper("dummy.asm")
        
        # Fresh mocks for memory and registers for each test
        self.mapper.memory = MagicMock()
        self.mapper.registers = MagicMock()

    # -----------------------------------------
    # Properties: Argument Pushing
    # -----------------------------------------
    def test_push_arguments_byte_formatting(self):
        self.mapper.registers.read_reg.side_effect = [0x1000, 0x0FF0] 
        argv = ["test", "arg"]
        
        addresses = self.mapper.push_arguments(argv)
        
        expected_calls = [
            unittest.mock.call(b'\x00gra'),
            unittest.mock.call(b'\x00tset'),
            unittest.mock.call(b'\x00')
        ]
        self.mapper.memory.push.assert_has_calls(expected_calls)
        self.assertEqual(len(addresses), 2)

    # -----------------------------------------
    # Properties: Full Initialization Flow
    # -----------------------------------------
    def test_initialize_stack_full_flow(self):
        self.mapper.registers.read_reg.return_value = 0x7fffffffe000
        
        self.mapper.initialize_stack(
            argvcount=2, 
            argv=["./prog", "input.txt"], 
            memory=self.mapper.memory, 
            stack_limit=0x7fff00000000,
            stack_start=0x7fffffffe000
        )
        
        self.mapper.registers.write_reg.assert_any_call("rsp", 0x7fffffffe000, False)
        self.mapper.memory.push.assert_any_call((0).to_bytes(8, "little"))
        self.mapper.memory.push.assert_any_call((2).to_bytes(8, "little"))

    # -----------------------------------------
    # Edge Cases: Alignment & Overflows
    # -----------------------------------------
    def test_align_stack_unaligned_edge_case(self):
        self.mapper.registers.read_reg.return_value = 0x1008
        self.mapper.align_stack(self.mapper.memory, stack_limit=0x1000)
        self.mapper.registers.write_reg.assert_called_with("rsp", 0x1000, False)

    def test_align_stack_causes_overflow_edge_case(self):
        self.mapper.registers.read_reg.return_value = 0x1008
        limit = 0x1008 
        
        with self.assertRaises(SystemExit) as cm:
            self.mapper.align_stack(self.mapper.memory, stack_limit=limit)
        
        self.assertEqual(cm.exception.code, 16)

    def test_initialize_stack_empty_argv(self):
        self.mapper.registers.read_reg.return_value = 0x2000
        self.mapper.initialize_stack(0, None, self.mapper.memory, 0x1000)
        self.mapper.memory.push.assert_any_call((0).to_bytes(8, "little"))

if __name__ == '__main__':
    unittest.main()