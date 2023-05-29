from abc import ABC, abstractmethod
from config.gamemodeconfig import GamemodeConfig
from logger import Logger
from main import Player


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: GamemodeConfig):
        self.config = config
    @abstractmethod
    def run(self):
        pass