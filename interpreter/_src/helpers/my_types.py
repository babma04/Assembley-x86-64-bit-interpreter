from typing import TYPE_CHECKING, TypeAlias, Dict, List, Union

if TYPE_CHECKING:
    # Only needed for static type checking -- importing these for real at
    # module load time creates a circular import, since data_path.py (and
    # friends) import LabelMap/etc. from this module.
    from interpreter._src.FUs.alu import ALU
    from interpreter._src.FUs.data_path import Data_Path
    from interpreter._src.FUs.fpu import FPU

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

FU: TypeAlias = Union["ALU", "FPU", "Data_Path"]