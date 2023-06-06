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

    def _on_update_configs(self, guild: int, configs: Mapping[int, cfg.GamemodeConfig]):
        self.logger.debug(f"Updating play command for guild {guild}")

        if guild in self.play_commands:
            self.remove_application_command(self.play_commands[guild])

        @slash_command(description="Start a game of hangman!",
                       guild_ids=[guild],
                       guild_only=True)
        async def play(ctx: ApplicationContext,
                       gamemode: Option(
                            SlashCommandOptionType.string,
                            choices=[
                                OptionChoice(name, config.get_value(cfg.GamemodeConfig.DESCRIPTION))
                                for name, config in configs.items()
                            ],
                            required=True,
                       )):
            if gamemode not in configs:
                await ctx.send(
                    embed=Embed(
                        title="Invalid option!",
                        description="That gamemode doesn't exist (yet). Please "\
                        "try again, or if you think that this is and error, "\
                        "contact an administrator. Valid options are:",
                        color=Color.from_rgb(255, 0, 0),
                        fields=[
                            EmbedField(
                                name=name,
                                value=config.get_value(
                                    cfg.GamemodeConfig.DESCRIPTION)
                            )
                            for name, config in configs.items()
                        ],
                    )
                )
            else:
                await self.play(ctx, configs[gamemode])

        self.play_commands[guild] = play
        self.add_application_command(self.play_commands[guild])
        # TODO: TALK TO DISCORD
        # self.register_commands([self.play_commands[guild]])
        # self.play_command.add_command(
        #     SlashCommand(
        #         callback,
        #         name=name,
        #         description=config.get_value(cfg.GamemodeConfig.DESCRIPTION),
        #         cooldown=CooldownMapping.from_cooldown(
        #             rate=config.get_value(cfg.GamemodeConfig.COMMAND_COOLDOWN_RATE),
        #             per=config.get_value(cfg.GamemodeConfig.COMMAND_COOLDOWN_PER),
        #             type=BucketType.member
        #         ),
        #         guild_ids=[guild],
        #     )
        # )

    def run(self) -> None:
        """Run the bot. Blocking call."""
        super().run(
            self.config.get_value(cfg.BotConfig.DISCORD_TOKEN),
            reconnect=True
        )

    async def on_ready(self):
        """Called when bot is connected to the Discord Gateway and ready"""
        self.gamemodes_manager.init_for_guilds(self.guilds)

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
