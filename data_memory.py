#import sys


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

    def __init__(self, memory_base: int, stack_start: int = 0x7fffffffe000):
        self.start: int= memory_base
        # Memory as an array of 8-bit cells
        self.memory: bytearray= bytearray(stack_start-memory_base)
        # Stack configuration
        self.stack_start: int= stack_start     
        self.stack_pointer: int= stack_start 


    # ------------------------
    # Read and write methods (flexible byte size entries)
    # ------------------------
    def read_bytes(self, addr: int, size: int) -> bytes:
        """
        Reads an integer representation of the desired data with a specific size in a specific address/addresses.
        
        :param addr: address to start writting to.
        :type addr: int
        :param size: size of the data to write: [1,2,4,8] bytes
        :type size: int
        :param data: data to write
        :type data: int
        :return: byte values at specific addresses
        :type bytes
        """
        return self.memory[addr:addr + size]

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
        self.memory[addr:addr + size] = data
    

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
