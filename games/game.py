from abc import ABC, abstractmethod
from discord import ApplicationContext

# Normal import because python and cyclic imports
import config.gamemodeconfig as gmc
from logger import Logger


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: gmc.GamemodeConfig):
        self.config = config

    @abstractmethod
    def run(self, ctx: ApplicationContext):
        pass

