import ctypes
import os

# NEEDS TO RECEIVE INTS NOT BYTES


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
    STACK_DEFAULT: int = 0x7fffffffe000

    def __init__(self, memory_base: int = RODATA_BASE, stack_start: int = STACK_DEFAULT):
        self.start: int= memory_base
        self.stack_start: int= stack_start     
        self.stack_pointer: int= stack_start

        # Loads C memory management lib as an instance of the class
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        _lib_path = os.path.join(_base_dir, "libmmu.so")
        self.lib = ctypes.CDLL(_lib_path)

        # Setup C types as usable types in python
        self.lib.write_mem.argtypes = [ctypes.c_uint64, ctypes.c_uint8]
        self.lib.read_mem.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.read_mem.restype = ctypes.c_int

    # ------------------------
    # Read and write methods 
    # ------------------------
    def read_bytes(self, addr: int, size: int) -> bytes:
        """
        Reads an integer representation of the desired data with a specific size in a specific address.
        
        :param addr: address to start writting to.
        :type addr: int
        :param size: size of the data to write: [1,2,4,8] bytes
        :type size: int
        :return: byte values at specific addresses
        :rtype: bytes
        """
        return bytes(self._c_read(addr + i) for i in range(size))
    
    def _c_read(self, addr: int) -> int:
        """
        Uses the read_mem funtion from the c script to read the value from memory.
        If the read returns 1 (signal for a misread) a MemoryError is raised.

        :param addr: Virtual address to read from.
        :type addr: int
        :return: the integer at the given memory address
        :rtype: int
        :raises MemoryError: If a misread is detected
        """
        res = ctypes.c_uint8(0)
        # If a misread is signaled raise MemoryError  
        if self.lib.read_mem(addr, ctypes.byref(res)) == 1:  
            raise MemoryError(f"Segmentation Fault at 0x{hex(addr)}")
        # Else return the pointer's value
        return res.value
    

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
        # Verify data correctness 
        if not self.valid_data_length(data, size):
            data = self.get_valid_data(data, size)
        # For each byte in data write it onto sequencial addresses starting at the base address
        for i, b in enumerate(data):
            self._c_write(addr + i, b)
    
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
    
    def _c_write(self, addr: int, value: int) -> None:
        """
        Uses the write_mem funtion from the c script to write the value into memory.
        Value must be 1 byte or will be truncated.

        :param addr: Virtual address to write to.
        :type addr: int
        :param value: 1 byte value to write.
        :type value: int
        """
        self.lib.write_mem(addr, value & 0xFF)

    # -----------------------
    #  STACK OPERATIONS (fixed 8 bytes per entry)
    # -----------------------
    def push(self, value: bytes) -> None:
        """
        Push a full 8-byte (64-bit) value.
        All stack cells are 8 bytes no matter what.
        
        :param value: value to add to the stack
        :type value: bytes
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
        return value
