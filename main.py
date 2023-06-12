# Callum Hynes - 1/06/2023
# AS91896 Programming Assignment
# Version 1

from pathlib import Path
from resources.config import GamemodeConfig
from games import Gamemode

# from logger import Logger
from resources.config import BotConfig
from hangmanbot import HangmanBot

# Gamemode.SINGLEPLAYER.value(
#     GamemodeConfig(Path("./gamemodes/singleplayer.txt"))).run()

# # game = SingleplayerGame(BotConfig("./config.txt"))
# # game.run()

bot = HangmanBot(Path("./config.txt"))
bot.run()
