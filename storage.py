import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))  # folder of the current script

class Storage:
    """
    Utility class for file storage operations.\n
    Takes care of all creation, reading and writing operations to files.
    All file creations are done in the project directory and to a JSON file format.
    Contains static methods only.\n
    Author: João Carilho Louro
    """
    
    @staticmethod
    def convert_to_json(file_name :str) -> str:
        """
        Convert any given file to a JSON file.

        :param file_name: The name of the file with extension.
        :type file_name: str
        :return str: The name of the new JSON file and creates a .json file with the same content.
        :requires: file_name includes the extension
        """
        new_file_name :str= file_name.split(".")[0] + ".json"
        
        raw_text :list[str]= Storage.load_file(file_name).split("\n")
        clean_lines :list[str] = []

        for line in raw_text:
            if ";" in line:
                line = line.split(";")[0]
                if line == "":
                    continue
            clean_lines.append(line.strip())
            
        Storage.save_file(file_name, clean_lines)
        return new_file_name
        

    @staticmethod
    def save_file(file_name :str, data :list[str] | list[ list[str]]) -> None:
        """
        Save data to a JSON file in the project folder.
        File must have the json extension.

        :param file_name: The full name of the file.
        :type file_name: str
        :param data: The data to save (must be serializable to JSON).
        :type data: list of strings
        :return None: Nothing
        :raises SyntaxError: if file_name does not end with '.json'
        """

        if not file_name.endswith('.json'):
            raise SyntaxError

        
        file_path :str= os.path.join(PROJECT_DIR, file_name)

        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)


    @staticmethod
    def save_file_dictionary(file_name :str, data :dict[str, str | dict[str, int]]) -> None:
        """
        Save dicitonaries to a JSON file in the project folder.
        File name must have the json extension.

        :param file_name: The full name of a new file.
        :type file_name: str
        :param data: The data to save (must be serializable to JSON).
        :type data: list of strings
        :return None: Nothing
        :raises SyntaxError: if file_name does not end with '.json'
        """

        if not file_name.endswith('.json'):
            raise SyntaxError

        
        file_path :str= os.path.join(PROJECT_DIR, file_name)

        if not os.path.isfile(file_path):
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)



    @staticmethod
    def load_file(file_name :str) -> str:
        """
        Load account information from a file and returns it in json format.

        :param file_name: The name of the file with extension.
        :type file_name: str
        :return str: The file's data, or an empty str if the file doesn't exist.
        :requires: file_name includes the .json extension && the file exists
        """
        file_path :str= os.path.join(PROJECT_DIR, file_name)
        try:
            with open(file_path) as f:
                return f.read()
        except FileNotFoundError:
            print(f"Something went wrong! File {file_name} cound't be opened.\n     Exiting program...\n")
            sys.exit(-1)
    

    @staticmethod
    def load_file_lines(file_name :str) -> list[str]:
        """
        Returns the contents of a JSON file previously converted into a single String as a list of every line in the file.

        :param file_name: The name of the file with extension.
        :type file_name: str
        :return strings list: A list of strings, each representing a line in the file.
        :requires: file_name includes the .json extension && the file exists 
        """
        file_path :str= os.path.join(PROJECT_DIR, file_name)
        with open(file_path, "r") as f:
            return json.load(f)
    
    @staticmethod
    def initialize_instructions() -> str:
        """
        Initializes the instruction list json file
        """
        file_name: str = "valid_instructions.json"
        if not os.path.isfile(file_name):
            data :dict[str, str | dict[str, int]]= {
                'valid start': "_start", 
                'cpu': {
                    'mov': 2,
                    'halt': 0,
                    'cmp': 2,
                    'jmp': 1,
                    'jb': 1,
                    'jl': 1,
                    'ja': 1,
                    'jg': 1,
                    'je': 1,
                    'jne': 1,
                    'jz': 1,
                    'js': 1,
                    'jc': 1,
                    'jo': 1
                },
                'alu': {
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
                }, 
                'fpu': {
            
                }
            }
            Storage.save_file_dictionary(file_name, data)
        return file_name
    

    @staticmethod
    def read_valid_start(file_name: str) -> str:
        """
        Returns the accepted start declaration according to the settings file (valid_instructions.json)

        :param file_name: name of the file that holds the settings
        :type file_name: str
        :return: the valid start declaration
        :type: str
        """
        data: dict[str, str | dict[str, int]] = {}
        with open(file_name, "r") as file:
            data = json.load(file)
        return data['valid start']  # type: ignore
    
    @staticmethod
    def read_valid_instructions(file_name: str) -> dict[str, dict[str, int]]:
        """
        Returns the valid instructions setting from the settings file (valid_instructions.json)
                
        :param file_name: name of the file that holds the settings
        :type file_name: str
        :return: the valid instructions for the current state of this program
        :rtype: dict[str, dict[str, int]]
        """
        data: dict[str, str | dict[str, int]] = {}
        
        with open(file_name, "r") as file:
            data = json.load(file)
        
        ret_data: dict[str, dict[str, int]] = {key: value for key, value in data.items() if isinstance(value, dict)}
        return ret_data

