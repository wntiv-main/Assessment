from abc import ABC, abstractmethod
from enum import Enum, EnumType
from typing import Callable, TypeVar

T = TypeVar("T")

class ParserUtil:
    class AbstractParser(ABC):
        @abstractmethod
        def parse(self, value: str):
            pass
        @abstractmethod
        def stringify(self, value) -> str:
            pass
    class Parser(AbstractParser):
        def __init__(self, parser: type | Callable[[str], T], stringifier: type | Callable[[T], str] = str):
            self.parser = parser
            self.stringifier = stringifier
        def parse(self, value: str) -> T:
            return self.parser(value)
        def stringify(self, value: T) -> str:
            return self.stringifier(value)
    class EnumParser(AbstractParser):
        def __init__(self, enum: EnumType):
            self.enum = enum
        def parse(self, value: str) -> Enum:
            return self.enum[value.upper()]
        def stringify(self, value: Enum) -> str:
            return value.name.lower()
    INT_PARSER = Parser(int)
    FLOAT_PARSER = Parser(float)
    STRING_PARSER = Parser(str)
    STRING_LIST_PARSER = Parser(lambda value: value.split("|"), lambda value: "|".join(value))