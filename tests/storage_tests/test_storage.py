"""
Test suite for storage.Storage

Run with:
    pytest test_storage.py -v

Design notes
------------
The `Storage` class now strictly separates file locations using `conftest.CACHE_DIR` 
and `conftest.PROJECT_ROOT`. 

- `load_file` and `convert_to_json` source files from `PROJECT_ROOT`.
- All writes, config initializations, and cache reads target `CACHE_DIR`.

To keep tests isolated and avoid polluting the real project folder, we monkeypatch 
both variables to point to an isolated `pytest` temporary directory and its subfolder.
"""
import json
import os
import sys
import pytest

import conftest
from helpers import storage
from helpers.storage import Storage


@pytest.fixture(autouse=True)
def isolate_filesystem(tmp_path, monkeypatch):
    """
    Run every test inside an isolated temporary directory. 
    Patches variables within the storage module namespace to protect 
    the actual local development files.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    monkeypatch.setattr(storage, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(storage, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ---------------------------------------------------------------------------
# clean_cache
# ---------------------------------------------------------------------------

class TestCleanCache:
    def test_removes_all_files_except_valid_instructions(self, tmp_path):
        cache = tmp_path / "cache"
        (cache / "temp1.json").write_text("[]")
        (cache / "temp2.json").write_text("[]")
        (cache / "valid_instructions.json").write_text("{}")
        
        Storage.clean_cache()
        
        assert not (cache / "temp1.json").exists()
        assert not (cache / "temp2.json").exists()
        assert (cache / "valid_instructions.json").exists()


# ---------------------------------------------------------------------------
# update_valid_instructions
# ---------------------------------------------------------------------------

class TestUpdateValidInstructions:
    def test_updates_only_dict_sections(self, tmp_path):
        initial_data = {
            "valid start": "_start",
            "data_path": {"mov": 2},
            "alu": {"add": 2}
        }
        cache_file = tmp_path / "cache" / "valid_instructions.json"
        cache_file.write_text(json.dumps(initial_data))

        new_data = {
            "data_path": {"mov": 3, "push": 1},
            "valid start": "SHOULD_NOT_CHANGE"  # Plain string, should be ignored
        }
        Storage.update_valid_instructions(new_data)

        updated = json.loads(cache_file.read_text())
        assert updated["data_path"] == {"mov": 3, "push": 1}
        assert updated["valid start"] == "_start" 

    def test_raises_filenotfound_when_missing(self):
        with pytest.raises(FileNotFoundError):
            Storage.update_valid_instructions({"alu": {}})


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------

class TestSaveFile:
    def test_writes_list_as_json_to_cache(self, tmp_path):
        Storage.save_file("data.json", ["line1", "line2", "line3"])
        written = json.loads((tmp_path / "cache" / "data.json").read_text())
        assert written == ["line1", "line2", "line3"]

    def test_writes_list_of_lists_as_json(self, tmp_path):
        payload = [["mov", "eax", "1"], ["add", "eax", "ebx"]]
        Storage.save_file("instructions.json", payload)
        written = json.loads((tmp_path / "cache" / "instructions.json").read_text())
        assert written == payload

    def test_overwrites_existing_file(self, tmp_path):
        Storage.save_file("data.json", ["old"])
        Storage.save_file("data.json", ["new"])
        written = json.loads((tmp_path / "cache" / "data.json").read_text())
        assert written == ["new"]

    def test_raises_valueerror_for_non_json_extension(self):
        with pytest.raises(ValueError, match="must have a .json extension"):
            Storage.save_file("data.txt", ["line1"])

    def test_file_is_pretty_printed_with_indent(self, tmp_path):
        Storage.save_file("data.json", ["a"])
        raw = (tmp_path / "cache" / "data.json").read_text()
        assert "\n" in raw


# ---------------------------------------------------------------------------
# save_file_dictionary
# ---------------------------------------------------------------------------

class TestSaveFileDictionary:
    def test_creates_file_when_absent_in_cache(self, tmp_path):
        data = {"valid start": "_start", "alu": {"add": 2}}
        Storage.save_file_dictionary("settings.json", data)
        written = json.loads((tmp_path / "cache" / "settings.json").read_text())
        assert written == data

    def test_does_not_overwrite_existing_file(self, tmp_path):
        original = {"valid start": "_start", "alu": {}}
        Storage.save_file_dictionary("settings.json", original)
        Storage.save_file_dictionary("settings.json", {"valid start": "CHANGED"})
        
        written = json.loads((tmp_path / "cache" / "settings.json").read_text())
        assert written == original 

    def test_raises_valueerror_for_non_json_extension(self):
        with pytest.raises(ValueError):
            Storage.save_file_dictionary("settings.txt", {"a": "b"})


# ---------------------------------------------------------------------------
# load_file / load_file_lines
# ---------------------------------------------------------------------------

class TestLoadFile:
    def test_returns_file_contents_from_project_root(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hello low level world")
        assert Storage.load_file("notes.txt") == "hello low level world"

    def test_exits_process_when_file_missing(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            Storage.load_file("does_not_exist.txt")
        assert exc_info.value.code == -1
        assert "couldn't be opened" in capsys.readouterr().out


class TestLoadFileLines:
    def test_returns_list_from_cached_json_array(self, tmp_path):
        (tmp_path / "cache" / "lines.json").write_text(json.dumps(["mov eax, 1", "add eax, ebx"]))
        assert Storage.load_file_lines("lines.json") == ["mov eax, 1", "add eax, ebx"]

    def test_raises_filenotfound_when_missing(self):
        with pytest.raises(FileNotFoundError):
            Storage.load_file_lines("missing.json")


# ---------------------------------------------------------------------------
# convert_to_json
# ---------------------------------------------------------------------------

class TestConvertToJson:
    def test_strips_comments_and_whitespace(self, tmp_path):
        source = (
            "mov eax, 1 ; load 1 into eax\n"
            "add eax, ebx\n"
            "sub eax, 1 ;done\n"
        )
        (tmp_path / "program.asm").write_text(source)
        new_name = Storage.convert_to_json("program.asm")

        assert new_name == "program.json"
        result = json.loads((tmp_path / "cache" / "program.json").read_text())
        
        # Note: The new implementation fixes the empty string bug
        assert result == [
            "mov eax, 1",
            "add eax, ebx",
            "sub eax, 1"
        ]

    def test_comment_only_line_is_skipped(self, tmp_path):
        # The new implementation fixes the bug where lines like "  ; note" were kept
        (tmp_path / "program.asm").write_text(
            "nop\n"
            "  ; a comment-only line\n"
            "hlt\n"
        )
        Storage.convert_to_json("program.asm")
        result = json.loads((tmp_path / "cache" / "program.json").read_text())
        assert result == ["nop", "hlt"]

    def test_keeps_lines_without_semicolons_untouched_but_stripped(self, tmp_path):
        (tmp_path / "program.asm").write_text("  jmp start  \nnop\n")
        Storage.convert_to_json("program.asm")
        result = json.loads((tmp_path / "cache" / "program.json").read_text())
        assert result == ["jmp start", "nop"]

    def test_preserves_multiple_dot_segments(self, tmp_path):
        # The new implementation uses os.path.splitext, fixing the truncation bug
        (tmp_path / "my.program.asm").write_text("nop\n")
        new_name = Storage.convert_to_json("my.program.asm")
        assert new_name == "my.program.json"

    def test_exits_when_source_file_missing(self):
        with pytest.raises(SystemExit):
            Storage.convert_to_json("missing.asm")


# ---------------------------------------------------------------------------
# initialize_instructions / read_methods
# ---------------------------------------------------------------------------

class TestInitializeInstructions:
    def test_returns_expected_file_name_and_creates_in_cache(self, tmp_path):
        # The split CWD vs PROJECT_DIR behavior was unified to CACHE_DIR
        file_name = Storage.initialize_instructions()
        assert file_name == "valid_instructions.json"

        created = tmp_path / "cache" / "valid_instructions.json"
        assert created.is_file()

        data = json.loads(created.read_text())
        assert data["valid start"] == "_start"
        assert data["data_path"]["mov"] == 2
        assert data["alu"]["xor"] == 2
        assert data["fpu"] == {}

    def test_does_not_overwrite_if_file_already_present_in_cache(self, tmp_path):
        preexisting = {"valid start": "CUSTOM"}
        (tmp_path / "cache" / "valid_instructions.json").write_text(json.dumps(preexisting))

        Storage.initialize_instructions()
        data = json.loads((tmp_path / "cache" / "valid_instructions.json").read_text())
        assert data == preexisting  


class TestReadValidSettings:
    def test_read_valid_start(self, tmp_path):
        (tmp_path / "cache" / "settings.json").write_text(
            json.dumps({"valid start": "_start", "alu": {"add": 2}})
        )
        assert Storage.read_valid_start("settings.json") == "_start"

    def test_read_valid_instructions_filters_to_dicts_only(self, tmp_path):
        settings = {
            "valid start": "_start", 
            "data_path": {"mov": 2, "jmp": 1},
            "alu": {"add": 2, "sub": 2},
            "fpu": {},
        }
        (tmp_path / "cache" / "settings.json").write_text(json.dumps(settings))
        result = Storage.read_valid_instructions("settings.json")

        assert "valid start" not in result
        assert result["data_path"] == {"mov": 2, "jmp": 1}
        assert result["alu"] == {"add": 2, "sub": 2}


# ---------------------------------------------------------------------------
# End-to-end / integration style test
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_initialize_then_read_round_trip(self):
        file_name = Storage.initialize_instructions()
        start = Storage.read_valid_start(file_name)
        instructions = Storage.read_valid_instructions(file_name)

        assert start == "_start"
        assert set(instructions.keys()) == {"data_path", "alu", "fpu"}
        assert instructions["data_path"]["lea"] == 2

    def test_convert_then_load_lines_round_trip(self, tmp_path):
        (tmp_path / "src.asm").write_text("mov eax, 1 ; comment\nadd eax, ebx\n")
        json_name = Storage.convert_to_json("src.asm")
        lines = Storage.load_file_lines(json_name)
        assert lines == ["mov eax, 1", "add eax, ebx"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))