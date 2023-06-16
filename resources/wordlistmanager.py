"""Manager of a word list from a set of files."""

from asyncio import Lock
from enum import IntEnum
from pathlib import Path
import time
from typing import Callable, Coroutine
from logger import Logger
from resources.resourcemanager import ResourceManager


class WordListManager(ResourceManager):
    """
    Produces a word list from a file list.

    Files can be blacklist or whitelists applied over current list, or
    just be appended to current list. Accepts a "|"-seperated list of
    file paths, with optional prefixes for modifiers ("-" is blacklist,
    "&" is whitelist).
    """

    logger = Logger()
    file_locks: dict[Path, Lock] = {}

    class ListType(IntEnum):
        """Enum of ways this sublist can be treated by the word list."""

        APPEND = 0
        BLACKLIST = 1
        WHITELIST = 2

    def __init__(self, file_paths: str,
                 task_handler: Callable[[Coroutine | Callable], None]):
        """Create the word list from the given "|"-seperated paths."""
        super().__init__(task_handler)
        self.file_paths = file_paths.split("|")
        self.words = ()

    async def _reload_inner(self):
        """Parse all files and assemble word list."""
        # Setup word list
        # Use HashSet instead of list, as order does not matter and
        # HashSet has much better performance for removing items, as
        # well as not needing to manually check for duplicates
        self.words = set()
        for file_path in self.file_paths:
            list_type = WordListManager.ListType.APPEND
            # Check for blacklist/whitelist modifiers
            if file_path.startswith("-"):
                file_path = file_path.removeprefix("-")
                list_type = WordListManager.ListType.BLACKLIST
            elif file_path.startswith("&"):
                file_path = file_path.removeprefix("&")
                list_type = WordListManager.ListType.WHITELIST
            file_path = Path(file_path)
            if not file_path.exists() or not file_path.is_file():
                self.logger.warn(f"File '{file_path}' does not exist "
                                 f"while loading word list")
                continue
            if file_path not in WordListManager.file_locks:
                WordListManager.file_locks[file_path] = Lock()
            # Lock file path so no other WordListManagers use it while
            # we do, to avoid IOError, wait until file is unlocked.
            async with WordListManager.file_locks[file_path]:
                start_time = time.perf_counter()
                self._parse_file(file_path, list_type)
            self.logger.debug(
                f"Loading words from '{file_path}', took "
                f"{(time.perf_counter() - start_time) * 1000}ms")
        self.words = tuple(self.words)

    def _parse_file(self, file_path: Path, list_type: ListType):
        try:
            with file_path.open("rt") as file:
                match list_type:
                    case WordListManager.ListType.BLACKLIST:
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
                            self.logger.debug(f"'{file_path}' removed "
                                              f"{len(removed_words)} words")
                        self.words -= frozenset(
                            map(str.lower,
                                map(str.strip,
                                    frozenset(file.readlines()))))
                    case WordListManager.ListType.WHITELIST:
                        # Remove everything not in this list
                        # Multiple calls to map and filter with unbound
                        # stdlib functions for performance (see above)
                        self.words &= frozenset(
                            map(str.lower,
                                map(str.strip,
                                    frozenset(file.readlines()))))
                    case WordListManager.ListType.APPEND:
                        # Add everything in this list
                        # Multiple calls to map and filter with unbound
                        # stdlib functions for performance (see above)
                        self.words |= frozenset(
                            map(str.lower,
                                filter(str.isalpha,
                                    map(str.strip,
                                        frozenset(file.readlines())))))
        # File not available
        except IOError as e:
            self.logger.error(f"Could not open file {file_path}, due to {e}")

    def __str__(self) -> str:
        """Return string that would create identical word list."""
        return "|".join(self.file_paths)
