
from abc import ABC, abstractmethod, abstractstaticmethod
from io import TextIOWrapper
import os
from typing import Any, Callable, TypeVar

from logger import Logger

T = TypeVar("T")

class Config(ABC):
    """
    Class to handle and manage a config file at a specified file path
    using a basic TOML-style config file
    """
    logger = Logger("Config")

    class ParserUtil:
        class AbstractParser(ABC):
            @abstractmethod
            def parse(value: str):
                pass
            @abstractmethod
            def stringify(value) -> str:
                pass
        class Parser(AbstractParser):
            def __init__(self, parser: type | Callable[[str], T], stringifier: type | Callable[[T], str] = str):
                self.parser = parser
                self.stringifier = stringifier
            def parse(self, value: str) -> T:
                return self.parser(value)
            def stringify(self, value: T) -> str:
                return self.stringifier(value)
        INT_PARSER = Parser(int)
        FLOAT_PARSER = Parser(float)
        STRING_PARSER = Parser(str)
        STRING_LIST_PARSER = Parser(lambda value: value.split("|"), lambda value: "|".join(value))

    class Entry:
        def __init__(self, name: str, validator, description: str, default_value):
            self.name = name
            self.validator = validator
            self.description = description
            self.value = default_value
            self.default_value = default_value
        def write(self, file: TextIOWrapper):
            for line in self.description.split("\n"):
                file.write(f"# {line}\n")
            file.write(f"{self.name}={self.validator.stringify(self.value)}\n\n")
        def parse(self, value):
            try:
                parsed_value = self.validator.parse(value)
            except ValueError:
                return False
            if parsed_value != self.value:
                Config.logger.debug(
                    f"Config value '{self.name}' changed to '{parsed_value}' from '{self.value}'")
                self.value = parsed_value
            return self.value
    
    def __init__(self, config_location):
        self.file_location = config_location
        # Options
        self.config_cache = {}
        self._add_config_options()
        # Create a default config file if one does not exist
        if not os.path.exists(self.file_location):
            self.logger.info("No config file found, creating default")
            with open(self.file_location, "x") as file:
                for entry in self.config_cache.values():
                    entry.write(file)
            self.last_read = os.stat(self.file_location).st_mtime
        else:
            self.logger.info(
                f"Loading config from file '{self.file_location}'")
            self.load_from_file()

    @abstractmethod
    def _add_config_options(self):
        pass

    def _add_config_option(self, *args):
        match args:
            case (Config.Entry(),):
                option = args[0]
            case (str(), _, str(), _):
                option = Config.Entry(*args)
            case _:
                self.logger.error("Failed to initialize config option from: ", args)
                return
        self.logger.debug(f"Initialised config option '{option.name}' with default value '{option.default_value}'")
        self.config_cache[option.name] = option

    def load_from_file(self):
        """
        Reads the entire file and populates the config cache
        """
        # Open file
        file = open(self.file_location, "rt")
        self.logger.info(f"Parsing config file at '{self.file_location}'")
        for line in file.readlines():
            line = line.removesuffix('\n')
            # Comments, empty lines in config file
            if line.startswith('#') or not line.strip():
                continue
            # Does not follow key=value syntax
            if '=' not in line:
                self.logger.warn(
                    f"Invalid syntax in '{self.file_location}', line reads '{line}'!")
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.removeprefix(" ")
            if (key in self.config_cache):
                # Detecting changes
                self.config_cache[key].parse(value)
            else:
                self.logger.warn(
                    f"Unknown config option '{key}', with value '{value}'!")
        self.last_read = os.stat(self.file_location).st_mtime

    def check_file_changes(self):
        """
        Reload the config file if it has changed since we last read
        """
        # Check if config file has been updated
        if os.stat(self.file_location).st_mtime > self.last_read:
            self.load_from_file()

    def get_option(self, key) -> str:
        # Get an option from the config file
        self.check_file_changes()
        return self.config_cache[key].value

class MainConfig(Config):
    DICTIONARY_LOCATION = "dictionary_location"
    NUMBER_LIVES = "number_of_lives"
    GAMEMODES_DIR = "gamemodes_directory"

    def _add_config_options(self):
        self._add_config_option(MainConfig.DICTIONARY_LOCATION, Config.ParserUtil.STRING_LIST_PARSER, "Path to the word list the game uses", ["./words.txt", "./words_alpha.txt", "-./profanity-list.txt", "-./word-blacklist.txt"])
        self._add_config_option(MainConfig.NUMBER_LIVES, Config.ParserUtil.INT_PARSER, "Number of lives the player has", 8)
        self._add_config_option(MainConfig.GAMEMODES_DIR, Config.ParserUtil.STRING_PARSER, "Directory to load gamemode configs from", "./gamemodes/")