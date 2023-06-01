from discord import AutocompleteContext, Bot, Embed, Intents,\
    ApplicationContext, Option, SlashCommandGroup, SlashCommand,\
    Color, EmbedField, SlashCommandOptionType
from discord.ext.commands import Cooldown, CooldownMapping, BucketType,\
    slash_command
from discord.utils import basic_autocomplete

import config as cfg
from logger import Logger
from resourcemanager import GamemodeConfigsManager


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

        self.add_application_command(self.play)
        self.config_command = SlashCommandGroup(
            "config", "Configure options for hangman"
        )

        self.gamemodes_manager = GamemodeConfigsManager(
            lambda: self.config.get_value(cfg.BotConfig.GAMEMODES_DIR),
            self._on_new_config
        )

        # self.add_application_command(self.play_command)
        self.add_application_command(self.config_command)

    def _on_new_config(self, guild: str, name: str,
                       config: cfg.GamemodeConfig):
        self.logger.debug(f"Adding gamemode '{name}' to guild {guild}")
        # Cannot use lambda due to async, cannot use functools.partial
        # due to missing __name__ attribute
        # async def callback(ctx: ApplicationContext):
        #     return await self.start_gamemode(config, ctx)
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

    @staticmethod
    def _get_gamemodes(ctx: AutocompleteContext):
        self: HangmanBot = ctx.bot
        return self.gamemodes_manager.gamemodes\
               [str(ctx.interaction.guild_id)].keys()

    @staticmethod
    @slash_command()
    async def play(ctx: ApplicationContext,
                   gamemode: Option(
                        SlashCommandOptionType.string,
                        autocomplete=basic_autocomplete(_get_gamemodes),
                        required=True,
                   )):
        """Discord bot command to start a game"""
        gamemodes = ctx.bot.gamemodes_manager.gamemodes[str(ctx.guild_id)]
        if gamemode not in gamemodes:
            ctx.send(
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
                        for name, config in gamemodes.items()
                    ],
                )
            )
        else:
            config = gamemodes[gamemode]
            # Call relevant Game constructor
            game = config.get_value(cfg.GamemodeConfig.GAME_TYPE)\
                   .value(config)
            game.run(ctx)

    def on_message(self):
        ...
