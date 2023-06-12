from abc import ABC, abstractmethod
from enum import Enum, EnumType
from pathlib import Path
from typing import Callable, TypeVar

from discord.ext.commands import Converter
from discord.ext.commands.context import Context

T = TypeVar("T")


class ParserUtil:
    """Utility classes for parsing strings into various other objects"""
    class AbstractParser(ABC, Converter):
        """Base class all parsers derive from"""
        async def convert(self, ctx: Context, argument: str):
            return self.parse(argument)

        @abstractmethod
        def parse(self, value: str):
            """Take a string and return an object"""
            pass

        @abstractmethod
        def stringify(self, value) -> str:
            """Take an object and return a string"""
            pass


    class Parser(AbstractParser):
        """Parser to wrap a parser and a stringifier function"""
        def __init__(self, parser: type | Callable[[str], T],
                     stringifier: type | Callable[[T], str] = str):
            self.parser = parser
            self.stringifier = stringifier

        def parse(self, value: str) -> T:
            return self.parser(value)
        def stringify(self, value: T) -> str:
            return self.stringifier(value)


    class EnumParser(AbstractParser):
        """Parser for an enum class"""
        def __init__(self, enum: EnumType):
            self.enum = enum

        def parse(self, value: str) -> Enum:
            try:
                return self.enum[value.upper()]
            except KeyError as e:
                error = ValueError(f"{value} is not a valid option for"\
                                   f" {self.enum.__name__} enum!")
                error.__cause__ = e
                raise error

        def stringify(self, value: Enum) -> str:
            return value.name.lower()

    @staticmethod
    def parse_bool(value: str):
        return value.lower().strip() in ("true", "yes", "y", "1")

    BOOL_PARSER = Parser(parse_bool)
    INT_PARSER = Parser(int)
    FLOAT_PARSER = Parser(float)
    STRING_PARSER = Parser(str)
    PATH_PARSER = Parser(Path)
    STRING_LIST_PARSER = Parser(lambda value: value.split("|"),
                                lambda value: "|".join(value))