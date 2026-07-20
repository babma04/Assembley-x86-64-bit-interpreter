# -----------------------
# SUPPORTED INSTRUCTIONS
# -----------------------
VALID_START: str = "_start"

INSTRUCTIONS: dict[str, dict[str, int]] = {
                'cpu': {
                    'syscall': 0,
                    'call': 1,
                    'ret': 0
                },
                'data_path': {
                    'lea': 2, 'mov': 2, 'jmp': 1, 'jb': 1, 'jl': 1, 'ja': 1,
                    'jg': 1, 'je': 1, 'jne': 1, 'jz': 1, 'js': 1, 'jc': 1, 'jo': 1
                },
                'alu': {
                    'cmp': 2, 'add': 2, 'adc': 2, 'sub': 2, 'sbb': 2, 'inc': 1,
                    'dec': 1, 'and': 2, 'or': 2, 'xor': 2, 'not': 1, 'neg': 1, 'xchg': 2
                }, 
                'fpu': {}
            }

# -------------------------------------
# Control Unit Helpers
# -------------------------------------

# -----------------
# keywords mapping
# -----------------

MASKS_DIRECTIVES = {
    'byte': 0xFF, 'word': 0xFFFF, 'dword': 0xFFFFFFFF, 'qword': 0xFFFFFFFFFFFFFFFF
}

# ----------------------------------------
# Patterns for operand type determination
# ----------------------------------------

COMPONENTS_ADDRESSING_PATTERN = r'(0x[\da-fA-F]+|[a-zA-Z_][a-zA-Z0-9_]*|\d+)'
GENERAL_PURPOSE_REGISTERS_PATTERN = r'([er]?[abcd]x|[er]?[sb]p|[er]?[sd]i|[er]?ip|r[89][bdlw]?|r1[0-5][bdlw]?|[abcd][hl])'
FPU_REGISTERS_PATTERN = r'(ymm[0-9]|xmm[0-9]|ymm1[0-5]|xmm1[0-5])'
NUMBER_REPRESENTATION_PATTERN = r'(0x[\da-fA-F]+|\d[\da-fA-F]*h|0b[01]+|[01]+b|0d\d+|[-+]?\d+d|[0-7]+[oq]|[-+]?\d+)'
WORD_OR_CHARACTERS_PATTERN = r'(\".*?\"|\'.*?\')'
IMMEDIATE_VALUE_PATTERN = fr'({NUMBER_REPRESENTATION_PATTERN}|{WORD_OR_CHARACTERS_PATTERN})'
REGISTER_PATTERN = fr'{GENERAL_PURPOSE_REGISTERS_PATTERN}|{FPU_REGISTERS_PATTERN}'
CONSTANTS_AND_LABELS_PATTERN = r'\b[a-zA-Z_]\w*\b'
DIRECT_AND_BASE_ADDRESSING_PATTERN = fr'^\[(?:\s*){COMPONENTS_ADDRESSING_PATTERN}(?:\s)*([\+\-](?:\s)*{COMPONENTS_ADDRESSING_PATTERN})*(?:\s)*\]$'
INDEXED_ADDRESSING_PATTERN = fr'^\[(?:\s*){COMPONENTS_ADDRESSING_PATTERN}(?:\s)*([\+\-\*](?:\s)*{COMPONENTS_ADDRESSING_PATTERN})*(?:\s)*\]$'
MEMORY_ADDRESSING_PATTERN = fr'^{INDEXED_ADDRESSING_PATTERN}|{DIRECT_AND_BASE_ADDRESSING_PATTERN}$'
OPERAND_PATTERN = fr'{MEMORY_ADDRESSING_PATTERN}|{REGISTER_PATTERN}|{IMMEDIATE_VALUE_PATTERN}{CONSTANTS_AND_LABELS_PATTERN}'

# -------------------------------------------//------------------------------------------- 

# ------------------------------------
# Segment Mapper Helpers
# ------------------------------------

# Directives for size identification and memory allocation verification
SIZE_DIRECTIVES = {
    'db': (1, True), 'dw': (2, True), 'dd': (4, True), 'dq': (8, True),
    'resb': (1, False), 'resw': (2, False), 'resd': (4, False), 'resq': (8, False)
}

# Architecture Constants for sections start and memory allocation
TEXT_BASE = 0x400000
RODATA_BASE = 0x500000
DATA_BASE = 0x600000
BSS_BASE = 0x700000
STACK_START = 0x7fffffffe000

# -----------------------------
# Pattern-Matching Expressions
# -----------------------------

TOKENS_PATTERN = r"""(?x)
    ".*?"|'.*?'|                  # Strings
    \[.*?\]|                      # Memory access
    \(.*?\)|                      # Parenthesized expressions
    0x[\da-fA-F]+|                # Hex Prefix
    \d+[\da-fA-F]*[hH]|           # Hex Suffix
    [01]+[bB]|                    # Binary
    0b[01]+|                      # Binary
    [a-zA-Z_]\w*|                 # Instructions / Registers / Labels
    [-+]?\d+                      # Signed Decimals
"""

ELEMENTS_TO_SKIP = r'^[,\s]+$'  # Commas and whitespace to skip during parsing