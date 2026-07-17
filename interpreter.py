import os
import sys
from parsing.segment_mapper import Segment_Mapper
from parsing.control_unit import Control_Unit
from helpers.storage import Storage


class Interpreter_x86:
    """
    Class to initialize and run the assembly interpreter.\n
    Requires a file path as a command line argument or user input.
    Prompts for command line arguments after validating the file path.\n
    Enables state observation after it stops running.

    Author: João Carilho Louro
    """


    __slots__ = ["loader", "cpu", "memory", "register"]

    def __init__ (self, file_name:str | None, args: list[str] | None, debugging:bool = False):
        """
        Initializes and runs the interpreter.\n
        After running you can get the state of the program.\n
        When finished you need to call clean() to free all the used memory!
        """


        if not file_name:
            file_name = Interpreter_x86.get_file()
        if not args:
            args = Interpreter_x86.get_args()

        Storage.clean_cache()  # Clean cache before starting
        validation_file_name: str = Storage.initialize_instructions()     # Update method to enable more instructions

        self.loader: Segment_Mapper = Segment_Mapper(file_name, len(args) if args else 0, args, validation_file_name)
        self.memory = self.loader.memory
        self.register = self.loader.registers
        self.cpu: Control_Unit = Control_Unit(self.loader, validation_file_name, debugging)
        self.cpu.run()
        # State could be offered here

    def exit(self):
        self.register.clean()
        self.memory.clean()
    

    
    # ------------------
    # Instance Methods
    # ------------------

    # TODO

    # ------------------
    # Static Methods
    # ------------------

    @staticmethod
    def get_file() -> str:
        """
        Get the file path from command line arguments or user input.

        :return: The file path
        :rtype: str
        """
        file_path: str = ""
        if len(sys.argv) != 2 or not Interpreter_x86.valid_file(sys.argv[1]):
            while (file_path == ""):
                    file_path = input("Enter the full path to the assembly file: ")
                    if not Interpreter_x86.valid_file(file_path):
                        file_path = ""
        return file_path if file_path else sys.argv[1]

    @staticmethod
    def valid_file(file_path: str) -> bool:
        """
        Check if the provided file path points to a valid file.

        :param file_path: Path to the file to be checked
        :type file_path: str
        :return: True if the file exists, False otherwise
        :rtype: bool
        """
        if not os.path.isfile(file_path):
            print("File not found. Please try again.\n")
            return False
        return True
    
    @staticmethod
    def get_args() -> list[str] | None:
        """
        Get command line arguments from user input.

        :return: List of command line arguments or None
        :rtype: list[str] | None
        """
        user_input: str = input("Enter command-line arguments separated by spaces (or press Enter for none): ")
        args: list[str] = user_input.split() if user_input.strip() else []
        return args if args else None