class ALU:
    """
    
    """
    def __init__(self):
        self.instruction: str = ""
        self.op1_value: bytes = b'0'
        self.op1_address: int | None = None
        self.op1_type: str | None = None
        self.op1_size: int = 0
        self.op2_value: bytes = b'0'
        self.op2_address: int | None = None
        self.op2_type: str | None = None
        self.op2_size: int = 0
        self.flags: dict[str, int] = {}
    
    def load_values(self, instruction: str, op1_value: bytes, op1_address: int | None, op1_type: str | None, op1_size: int, op2_value: bytes, op2_address: int | None, op2_type: str | None, op2_size: int, flags: dict[str, int]) -> None:
        """
        Initializes the instances of the class.
        
        :param instruction: Instruction to do
        :type instrution: str
        :param op1_value: Value of the source operand
        :type op1_value: bytes
        :param op1_address: Address of the source operand if any
        :type op1_address: int | None
        :param op1_type: Operand type of the source operand if it exists
        :type op1_type: str | None
        :param op1_size: Number of bytes the source operand takes
        :type op1_size: int
        :param op2_value: Value of the destination operand
        :type op2_value: bytes
        :param op2_address: Address of the destination operand if any
        :type op2_address: int | None
        :param op2_type: Operand type of the destination operand if it exists
        :type op2_type: str | None
        :param op2_size: Number of bytes the destination operand takes
        :type op2_size: int
        :param flags: Current state of the program flags
        :type flags: dict[str, int]
        """
        self.instruction = instruction
        self. op1_value = op1_value
        self.op1_address = op1_address
        self.op1_type = op1_type
        self.op1_size = op1_size
        self.op2_value = op2_value
        self.op2_address = op2_address
        self.op2_type = op2_type
        self.op2_size = op2_size
        self.flags = flags
    