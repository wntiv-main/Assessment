from abc import ABC, abstractmethod
from discord import ApplicationContext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import GamemodeConfig
from logger import Logger


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: 'GamemodeConfig'):
        self.config = config

    @abstractmethod
    def run(self, ctx: ApplicationContext):
        pass


# class 