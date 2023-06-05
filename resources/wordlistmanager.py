
from pathlib import Path
import time
from typing import Callable
from logger import Logger
from resources.resourcemanager import ResourceManager


class WordListManager(ResourceManager):
    """Produces a word list from a file list
    Files can be blacklist or whitelists applied over current list,
    or just be appended to current list
    """
    logger = Logger("WordListManager")

    def __init__(self, file_path_provider: Callable[[], list[str]]):
        super().__init__()
        # Defer word list loading as it could be slow
        self.file_paths = file_path_provider
        self.words = ()

    def reload_inner(self):
        """Parse all files and assemble word list"""
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
            file_path = Path(file_path)
            if not file_path.exists() or not file_path.is_file():
                self.logger.warn(f"File '{file_path}' does not exist while"\
                                 f" loading word list")
                continue
            with file_path.open() as file:
                match list_type:
                    case "blacklist":
                        # Remove anything in this list
                        # Use of two calls to map and passing unbound
                        # functions is preferable as these functions are all
                        # provided by the standard library, and are
                        # implemented in C as opposed to Python. By doing this
                        # the runtime can stay in C code for longer, and does
                        # not have to switch back out into the Python code
                        # (e.g. lambda) as often
                        if self.logger.is_debug():
                            # Calculating what words are going to be removed
                            # is slower, only do so if the logs are going to
                            # be visible anyways
                            removed_words = self.words.intersection(frozenset(
                                map(str.lower,
                                    map(str.strip, 
                                        frozenset(file.readlines())))))
                            self.logger.debug(f"'{file_path}' removed "\
                                              f"{len(removed_words)}: "\
                                              f"{list(removed_words)}")
                        self.words -= frozenset(
                            map(str.lower, 
                                map(str.strip, 
                                    frozenset(file.readlines()))))
                    case "whitelist":
                        # Remove everything not in this list
                        # Multiple calls to map and filter with unbound
                        # stdlib functions for performance (see above)
                        self.words &= frozenset(
                            map(str.lower,
                                map(str.strip,
                                    frozenset(file.readlines()))))
                    case "append":
                        # Add everything in this list
                        # Multiple calls to map and filter with unbound
                        # stdlib functions for performance (see above)
                        self.words |= frozenset(
                            map(str.lower,
                                filter(str.isalpha,
                                    map(str.strip,
                                        frozenset(file.readlines())))))
            self.logger.debug(f"Loading words from '{file_path}', took"\
                f" {(time.perf_counter() - start_time) * 1000}ms")
        self.words = tuple(self.words)
