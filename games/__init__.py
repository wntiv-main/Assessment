from enum import Enum

from .singleplayer import SingleplayerGame


class Gamemode(Enum):
    SINGLEPLAYER = SingleplayerGame
