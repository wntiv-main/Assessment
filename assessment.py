from io import TextIOWrapper
import os
import sys
import random
from abc import ABC, abstractmethod, abstractstaticmethod
from enum import IntEnum
from typing import Callable
import pathlib

os.system("")

class ResourceManager(ABC):
    class State(IntEnum):
        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2

    def __init__(self):
        self.state = ResourceManager.State.UNINITIALIZED

    def reload(self):
        self.state = ResourceManager.State.INITIALIZING
        self.reload_inner()
        self.state = ResourceManager.State.READY

    @abstractmethod
    def reload_inner(self):
        pass

    def hook_ready(self):
        # For future threading possibility:
        # May need to synchronize and await for resource to finish loading so we can use it
        match self.state:
            case ResourceManager.State.UNINITIALIZED:
                self.reload()
            case ResourceManager.State.INITIALIZING:
                while self.state != ResourceManager.State.READY:
                    pass
            case ResourceManager.State.READY:
                pass


class Logger:
    class Level(IntEnum):
        DEBUG = 0
        INFO = 1
        WARN = 2
        ERROR = 3
        DEFAULT = 4
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def __init__(self, name: str, level: Level = Level.DEFAULT):
        self.name = name
        self.level = level

    def get_level(self):
        if self.level == Logger.Level.DEFAULT:
            return Logger.Level.DEBUG
        return self.level

    def _traceback(self):
        caller = sys._getframe().f_back.f_back
        match self.get_level():
            case Logger.Level.DEBUG:
                return f"{caller.f_code.co_name} at ./{pathlib.Path(caller.f_code.co_filename).absolute().relative_to(pathlib.Path('./').absolute())}:{caller.f_lineno}"
            case _:
                return f"{caller.f_code.co_name}"
    
    def is_debug(self):
        return self.get_level() <= self.Level.DEBUG

    def debug(self, *args, **kwargs):
        if self.is_debug():
            print(f"{self.OKCYAN}[{self.name}:DEBUG in {self._traceback()}]", *args, self.ENDC, **kwargs)

    def is_info(self):
        return self.get_level() <= self.Level.INFO
    
    def info(self, *args, **kwargs):
        if self.is_info():
            print(f"[{self.name}:INFO in {self._traceback()}]", *args, **kwargs)

    def is_warn(self):
        return self.get_level() <= self.Level.WARN
    
    def warn(self, *args, **kwargs):
        if self.is_warn():
            print(f"{self.WARNING}[{self.name}:WARN in {self._traceback()}]", *args, self.ENDC, **kwargs)

    def is_error(self):
        return self.get_level() <= self.Level.ERROR
    
    def error(self, *args, **kwargs):
        if self.is_error():
            print(f"{self.FAIL}[{self.name}:ERROR in {self._traceback()}]", *args, self.ENDC, **kwargs)

# Anything that can provide words
# For future multiplayer support?


class WordProvider(ABC):
    @abstractmethod
    # Return a word somehow plz
    def get_word(self) -> str:
        pass

# Singleplayer random word provider


class RandomWordProvider(WordProvider, ResourceManager):
    logger = Logger("RandomWordProvider")

    def __init__(self, file_paths):
        super().__init__()
        # Defer word list loading as it could be slow
        self.file_paths = file_paths
        self.words = set()

    def reload_inner(self):
        # Setup word list
        self.words = set()
        for file_path in self.file_paths:
            self.logger.info(f"Loading words from '{file_path}'")
            is_blacklist = False
            if file_path.startswith("-"):
                file_path = file_path.removeprefix("-")
                is_blacklist = True
            with open(file_path) as file:
                for word in file.readlines():
                    word = word.strip().lower()
                    if is_blacklist:
                        # if self.logger.is_debug() and word in self.words:
                            # self.logger.debug(f"'{word}' removed by blacklist '{file_path}'")
                        self.words.discard(word)
                    else:
                        if len(word) > 3 and word.isalpha():
                            self.words.add(word)
        self.words = list(self.words)

    def get_word(self):
        self.hook_ready()
        # Just a random word, no trailing newline
        # Removing newlines lazily so as to not have to loop over entire list
        return random.choice(self.words).lower().removesuffix("\n")


