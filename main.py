# Callum Hynes
# AS91896 Programming Assignment
# 1/06/2023 / Version 2

from pathlib import Path
from hangmanbot import HangmanBot

bot = HangmanBot(Path("./config.txt"))
bot.run()
