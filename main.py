# import random
# from abc import ABC, abstractmethod
# from enum import IntEnum
# import time
# from typing import Callable

from config import GamemodeConfig
from games import Gamemode

# from logger import Logger
from config import BotConfig
from hangmanbot import HangmanBot
# from resourcemanager import ResourceManager


# # Anything that can provide words
# # For future multiplayer support?






Gamemode.SINGLEPLAYER.value(GamemodeConfig("./gamemodes/singleplayer.txt")).run()

# # game = SingleplayerGame(BotConfig("./config.txt"))
# # game.run()


# bot = HangmanBot(BotConfig("./config.txt"))
# bot.run()