class Config:
    logger = Logger("Config")
    DICTIONARY_LOCATION = "dictionary_location"
    NUMBER_LIVES = "number_of_lives"
    
    class ParserUtil:
        class TypeParser:
            def __init__(self, parser: type | Callable[[str], any]):
                self.parser = parser
            def parse(self, value: str):
                return self.parser(value)
            def stringify(self, value) -> str:
                return str(value)
        class Parser(ABC):
            @abstractstaticmethod
            def parse(value: str):
                pass
            @abstractstaticmethod
            def stringify(value) -> str:
                pass
        class StringListParser(Parser):
            @abstractstaticmethod
            def parse(value: str) -> list[str]:
                return value.split("|")
            @abstractstaticmethod
            def stringify(value: list[str]) -> str:
                return "|".join(value)
        INT_PARSER = TypeParser(int)
        FLOAT_PARSER = TypeParser(float)
        STRING_PARSER = TypeParser(str)


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
        self._add_config_option(Config.DICTIONARY_LOCATION, Config.ParserUtil.StringListParser, "Path to the word list the game uses", ["./words.txt", "./words_alpha.txt", "-./profanity-list.txt", "-./word-blacklist.txt"])
        self._add_config_option(Config.NUMBER_LIVES, Config.ParserUtil.INT_PARSER, "Number of lives the player has", 8)
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
        file = open(self.file_location, "rt")
        # Parse config file to update {self.config_cache}
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
            if (key in self.config_cache):
                # Detecting changes
                self.config_cache[key].parse(value)
            else:
                self.logger.warn(
                    f"Unknown config option '{key}', with value '{value}'!")
        self.last_read = os.stat(self.file_location).st_mtime

    def check_file_changes(self):
        # Check if config file has been updated
        if os.stat(self.file_location).st_mtime > self.last_read:
            self.load_from_file()

    def get_option(self, key) -> str:
        # Get an option from the config file
        self.check_file_changes()
        return self.config_cache[key].value
    
class Player:
    class State(IntEnum):
        PLAYING = 0
        WON = 1
        DEAD = 2
    def __init__(self, word, lives):
        self.word = word
        self.lives = lives
        self.progress = ["_"] * len(word)
        self.guessed = []
        self.state = Player.State.PLAYING
    def turn(self):
        print(" ".join(self.progress))
        while guess := input("Enter your guess: ").strip().lower():
            if not guess.isalpha(): 
                print(f"Your guess '{guess}' should only contain letters")
                continue
            if len(guess) == 1:
                if guess in self.guessed:
                    print(f"You have already guessed '{guess.upper()}', try another.")
                    continue
                self.guessed.append(guess)
                if guess in self.word:
                    print(f"The letter '{guess.upper()}' is in the word!")
                    for i in range(len(self.word)):
                        if self.word[i] == guess:
                            self.progress[i] = guess.upper()
                    if "_" not in self.progress:
                        self.state = Player.State.WON
                else:
                    print(f"The letter '{guess.upper()}' is not in the word!")
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = Player.State.DEAD
                break


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: Config):
        self.config = config
        self.random = RandomWordProvider(
            self.config.get_option(Config.DICTIONARY_LOCATION))
        
    @abstractmethod
    def run(self):
        pass

class SingleplayerGame(Game):
    def __init__(self, config: Config):
        super().__init__(config)
        self.player = Player(self.random.get_word(), self.config.get_option(Config.NUMBER_LIVES))

    def run(self):
        while self.player.state == Player.State.PLAYING:
            self.player.turn()
        match self.player.state:
            case Player.State.WON:
                print("YOU WIN!!!")
            case Player.State.DEAD:
                print(f"YOU LOST! The word was '{self.player.word}'")
            


game = SingleplayerGame(Config("./config.txt"))
game.run()