import os
import sys
from segment_mapper import Segment_Mapper
from control_unit import Control_Unit
from storage import Storage

def main():
    """
    Main function to initialize and run the assembly simulator.\n
    Requires a file path as a command line argument or user input.
    Prompts for command line arguments after validating the file path.\n
    Author: João Carilho Louro

    :return: None
    :rtype: None
    :requires: segment_mapper.py, control_unit.py, storage.py
    :example: python main.py /path/to/assembly_file.asm
    :note: Ensure the assembly file exists at the specified path.
    """
    validation_file_name: str = Storage.initialize_instructions()     # Update method to enable more instructionss
    
    file = get_file()
    argv: list[str] | None = get_args()

    if argv is None:
        argvcount: int = 0
    else:
        argvcount: int = len(argv)

    loader: Segment_Mapper = Segment_Mapper(file, argvcount, argv, validation_file_name) 
    cpu: Control_Unit = Control_Unit(loader.memory, loader, validation_file_name)           
    cpu.run()                 

def get_file() -> str:
    """
    Get the file path from command line arguments or user input.

    :return: The file path
    :rtype: str
    """
    file_path: str = ""
    if len(sys.argv) != 2 or not valid_file(sys.argv[1]):
        while (file_path == ""):
                file_path = input("Enter the full path to the assembly file: ")
                if not valid_file(file_path):
                    file_path = ""
    return file_path if file_path else sys.argv[1]

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

def get_args() -> list[str] | None:
    """
    Get command line arguments from user input.

    :return: List of command line arguments or None
    :rtype: list[str] | None
    """
    user_input: str = input("Enter command-line arguments separated by spaces (or press Enter for none): ")
    args: list[str] = user_input.split() if user_input.strip() else []
    return args if args else None

if __name__ == "__main__":
    main()