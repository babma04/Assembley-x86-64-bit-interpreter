class Data_Memory:
    """
    Simulates the full system memory with:
      - byte-addressable memory
      - a downward-growing stack
      - stack cells fixed to 8 bytes each
      \n
    Used by the Segment_Mapper to create the memory for the CPU.
    All memory addresses are relative to the memory base address.
    Provides methods to read and write data of various sizes and to perform stack operations.\n
    All memory is stored in a bytearray for efficiency.
    All stack operations (push/pop) are done with fixed 8-byte entries.
    Allows reading and writing of data in sizes of 1, 2, 4, or 8 bytes.
    All stack operations (push/pop) are done with fixed 8-byte entries.\n
    Author: João Carilho Louro


    :param memory_base: Base address of the memory
    :type memory_base: int
    :param stack_start: Starting address of the stack (default is 0x7fffffffe000)
    :type stack_start: int
    :return: An instance of Data_Memory
    :rtype: Data_Memory
    """

    RODATA_BASE: int = 0x500000

    def __init__(self, memory_base: int, stack_start: int = 0x7fffffffe000):
        self.start: int= memory_base
        # Memory as an array of 8-bit cells
        self.memory: bytearray= bytearray(stack_start-memory_base)
        # Stack configuration
        self.stack_start: int= stack_start     
        self.stack_pointer: int= stack_start 


    # ------------------------
    # Read and write methods 
    # ------------------------
    def read_bytes(self, addr: int, size: int) -> bytes:
        """
        Reads an integer representation of the desired data with a specific size in a specific address/addresses.
        
        :param addr: address to start writting to.
        :type addr: int
        :param size: size of the data to write: [1,2,4,8] bytes
        :type size: int
        :return: byte values at specific addresses
        :rtype: bytes
        """
        addr -= Data_Memory.RODATA_BASE
        return self.memory[addr:addr + size]
    
    # Writing structure:

        # int value: 0x1234
        # int size: 4
        # bytes value: b'\34\12'
        # bytes extended value: b'\34\12\00\00'

        # writing:
        #     @3: b'\00'
        #     @2: b'\00'
        #     @1: b'\12'
        #     @0: b'\34'

    def write_bytes(self, addr: int, size: int, data: bytes) -> None:
        """
        Writes a byte representation of the desired data with a specific size in a specific address/addresses.
        
        :param addr: address to start writting to.
        :type addr: int
        :param size: size of the data to write: [1,2,4,8] bytes
        :type size: int
        :param data: data to write
        :type data: bytes
        """
        if not self.valid_data_length(data, size):
            data = self.get_valid_data(data, size)
        self.memory[addr:addr + size] = data
    
    def valid_data_length(self, data: bytes, size: int) -> bool:
        """
        Verifies if the length of the data is valid for the size attributed to the write call.\n
        Tries to prevent errors in writing when there are not enought elements in the data variable for the number of bytes to write.

        :param data: Byte representatuion of the data to write.
        :type data: bytes
        :param size: Number of bytes to write
        :type size: int
        :return: True if the number of bytes of the data variable matches the size given
        :rtype: bool
        """
        return len(data) == size 
    
    def get_valid_data(self, data: bytes, size: int) -> bytes:
        """
        Returns a copy of data with the correct amount of explicit bytes.\n
        If any bytes are not explicitly writen, writes them as a 0 at the end of the data, for each missing bytes.

        :param data: Byte representatuion of the data to write.
        :type data: bytes
        :param size: Number of bytes to write
        :type size: int
        :return: Full data with all implicite bytes writen out 
        :rtype: bytes
        """
        return data[:size].ljust(size, b'\x00')

    # -----------------------
    #  STACK OPERATIONS (fixed 8 bytes per entry)
    # -----------------------
    def push(self, value: bytes) -> None:
        """
        Push a full 8-byte (64-bit) value.
        All stack cells are 8 bytes no matter what.
        
        :param value: value to add to the stack
        :type value: int
        """
        # stack grows downward
        self.stack_pointer -= 0x8
        self.write_bytes(self.stack_pointer, 8, value)

    def pop(self) ->  bytes:
        """
        Pop a full 8-byte (64-bit) value.
        
        :return: current value at the top of the stack
        :type: bytes
        """
        value = self.read_bytes(self.stack_pointer, 8)
        self.stack_pointer += 0x8
        #TODO return of the object
        return value
