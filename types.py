from typing import TypeAlias, Dict, List, Union

# Keep it simple and clean
Address: TypeAlias = int
WordSize: TypeAlias = int

# Section Info Aliases
# .data and .rodata: Mapping a name to its address and size
DataSectionInfo: TypeAlias = Dict[str, Dict[str, List[Address] | int]]

# .bss: Mapping a name to its list of addresses and size
BssSectionInfo: TypeAlias = Dict[str, Dict[str, List[Address] | int]]

# .text labels: Mapping a name to its index 
LabelMap: TypeAlias = Dict[str, int]

# Constants: Mapping name to its value and index
ConstantMap: TypeAlias = Dict[str, Dict[str, int | str]]

# For getting info on the valid_instructions.json file
InstructionSet: TypeAlias = Dict[str, Union[List[str], Dict[str, int]]]