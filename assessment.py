from io import TextIOWrapper
import os
import random
from abc import ABC, abstractmethod, abstractstaticmethod
from enum import IntEnum
from typing import Callable
import dotenv
from logger import Logger
from config import MainConfig

dotenv.load_dotenv()


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

    def __init__(self, config: MainConfig):
        self.config = config
        self.random = RandomWordProvider(
            self.config.get_option(MainConfig.DICTIONARY_LOCATION))

    @abstractmethod
    def run(self):
        pass

class SingleplayerGame(Game):
    def __init__(self, config: MainConfig):
        super().__init__(config)
        self.player = Player(self.random.get_word(), self.config.get_option(MainConfig.NUMBER_LIVES))

    def run(self):
        while self.player.state == Player.State.PLAYING:
            self.player.turn()
        match self.player.state:
            case Player.State.WON:
                print("YOU WIN!!!")
            case Player.State.DEAD:
                print(f"YOU LOST! The word was '{self.player.word}'")


game = SingleplayerGame(MainConfig("./config.txt"))
game.run()