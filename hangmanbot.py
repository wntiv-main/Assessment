from typing import Any
from discord import Bot, Intents, ApplicationContext, SlashCommandGroup

from config import MainConfig

class HangmanBot(Bot):
    def __init__(self, config: MainConfig):
        self.config = config
        intents = Intents.none()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__("Hangman game for Discord", intents=intents)

        self.play_command = SlashCommandGroup("play", "Start a game of hangman")
        self.config_command = SlashCommandGroup("config", "Configure options for hangman")

        # Have to define in __init__
        self.add_application_command(self.command)

    def run(self) -> None:
        super().run(self.config.get_value(MainConfig.DISCORD_TOKEN), reconnect=True)

    def on_message(self):
        ...

