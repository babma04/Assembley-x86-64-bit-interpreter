"""
Shared setup for tests/bridge/.

Puts bridges/ on sys.path so `from register_manager import ...` and
`from data_memory import ...` work the same way data_memory.py itself
expects (it does a flat `from register_manager import Registers_Interface`,
not a package-relative import).

Finds the project root by walking upward looking for a `bridges/` directory,
rather than assuming a fixed number of parent directories from this file.
That assumption already broke once (when these tests moved from tests/ to
tests/bridge/) and would break again the next time anything moves --
walking up removes that whole class of bug.
"""
import os
import sys


def _find_project_root(start_dir: str) -> str:
    current = start_dir
    while True:
        if os.path.isdir(os.path.join(current, "bridges")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise RuntimeError(
                f"Could not find a 'bridges' directory above {start_dir} -- "
                "is this test file still somewhere inside the project tree?"
            )
        current = parent


PROJECT_ROOT = _find_project_root(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, "_src/")
CACHE_DIR = os.path.join(PROJECT_ROOT, "program_cache")
BRIDGES_DIR = os.path.join(PROJECT_ROOT, "bridges")
if BRIDGES_DIR not in sys.path:
    sys.path.insert(0, BRIDGES_DIR)

LIBREG_PATH = os.path.join(PROJECT_ROOT, "lib", "libreg.so")
LIBMMU_PATH = os.path.join(PROJECT_ROOT, "lib", "libmmu.so")
LIBS_PRESENT = os.path.exists(LIBREG_PATH) and os.path.exists(LIBMMU_PATH)