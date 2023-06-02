# Callum Hynes - 1/06/2023
# AS91896 Programming Assignment
# Version 1

from config import GamemodeConfig
from games import Gamemode

# from logger import Logger
from config import BotConfig
from hangmanbot import HangmanBot

Gamemode.SINGLEPLAYER.value(
    GamemodeConfig("./gamemodes/singleplayer.txt")).run()

# # game = SingleplayerGame(BotConfig("./config.txt"))
# # game.run()

bot = HangmanBot(BotConfig("./config.txt"))
# bot.run()
