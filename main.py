from io import TextIOWrapper
import os
import random
from abc import ABC, abstractmethod, abstractstaticmethod
from enum import IntEnum
import time
from typing import Callable

from logger import Logger
from config import MainConfig
from hangmanbot import HangmanBot
from resourcemanager import ResourceManager


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

    def __init__(self, file_path_provider: Callable[[], list[str]]):
        super().__init__()
        # Defer word list loading as it could be slow
        self.file_paths = file_path_provider
        self.words = []

    def reload_inner(self):
        # Setup word list
        # Use HashSet instead of list, as order does not matter and
        # HashSet has much better performance for removing items, as
        # well as not needing to manually check for duplicates
        self.words = set()
        for file_path in self.file_paths():
            start_time = time.perf_counter()
            list_type = "append"

            if file_path.startswith("-"):
                file_path = file_path.removeprefix("-")
                list_type = "blacklist"
            elif file_path.startswith("&"):
                file_path = file_path.removeprefix("&")
                list_type = "whitelist"
            with open(file_path) as file:
                # TODO: balance readability and performance
                match list_type:
                    case "blacklist":
                        # Use of two calls to map and passing unbound functions is preferable as these functions
                        # are all provided by the standard library, and are implemented in C as opposed to Python
                        # By doing this the runtime can stay in C code for longer, and does not have to switch back
                        # out into the Python code (e.g. lambda) as often
                        # self.words -= frozenset(map(lambda word: word.strip().lower(), frozenset(file.readlines())))
                        if self.logger.is_debug():
                            removed_words = self.words.intersection(frozenset(map(str.lower, map(str.strip, frozenset(file.readlines())))))
                            self.logger.debug(f"'{file_path}' removed {len(removed_words)}: {list(removed_words)}")
                        self.words -= frozenset(map(str.lower, map(str.strip, frozenset(file.readlines()))))
                    case "whitelist":
                        # Multiple calls to map and filter with unbound stdlib functions for performance (see above)
                        self.words &= frozenset(map(str.lower, map(str.strip, frozenset(file.readlines()))))
                    case "append":
                        # Multiple calls to map and filter with unbound stdlib functions for performance (see above)
                        self.words |= frozenset(
                            map(str.lower,
                                filter(str.isalpha,
                                    map(str.strip, frozenset(file.readlines())))))
            self.logger.debug(f"Loading words from '{file_path}', took {(time.perf_counter() - start_time) * 1000}ms")
        start_time = time.perf_counter()
        self.words -= frozenset((None,))
        self.words = list(self.words)
        self.logger.debug(f"Finalising word list, took {(time.perf_counter() - start_time) * 1000}ms")


    def get_word(self):
        self.hook_ready()
        return random.choice(self.words)


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
    def output_progress(self):
        print(" ".join(self.progress))
    def turn(self):
        self.output_progress()
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
                        self.output_progress()
                        self.state = Player.State.WON
                else:
                    print(f"The letter '{guess.upper()}' is not in the word!")
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = Player.State.DEAD
                break


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: MainConfig):
        self.config = config
        self.random = RandomWordProvider(
            lambda: self.config.get_value(MainConfig.DICTIONARY_LOCATION))
        self.config.get_option(MainConfig.DICTIONARY_LOCATION).when_changed(lambda _, _1: self.random.reload())

    @abstractmethod
    def run(self):
        pass

class SingleplayerGame(Game):
    def __init__(self, config: MainConfig):
        super().__init__(config)
        self.player = Player(self.random.get_word(), self.config.get_value(MainConfig.NUMBER_LIVES))

    def run(self):
        while self.player.state == Player.State.PLAYING:
            self.player.turn()
            self.config.check_file_changes()
        match self.player.state:
            case Player.State.WON:
                print("YOU WIN!!!")
            case Player.State.DEAD:
                print(f"YOU LOST! The word was '{self.player.word}'")


game = SingleplayerGame(MainConfig("./config.txt"))
# game.run()

bot = HangmanBot(MainConfig("./config.txt"))
bot.run()
