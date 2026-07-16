import unittest
from unittest.mock import patch, MagicMock
import sys

from parsing.segment_mapper import Segment_Mapper

class TestMemorySegments(unittest.TestCase):

    @patch('parsing.segment_mapper.Storage')
    def setUp(self, MockStorage):
        # Map to the JSON cache expectations
        MockStorage.read_valid_start.return_value = "_start"
        MockStorage.convert_to_json.return_value = "dummy.json"
        MockStorage.load_file_lines.return_value = ["global _start", "_start:"]
        
        self.mapper = Segment_Mapper("dummy.asm")
        self.mapper.memory = MagicMock()
        
        self.mapper.data_segment = {}
        self.mapper.bss_segment = {}

    # -----------------------------------------
    # Properties: .data Allocations
    # -----------------------------------------
    def test_load_single_data_property(self):
        current_rip = 0x600000
        line = ["my_var", "dd", "255"]
        
        new_rip = self.mapper.load_single_data(line, "data", current_rip)
        
        self.assertEqual(new_rip, 0x600004)
        self.assertIn("my_var", self.mapper.data_segment)
        self.assertEqual(self.mapper.data_segment["my_var"]["size"], 4)
        self.assertEqual(self.mapper.data_segment["my_var"]["addresses"], [0x600000, 0x600001, 0x600002, 0x600003])
        
        expected_bytes = (255).to_bytes(4, "little")
        self.mapper.memory.write_bytes.assert_called_with(0x600000, expected_bytes, 4)

    def test_load_timed_data_property(self):
        current_rip = 0x600000
        line = ["buffer", "times", "10", "db", "0"]
        
        new_rip = self.mapper.load_timed_data(line, "data", current_rip)
        
        self.assertEqual(new_rip, 0x60000A)
        self.assertEqual(self.mapper.data_segment["buffer"]["size"], 10)
        self.assertEqual(len(self.mapper.data_segment["buffer"]["addresses"]), 10)

    # -----------------------------------------
    # Properties: .bss Allocations
    # -----------------------------------------
    def test_load_bss_property(self):
        self.mapper.memory_list = [
            ["section", ".bss"],
            ["uninit_arr", "resw", "5"], 
            ["section", ".text"]
        ]
        
        new_rip = self.mapper.load_bss(current_rip=0x700000, index=0)
        
        self.assertEqual(new_rip, 0x70000A)
        self.assertEqual(self.mapper.bss_segment["uninit_arr"]["size"], 10)
        
        expected_bytes = (0).to_bytes(2, "little")
        self.mapper.memory.write_bytes.assert_any_call(0x700000, expected_bytes, 2)

    # -----------------------------------------
    # Edge Cases: Formatting & Exits
    # -----------------------------------------
    @patch('sys.stdout', new_callable=MagicMock)
    def test_data_validation_invalid_size_exit(self, mock_stdout):
        line = ["my_var", "resb", "10"]
        self.assertFalse(self.mapper.data_format_validation(line, index=1, section="data"))

    @patch('sys.stdout', new_callable=MagicMock)
    def test_data_validation_duplicate_label_exit(self, mock_stdout):
        self.mapper.rodata_segment["sys_const"] = {'size': 4, 'addresses': []}
        line = ["sys_const", "dd", "10"]
        self.assertFalse(self.mapper.data_format_validation(line, index=2, section="data"))

    def test_write_section_to_memory_string_fallback(self):
        self.mapper.write_section_to_memory(
            memory=self.mapper.memory, 
            times=1, 
            specifier=2, 
            addresses=[0x600000, 0x600001], 
            current_rip=0x600000, 
            value="AB"
        )
        self.mapper.memory.write_bytes.assert_called_with(0x600000, b'AB', 2)

if __name__ == '__main__':
    unittest.main()