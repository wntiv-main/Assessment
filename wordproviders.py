from abc import ABC, abstractmethod
import random
import time
from typing import Callable

from logger import Logger
from resourcemanager import ResourceManager


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
        self.words = ()

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
        self.words -= frozenset((None,))
        self.words = tuple(self.words)

    def get_word(self):
        self.hook_ready()
        return random.choice(self.words)