"""Utility classes for parsing and stringifying specific objects."""

from abc import ABC, abstractmethod
from enum import Enum, EnumType
import inspect
from pathlib import Path
from typing import Callable, TypeVar

from discord.ext.commands import Converter

from resources.wordlistmanager import WordListManager

T = TypeVar("T")


class AbstractParser(ABC, Converter):
    """Utility class for parsing strings into various other objects."""

    @abstractmethod
    def parse(self, value: str):
        """Take a string and return an object."""
        pass

    @abstractmethod
    def stringify(self, value) -> str:
        """Take an object and return a string."""
        pass


class Parser(AbstractParser):
    """Parser to wrap a parser and a stringifier function."""

    def __init__(self, parser: type | Callable[[str], T],
                 stringifier: type | Callable[[T], str] = str):
        """Create a parser from a function returning a string."""
        self.parser = parser
        self.stringifier = stringifier

    def parse(self, value: str) -> T:
        """Call parser to parse value."""
        return self.parser(value)

    def stringify(self, value: T) -> str:
        """Call stringifier to stringify value."""
        return self.stringifier(value)


class ComplexParser(Parser):
    """Parser that requires extra information from the parsee."""

    def __init__(self, parser: type | Callable[..., T],
                 stringifier: type | Callable[[T], str] = str):
        """Create a parser from a function."""
        self.parser = parser
        self.arg_names = inspect.getfullargspec(self.parser)[0]
        self.stringifier = stringifier

    def parse(self, value: str, context) -> T:
        """Call parser with extra information from context."""
        kwargs_to_pass = {}
        for arg in self.arg_names:
            if hasattr(context, arg):
                kwargs_to_pass[arg] = getattr(context, arg)
        return self.parser(value, **kwargs_to_pass)

    def stringify(self, value: T) -> str:
        """Call stringifier to stringify value."""
        return self.stringifier(value)


class EnumParser(AbstractParser):
    """Parser for an enum class."""

    def __init__(self, enum: EnumType):
        """Create a parser from an enum class."""
        self.enum = enum

    def parse(self, value: str) -> Enum:
        """Try find enum value from string value."""
        try:
            return self.enum[value.upper()]
        except KeyError as e:
            error = ValueError(f"{value} is not a valid option for "
                               f"{self.enum.__name__} enum!")
            error.__cause__ = e
            raise error

    def stringify(self, value: Enum) -> str:
        """Return lowercase name of enum."""
        return value.name.lower()


@staticmethod
def _parse_bool(value: str):
    """Parse string as a boolean value, allow for some options."""
    return value.lower().strip() in ("true", "yes", "y", "1")


BOOL_PARSER = Parser(_parse_bool)
INT_PARSER = Parser(int)
FLOAT_PARSER = Parser(float)
STRING_PARSER = Parser(str)
PATH_PARSER = Parser(Path)
STRING_LIST_PARSER = Parser(lambda value: value.split("|"),
                            lambda value: "|".join(value))
WORD_LIST_PARSER = ComplexParser(WordListManager)
