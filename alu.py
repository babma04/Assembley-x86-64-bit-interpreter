import sys
from control_unit import Control_Unit

class ALU:
    """
    
    """
    def __init__(self, instruction, operand1, operand2, flags):
        self.instruction = instruction
        self.op1 = operand1
        self.op2 = operand2
        self.halted = False
        self.flags = flags

        

        self.valid_instructions = {
            'add': 2,
            'adc': 2,
            'sub': 2,
            'sbb': 2,
            'inc': 1,
            'dec': 1,
            'and': 2,
            'or': 2,
            'xor': 2,
            'not': 1,
            'neg': 1,
            'xchg': 2
            #to be complited
        }

        self.instruction = None
    
    def set_flags(self, dest, result):
        """
        Sets the flags in funtion of the operations result and op1.
        Sets all flags, so any instruction that does not affect a given flag should save its inicial value and re-attribute it.
        """
        dest_size = CPU.get_size(dest)
        max_unsigned_val = 2**dest_size -1
        max_signed_val = 2**(dest_size-1) - 1
        min_val = -2**(dest_size-1)

        # Carry flag detection
        if result > max_unsigned_val:
            self.flags['C'] = 1
            # wrap around the result to fit in the destination size
            result = result % (2**dest_size)
        else:
            self.flags['C'] = 0

        # Zero result detection
        if result == 0:
            self.flags['Z'] = 1
        else:
            self.flags['Z'] = 0

        # Sign change detection
        if result * dest < 0:
            self.flags['S'] = 1
        else:
            self.flags['S'] = 0
            
        # Overflow detection (signed)
        if result > max_signed_val or result < min_val:
            self.flags['O'] = 1
            # Wrap result to simulate 
            mask = 2**dest_size - 1
            result =  result & mask
        else:
            self.flags['O'] = 0
        return result

    def attribute_instruction(self):
        if self.instruction == "add":
            self.add(self.op1, self.op2)
        elif self.instruction == "adc":
            self.adc(self.op1, self.op2)
        elif self.instruction == "sub":
            self.sub(self.op1, self.op2)
        elif self.instruction == "sbb":
            self.sbb(self.op1, self.op2)
        elif self.instruction == "inc":
            self.inc(self.op2)
        elif self.instruction == "dec":
            self.dec(self.op1)
        elif self.instruction == "and":
            self.and_op(self.op1, self.op2)
        elif self.instruction == "or":
            self.or_op(self.op1, self.op2)
        elif self.instruction == "xor":
            self.xor_op(self.op1, self.op2)
        elif self.instruction == "not":
            self.not_op(self.op1)
        elif self.instruction == "neg":
            self.neg(self.op1)
        elif self.instruction == "xchg":
            self.xchg(self.op1, self.op2)
        

    def add(self):
        """
        Add the value from src to dest and store the result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ###rever flags
        if self.op2 is None:
            print("INVALID OPERAND COUNT FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        elif CPU.is_immediate(self.op1) or CPU.is_constant(self.op1):
            print("INVALID DESTINATION OPERAND TYPE FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        else:
            operand1 = CPU.select_operand(self.op1)
            operand2 = CPU.select_operand(self.op2)
            result = operand1 + operand2
            result = self.set_flags(operand1, result)
            self.op1(result)
    

    def adc(self):
        """
        Add the value from src to dest with carry and store the result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        if self.op2 is None:
            print("INVALID OPERAND COUNT FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        elif CPU.is_immediate(self.op1) or CPU.is_constant(self.op1):
            print("INVALID DESTINATION OPERAND TYPE FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        else:
            operand1 = CPU.select_operand(self.op1)
            operand2 = CPU.select_operand(self.op2)
        
            result = operand1 + operand2 + int(self.flags['C'])
            result = self.set_flags(operand1, result)
            self.op1(result)
    

    def sub(self):
        """
        Subtract the value from src from dest and store the result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        if self.op2 is None:
            print("INVALID OPERAND COUNT FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        elif CPU.is_immediate(self.op1) or CPU.is_constant(self.op1):
            print("INVALID DESTINATION OPERAND TYPE FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        else:
            operand1 = CPU.select_operand(self.op1)
            operand2 = CPU.select_operand(self.op2)
            result = operand1 - operand2
            result = self.set_flags(operand1, result)
            self.op1(result)
    
    # def sub_cmp(self):
    #     """
    #     Subtract the value from src from dest without store the result in dest.
    #     Used in comparisons and to verify jump instructions.
    #     :param dest: The destination register or memory location.
    #     :param src: The source register, memory location, or immediate value.
    #     """
    #     ### rever flags
    #     CPU.get_operands()
    #     result = self.op1_get + self.op2_get + int(self.flags['C'])
    #     result = CPU.set_flags(self.op1_get, result)
    
    def sbb(self):
        """
        Subtract the value from src from dest with borrow and store the result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        if self.op2 is None:
            print("INVALID OPERAND COUNT FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        elif CPU.is_immediate(self.op1) or CPU.is_constant(self.op1):
            print("INVALID DESTINATION OPERAND TYPE FOR ADD INSTRUCTION\nHalting execution.")
            sys.exit(-1, "Program forced exit on SemanticError.")
        else:
            operand1 = CPU.select_operand(self.op1)
            operand2 = CPU.select_operand(self.op2)
        
            result = operand1 - operand2 - int(self.flags['C'])
            result = self.set_flags(operand1, result)
            self.op1(result)
            
    
    # def mul(self):
    #     #todo
    
    # def imul(self):
    #     #todo

    # def div(self):
    #     #todo
    
    # def idiv(self):
    #     #todo
    
    def shl(self):
        CPU.get_operands()
        result = self.op1_get << self.op2_get 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
    
    def shr(self):
        CPU.get_operands()
        result = self.op1_get >> self.op2_get 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)

    # def scl(self):
    #     #todo
    # def scr(self):
    #     #todo
    # def rol(self):
    #     #todo
    # def ror(self):
    #     #todo
    # def rcl(self):
    #     #todo
    # def rcr(self):
    #     #todo
        
        
    def inc(self):
        """
        Increment the value of dest by 1.
        :param dest: The destination register or memory location.
        """
        ### rever flags
        CPU.get_operands()
        result = self.op1_get + 1
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
        

    def dec(self):
        """
        Decrement the value of dest by 1.
        :param dest: The destination register or memory location.
        """
        ### rever flags
        CPU.get_operands()
        result = self.op1_get -1 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
    
    def and_op(self):
        """
        Perform bitwise AND between dest and src, store result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        CPU.get_operands()
        result = self.op1_get & self.op2_get 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
    

    def or_op(self):
        """
        Perform bitwise OR between dest and src, store result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        CPU.get_operands()
        result = self.op1_get | self.op2_get
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
    

    def xor_op(self):
        """
        Perform bitwise XOR between dest and src, store result in dest.
        :param dest: The destination register or memory location.
        :param src: The source register, memory location, or immediate value.
        """
        ### rever flags
        CPU.get_operands()
        result = self.op1_get ^ self.op2_get 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)

    def not_op(self, dest):
        """
        Perform bitwise NOT on dest, store result in dest.
        :param dest: The destination register or memory location.
        """
        dest_get, dest_set = self.select_operand(dest)
        result = ~int(dest_get())
        dest_set(result)
    

    def neg(self):
        """
        Negate the value of dest (two's complement), store result in dest.
        :param dest: The destination register or memory location.
        """
        ### rever flags
        CPU.get_operands()
        result = -self.op1_get 
        result = CPU.set_flags(self.op1_get, result)
        self.op1_set(result)
    

    def xchg(self):
        """
        Exchange the values of op1 and op2.
        !!!Does not yet support op1 to be a memory location!!!
        :param op1: The first register or memory location.
        :param op2: The second register or memory location.
        """
        ### rever flags
        CPU.get_operands()
        temp = self.op1_get 
        self.op1_set(self.op2_get)
        self.op2_set(temp)

    