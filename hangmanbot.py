from typing import Mapping
from discord import AutocompleteContext, Bot, Embed, Intents,\
    ApplicationContext, Option, OptionChoice, SlashCommandGroup, SlashCommand,\
    Color, EmbedField, SlashCommandOptionType
from discord.ext.commands import Cooldown, CooldownMapping, BucketType,\
    slash_command
from discord.utils import basic_autocomplete

import resources.config as cfg
from logger import Logger
from resources.serverconfigmanager import GamemodeConfigsManager
from resources.servermanager import ServerManager


class HangmanBot(Bot):
    """Discord bot implementation"""
    logger = Logger("HangmanBot")
    def __init__(self, config: cfg.BotConfig):
        self.config = config
        intents = Intents.none()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__("Hangman game for Discord", intents=intents)

        # self.add_application_command(self.play)
        self.config_command = SlashCommandGroup(
            "config", "Configure options for hangman"
        )

        self.configs_manager = ServerManager(
            self,
            lambda: self.config.get_value(cfg.BotConfig.GAMEMODES_DIR)
        )

        # self.add_application_command(self.play_command)
        self.add_application_command(self.config_command)

    def run(self) -> None:
        """Run the bot. Blocking call."""
        super().run(
            self.config.get_value(cfg.BotConfig.DISCORD_TOKEN),
            reconnect=True
        )

    async def on_ready(self):
        """Called when bot is connected to the Discord Gateway and ready"""
        self.configs_manager.init_for_guilds(self.guilds)

    async def play(ctx: ApplicationContext,
                   gamemode: cfg.GamemodeConfig):
        """Start a game"""
        # Call relevant Game constructor
        game = gamemode.get_value(cfg.GamemodeConfig.GAME_TYPE)\
                .value(gamemode)
        # Run game
        game.run(ctx)

    def on_message(self):
        ...
