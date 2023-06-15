"""Implementation for all games."""

from enum import Enum

from games.singleplayer import SingleplayerGame


class Gamemode(Enum):
    """Enum class of all available gamemodes."""

    SINGLEPLAYER = SingleplayerGame
