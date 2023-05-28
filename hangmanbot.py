from typing import Any
from discord import Bot, Intents, ApplicationContext, SlashCommandGroup, SlashCommand
from functools import partial

from config import MainConfig, GamemodeConfig
from resourcemanager import GamemodeConfigsManager

class HangmanBot(Bot):
    def __init__(self, config: MainConfig):
        self.config = config
        intents = Intents.none()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__("Hangman game for Discord", intents=intents)

        self.gamemodes_manager = GamemodeConfigsManager(lambda: self.config.get_value(MainConfig.GAMEMODES_DIR))

        self.play_command = SlashCommandGroup("play", "Start a game of hangman")
        for name, config in self.gamemodes_manager.gamemodes.items():
            self.play_command.add_command(SlashCommand(
                name = name,
                callback = partial(self.start_gamemode, config),
                description = config.get_value(GamemodeConfig.DESCRIPTION),
                cooldown = config.get_value(GamemodeConfig.COMMAND_COOLDOWN)
            ))
        self.config_command = SlashCommandGroup("config", "Configure options for hangman")

        self.add_application_command(self.play_command)
        self.add_application_command(self.config_command)

    def run(self) -> None:
        super().run(self.config.get_value(MainConfig.DISCORD_TOKEN), reconnect=True)

    async def start_gamemode(self, config: GamemodeConfig, ctx: ApplicationContext):
        ...

    def on_message(self):
        ...

