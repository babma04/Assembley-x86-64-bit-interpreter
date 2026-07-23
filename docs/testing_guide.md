# Testing & Debugging Strategy

This document outlines the testing architecture for the Assembly x86-64 Interpreter. Because the project spans high-level Python (parsing, control flow) and low-level C (hardware state, execution), the testing strategy is divided into isolated layers that converge into full system integration tests.

---

## 1. Test Architecture Overview

The `tests/` directory is structured to isolate failures to their specific domain:

* **C Execution Tests (`tests/execution_tests/`):** Pure C unit tests verifying memory allocation (MMU), register manipulation, bit-masking, and raw operation execution (ALU) independent of Python.
* **Bridge Tests (`tests/bridge/`):** Python tests verifying the `ctypes` integration, ensuring data buffers, pointers, and types are correctly passed across the language boundary.
* **Parser Tests (`tests/parser/`):** Python tests validating Phase 1 (Mapping) and instruction decoding logic, ensuring regex and token matchers correctly handle valid and invalid syntax.
* **Integration Tests (`tests/test_cpu.py`):** End-to-end CPU tests that run full `.asm` files from `tests/asm/` and verify the final hardware state.

---

## 2. Running the Tests

### 2.1 C-Level Unit Tests
The C tests are compiled and executed via the root `Makefile`. These tests must pass before you can trust the Python bridge.

```bash
# Build the shared libraries and the test binaries, then run the tests
make test

# To clean test binaries and build artifacts
make clean
```

### 2.2 Python & Integration Tests

The Python test suites (Bridge, Parser, Storage, and CPU Integration) use pytest. They automatically detect the `.so` files in `interpreter/_src/lib/`.

```bash
# Run the entire Python test suite
pytest -v

# Run specific test suites
pytest tests/bridge/ -v
pytest tests/parser/ -v
pytest tests/test_cpu.py -v
# etc

# Run tests and stop on the first failure
pytest -x -v
```

Note: If the C shared libraries (`libreg.so`, `libmmu.so`, `liboperations.so`) are not built, Python tests relying on them will be skipped or fail. Always run `make` before `pytest`.

---

## 3. Developer Workflow: Adding Features

When contributing to the interpreter, tests must be added at the layer where the logic lives.

### Scenario: Adding a New Assembly Instruction (e.g., shl)

* **Step 1**: C-Level Implementation & Testing

1. Implement the operation logic and flag calculations in `interpreter/_src/execution/src/operations.c`.
2. Write a unit test in `tests/execution_tests/` to verify `shl` computes the correct result and sets the correct flags (`ZF`, `CF`, etc.).
3. Run `make test` to verify the C logic is sound.

* **Step 2**: Python-Level Implementation & Testing

1. Update `interpreter/_src/parsing/pattern_matching_helpers.py` so the parser recognizes `shl` and its allowed operands.
2. Extend the relevant Functional Unit (e.g., `alu.py`) to handle the dispatch.
3. Write a test in `tests/parser/` to ensure malformed `shl` commands are rejected (e.g., `INVALID_INSTRUCTION_SYNTAX`).

* **Step 3**: End-to-End Integration Testing

1. Create a minimal `.asm` file in `tests/asm/` that uses the new `shl` instruction in a few different contexts (e.g., register/register, register/immediate).
2. Add a test case in `tests/test_cpu.py` that loads this `.asm` file, runs the interpreter, and asserts that the final register state matches the expected mathematical outcome.
3. Run `pytest tests/test_cpu.py -v` to confirm the full pipeline works.
