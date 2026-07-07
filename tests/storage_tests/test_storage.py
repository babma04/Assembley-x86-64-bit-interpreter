"""
Test suite for storage.Storage

Run with:
    pytest test_storage.py -v

Design notes
------------
Storage.PROJECT_DIR is computed once, at import time, from the location of
storage.py on disk. Several methods (save_file, save_file_dictionary,
load_file, load_file_lines) always read/write relative to PROJECT_DIR,
no matter what the process's current working directory is.

Three other methods -- initialize_instructions, read_valid_start, and
read_valid_instructions -- work with file_name directly, relative to the
current working directory (NOT PROJECT_DIR). This is intentional: these
are "execution start" helper methods that validate/initialize the
settings a running program needs from wherever it is launched, as
opposed to the general-purpose storage helpers above, which always
manage files alongside storage.py itself. The tests below document current behavior.

To keep tests isolated and not pollute the real project folder, we
monkeypatch `storage.PROJECT_DIR` to a pytest tmp_path for every test,
and we `chdir` into that same tmp_path so the cwd-relative methods are
also sandboxed.

All errors on this file are ignorable as they are only unverified typing for the strict typing mode of python 3.11 
"""
import json
import os
import sys

import pytest

from helpers import storage
from helpers.storage import Storage


@pytest.fixture(autouse=True)
def isolate_filesystem(tmp_path, monkeypatch):
    """
    Run every test inside an isolated temporary directory, and point
    Storage.PROJECT_DIR at that same directory, so tests never touch
    the real project folder and never interfere with each other.
    """
    monkeypatch.setattr(storage, "PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------

class TestSaveFile:
    def test_writes_list_as_json(self, tmp_path):
        Storage.save_file("data.json", ["line1", "line2", "line3"])

        written = json.loads((tmp_path / "data.json").read_text())
        assert written == ["line1", "line2", "line3"]

    def test_writes_list_of_lists_as_json(self, tmp_path):
        payload = [["mov", "eax", "1"], ["add", "eax", "ebx"]]
        Storage.save_file("instructions.json", payload)

        written = json.loads((tmp_path / "instructions.json").read_text())
        assert written == payload

    def test_overwrites_existing_file(self, tmp_path):
        Storage.save_file("data.json", ["old"])
        Storage.save_file("data.json", ["new"])

        written = json.loads((tmp_path / "data.json").read_text())
        assert written == ["new"]

    def test_raises_syntaxerror_for_non_json_extension(self):
        with pytest.raises(SyntaxError):
            Storage.save_file("data.txt", ["line1"])

    def test_raises_syntaxerror_for_no_extension(self):
        with pytest.raises(SyntaxError):
            Storage.save_file("data", ["line1"])

    def test_file_is_pretty_printed_with_indent(self, tmp_path):
        Storage.save_file("data.json", ["a"])
        raw = (tmp_path / "data.json").read_text()
        # indent=4 means the content is spread across multiple lines
        assert "\n" in raw


# ---------------------------------------------------------------------------
# save_file_dictionary
# ---------------------------------------------------------------------------

class TestSaveFileDictionary:
    def test_creates_file_when_absent(self, tmp_path):
        data = {"valid start": "_start", "alu": {"add": 2}}
        Storage.save_file_dictionary("settings.json", data)

        written = json.loads((tmp_path / "settings.json").read_text())
        assert written == data

    def test_does_not_overwrite_existing_file(self, tmp_path):
        original = {"valid start": "_start", "alu": {}}
        Storage.save_file_dictionary("settings.json", original)

        # Attempt to save different data to the same file name
        Storage.save_file_dictionary("settings.json", {"valid start": "CHANGED"})

        written = json.loads((tmp_path / "settings.json").read_text())
        assert written == original  # unchanged, first write wins

    def test_raises_syntaxerror_for_non_json_extension(self):
        with pytest.raises(SyntaxError):
            Storage.save_file_dictionary("settings.txt", {"a": "b"})


# ---------------------------------------------------------------------------
# load_file
# ---------------------------------------------------------------------------

class TestLoadFile:
    def test_returns_file_contents(self, tmp_path):
        (tmp_path / "notes.txt").write_text("hello world")
        assert Storage.load_file("notes.txt") == "hello world"

    def test_exits_process_when_file_missing(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            Storage.load_file("does_not_exist.txt")

        assert exc_info.value.code == -1
        captured = capsys.readouterr()
        assert "couldn't be opened" in captured.out


# ---------------------------------------------------------------------------
# load_file_lines
# ---------------------------------------------------------------------------

class TestLoadFileLines:
    def test_returns_list_from_json_array(self, tmp_path):
        (tmp_path / "lines.json").write_text(json.dumps(["mov eax, 1", "add eax, ebx"]))
        result = Storage.load_file_lines("lines.json")
        assert result == ["mov eax, 1", "add eax, ebx"]

    def test_raises_filenotfound_when_missing(self):
        # Unlike load_file, load_file_lines has no try/except and lets
        # FileNotFoundError propagate.
        with pytest.raises(FileNotFoundError):
            Storage.load_file_lines("missing.json")

    def test_raises_jsondecodeerror_on_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not valid json")
        with pytest.raises(json.JSONDecodeError):
            Storage.load_file_lines("bad.json")


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
        result = json.loads((tmp_path / "program.json").read_text())
        # Note: the source string ends with "\n", so split("\n") produces
        # a trailing empty string as the final "line", which survives
        # through to the output (it has no ";" so it isn't skipped).
        assert result == [
            "mov eax, 1",
            "add eax, ebx",
            "sub eax, 1",
            "",
        ]

    def test_comment_only_line_is_not_actually_skipped(self, tmp_path):
        # Known quirk: the skip check is `if line == "":`, tested against
        # the text BEFORE stripping. A comment-only line like "  ; note"
        # becomes "  " (not "") after splitting on ";", so the emptiness
        # check does not trigger and an empty string is appended instead
        # of the line being dropped entirely.
        (tmp_path / "program.asm").write_text(
            "nop\n"
            "  ; a comment-only line\n"
            "hlt\n"
        )
        Storage.convert_to_json("program.asm")
        result = json.loads((tmp_path / "program.json").read_text())
        assert result == ["nop", "", "hlt", ""]

    def test_comment_only_line_with_no_leading_whitespace_is_skipped(self, tmp_path):
        # Only when there is NOTHING before the ";" (not even a space)
        # does the equality check `line == ""` succeed and the line get
        # dropped.
        (tmp_path / "program.asm").write_text(
            "nop\n"
            ";pure comment, no leading space\n"
            "hlt\n"
        )
        Storage.convert_to_json("program.asm")
        result = json.loads((tmp_path / "program.json").read_text())
        assert result == ["nop", "hlt", ""]

    def test_keeps_lines_without_semicolons_untouched_but_stripped(self, tmp_path):
        (tmp_path / "program.asm").write_text("  jmp start  \nnop\n")
        Storage.convert_to_json("program.asm")

        result = json.loads((tmp_path / "program.json").read_text())
        assert result == ["jmp start", "nop", ""]
        # Note: the trailing "" comes from the trailing newline in the
        # source file producing an empty final line after split("\n").

    def test_uses_first_dot_segment_for_new_name(self, tmp_path):
        # split(".")[0] means any name with multiple dots is truncated
        # at the first dot -- documenting current (possibly surprising)
        # behavior.
        (tmp_path / "my.program.asm").write_text("nop\n")
        new_name = Storage.convert_to_json("my.program.asm")
        assert new_name == "my.json"

    def test_exits_when_source_file_missing(self):
        with pytest.raises(SystemExit):
            Storage.convert_to_json("missing.asm")


# ---------------------------------------------------------------------------
# initialize_instructions
# ---------------------------------------------------------------------------

class TestInitializeInstructions:
    def test_returns_expected_file_name(self):
        assert Storage.initialize_instructions() == "valid_instructions.json"

    def test_creates_file_in_project_dir_when_absent_from_cwd(self, tmp_path):
        # By design, the "does it already exist?" check looks at the
        # current working directory (os.path.isfile(file_name)) -- this
        # is the execution-start check. The actual write goes through
        # save_file_dictionary, which writes to PROJECT_DIR. In this
        # fixture PROJECT_DIR == cwd == tmp_path, so the two locations
        # coincide and the file appears as expected.
        Storage.initialize_instructions()

        created = tmp_path / "valid_instructions.json"
        assert created.is_file()

        data = json.loads(created.read_text())
        assert data["valid start"] == "_start"
        assert data["data_path"]["mov"] == 2
        assert data["alu"]["xor"] == 2
        assert data["fpu"] == {}

    def test_does_not_overwrite_if_file_already_present_in_cwd(self, tmp_path):
        # Pre-seed a file with different content at the cwd-relative path.
        preexisting = {"valid start": "CUSTOM"}
        (tmp_path / "valid_instructions.json").write_text(json.dumps(preexisting))

        Storage.initialize_instructions()

        data = json.loads((tmp_path / "valid_instructions.json").read_text())
        assert data == preexisting  # left untouched

    def test_cwd_check_is_independent_of_project_dir(self, tmp_path, monkeypatch):
        # Demonstrates the intentional cwd-vs-PROJECT_DIR split directly:
        # point PROJECT_DIR somewhere else while keeping cwd at tmp_path.
        # The isfile() check still looks at cwd (the execution-start
        # directory), but the write (via save_file_dictionary) goes to
        # the (different) PROJECT_DIR.
        other_dir = tmp_path / "elsewhere"
        other_dir.mkdir()
        monkeypatch.setattr(storage, "PROJECT_DIR", str(other_dir))

        assert not (tmp_path / "valid_instructions.json").exists()
        Storage.initialize_instructions()

        # Not created in cwd...
        assert not (tmp_path / "valid_instructions.json").exists()
        # ...but created in PROJECT_DIR instead.
        assert (other_dir / "valid_instructions.json").is_file()


# ---------------------------------------------------------------------------
# read_valid_start / read_valid_instructions
# ---------------------------------------------------------------------------

class TestReadValidStart:
    def test_returns_start_value(self, tmp_path):
        (tmp_path / "settings.json").write_text(
            json.dumps({"valid start": "_start", "alu": {"add": 2}})
        )
        assert Storage.read_valid_start("settings.json") == "_start"

    def test_raises_keyerror_if_missing(self, tmp_path):
        (tmp_path / "settings.json").write_text(json.dumps({"alu": {"add": 2}}))
        with pytest.raises(KeyError):
            Storage.read_valid_start("settings.json")

    def test_raises_filenotfound_when_missing(self):
        with pytest.raises(FileNotFoundError):
            Storage.read_valid_start("missing.json")


class TestReadValidInstructions:
    def test_filters_to_dict_valued_entries_only(self, tmp_path):
        settings = {
            "valid start": "_start",  # a plain string, should be filtered out
            "data_path": {"mov": 2, "jmp": 1},
            "alu": {"add": 2, "sub": 2},
            "fpu": {},
        }
        (tmp_path / "settings.json").write_text(json.dumps(settings))

        result = Storage.read_valid_instructions("settings.json")

        assert "valid start" not in result
        assert result["data_path"] == {"mov": 2, "jmp": 1}
        assert result["alu"] == {"add": 2, "sub": 2}
        assert result["fpu"] == {}

    def test_raises_filenotfound_when_missing(self):
        with pytest.raises(FileNotFoundError):
            Storage.read_valid_instructions("missing.json")


# ---------------------------------------------------------------------------
# End-to-end / integration style test
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_initialize_then_read_round_trip(self, tmp_path):
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
        assert lines == ["mov eax, 1", "add eax, ebx", ""]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))