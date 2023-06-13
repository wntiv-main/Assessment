import os
import pathlib
from pathlib import Path
import shutil
from typing import Callable, Coroutine, Iterable, Mapping

from discord import (
    ApplicationContext, Bot, Color, Embed, EmbedField, Guild, Interaction, Message, Option, OptionChoice, Permissions,
    SlashCommand, ApplicationCommandMixin, SlashCommandGroup, SelectOption
)
from discord.ui import View, Select, string_select
from games.game import Game
from resources.config import GamemodeConfig
from logger import Logger
from resources.resourcemanager import ResourceManager


class ServerManager(ResourceManager):
    logger = Logger()
    SELECT_GAMEMODE_MSG = "Please select a gamemode"
    _ALPHABET = "abcdefghijklmnopqrstuvwxyz"
    _DIGITS = "0123456789"
    _ALLOWED_FIRST_CHARS = frozenset(_ALPHABET + _ALPHABET.upper())
    _ALLOWED_CHARS = frozenset(_ALPHABET + _ALPHABET.upper() + _DIGITS + "-_ ")

    class GamemodeSelectorView(View):
        def __init__(self, server: 'ServerManager',
                     callback: Callable[[Interaction, str], Coroutine]):
            super().__init__(timeout=None)
            self.callback = callback
            select: Select = self.get_item("gamemode_select")
            for name, cfg in server.gamemodes.items():
                select.add_option(
                    label=name,
                    description=cfg.get_value(GamemodeConfig.DESCRIPTION)
                )

        @string_select(
                custom_id="gamemode_select",
                placeholder="Select Gamemode...",
                min_values=1,
                max_values=1,
                options=[])
        async def on_select(self, select: Select, ctx: Interaction):
            self.disable_all_items()
            await ctx.message.delete() # (view=self)
            self.stop()
            await self.callback(ctx, select.values[0])

    def __init__(self, path: Path, guild_id: int,
                 task_handler: Callable[[Coroutine], None],
                 reload: Callable[[], None]):
        super().__init__(task_handler)
        self.sync_discord_commands = reload
        self.path = path
        self.id = guild_id
        self.gamemodes: dict[str, GamemodeConfig] = {}
        self.running_games: list[Game] = []
        self.play_command = SlashCommand(
            self.play,
            name="play",
            description="Start a game of hangman!",
            guild_ids=[self.id],
            guild_only=True,
            options=[Option(
                str,
                name="gamemode",
                required=False,
                description="The gamemode you want to play",
                choices=[]
            )]
        )
        required_perms = Permissions()
        required_perms.administrator = True
        self.config_command = SlashCommandGroup(
            name="config",
            description="Configure the bot and the gamemodes",
            guild_ids=[self.id],
            guild_only=True,
            default_member_permissions=required_perms)
        self.config_gamemode_command = self.config_command.create_subgroup(
            name="gamemode",
            description="Create and edit the gamemodes for this server"
        )
        self.config_new_command = SlashCommand(
            self.new_gamemode,
            name="new",
            description="Create a new gamemode",
            options=[
                Option(str, 
                       name="name",
                       description="The name of the new gamemode. "
                                   "Should only contain alphanumeric chars",
                       required=True,
                       max_length=100,
                       min_length=3)
            ],
            parent=self.config_gamemode_command)
        self.config_edit_command = SlashCommand(
            self.edit_gamemode,
            name="edit",
            description="Edit a gamemode",
            options=[
                Option(str,
                       name="name",
                       description="The gamemode to edit",
                       required=False,
                       choices=[])
            ],
            parent=self.config_gamemode_command)
        self.config_gamemode_command.add_command(self.config_new_command)
        self.config_gamemode_command.add_command(self.config_edit_command)

    @staticmethod
    def _get_name_error(name: str) -> str | None:
        # Validation checks, ordered by performance
        if len(name) < 1:
            return "Gamemode name cannot be empty"
        if len(name) > 50:
            return "Gamemode name cannot be longer than 50 chars"
        # Invalid first char
        if name[0] not in ServerManager._ALLOWED_FIRST_CHARS:
            return (f"First letter of name must be alphabetical "
                    f"(a-z, A-Z), got '{name[0]}'")
        # Invalid chars
        invalid_chars = set(name).difference(ServerManager._ALLOWED_CHARS)
        if invalid_chars:
            chrs_printable = (str(invalid_chars).removeprefix("{")
                                 .removesuffix("}"))
            return (f"Gamemode name should only contain alphanumeric "
                    f"chars (a-z, A-Z, 0-9), and spaces, underscores, "
                    f"and hyphens (' ', _, -). Found: {chrs_printable}")
        return None

    @staticmethod
    def _escaped_name(name: str) -> str:
        return name.lower().replace(" ", "-")

    async def _reload_inner(self):
        # Recursive walk of dir tree
        for child in self.path.rglob("*"):
            # Only open config files
            if child.is_file():
                if child.stem not in self.gamemodes:
                    # New files in dir
                    self.gamemodes[child.stem] = GamemodeConfig(
                        child, self.task_handler)
                else:
                    # Changes to old files in dir
                    self.gamemodes[child.stem].check_file_changes()
                    # Deleted files in dir
                    if (self.gamemodes[child.stem].state
                        == ResourceManager.State.REMOVED):
                        del self.gamemodes[child.stem]
        self.sync_command_choices()

    def load_defaults(self, default_configs: Iterable[Path]) -> None:
        if self.state != ResourceManager.State.READY or not self.path.exists():
            if not self.path.exists():
                self.path.mkdir()
            for file in default_configs:
                new_path = self.path.joinpath(file)
                shutil.copy(file.absolute(), new_path)
                cfg = GamemodeConfig(new_path)
                self.gamemodes[file.stem] = cfg
            self.sync_command_choices()
            self.state = ResourceManager.State.READY

    def sync_command_choices(self) -> None:
        options = [OptionChoice(name) for name, cfg in self.gamemodes.items()]
        self.play_command.options[0].choices = options
        self.config_edit_command.options[0].choices = options

    def add_command_to(self, bot: ApplicationCommandMixin) -> None:
        bot.add_application_command(self.play_command)
        bot.add_application_command(self.config_command)

    def remove_command_from(self, bot: ApplicationCommandMixin) -> None:
        bot.remove_application_command(self.play_command)
        bot.remove_application_command(self.config_command)

    async def play(self, ctx: ApplicationContext | Interaction,
                   gamemode: str | None):
        if gamemode is None:
            if isinstance(ctx, Interaction):
                self.logger.error(f"Selector called play with no value")
                return
            await ctx.send_response(
                embed=Embed(
                    title=ServerManager.SELECT_GAMEMODE_MSG,
                    color=Color.from_rgb(0, 255, 0)
                ),
                view=ServerManager.GamemodeSelectorView(
                    self, self.play),
                ephemeral=True
            )
            return
        if ServerManager._escaped_name(gamemode) not in self.gamemodes:
            title = f"Invalid option `{gamemode}`!"
            desc = ("That gamemode doesn't exist (yet). "
                    "Please try again, or if you think that this is "
                    "an error, contact an administrator. Valid "
                    "options are:")
            await ctx.send_response(
                embed=Embed(
                    title=title,
                    description=desc,
                    color=Color.from_rgb(255, 0, 0),
                    fields=[
                        EmbedField(
                            name=name,
                            value=config.get_value(
                                GamemodeConfig.DESCRIPTION)
                        )
                        for name, config in self.gamemodes.items()
                    ],
                ),
                ephemeral=True
            )
            return
        gamemode = ServerManager._escaped_name(gamemode)

        interaction: Interaction
        if isinstance(ctx, ApplicationContext):
            interaction = ctx.interaction
        else:
            interaction = ctx

        gamemode_config = self.gamemodes[gamemode]
        # Game play...
        game_ctor: type[Game] = gamemode_config.get_value(
            GamemodeConfig.GAME_TYPE).value
        game = game_ctor(gamemode_config, self.task_handler)
        self.running_games.append(game)
        await game.run(interaction)

    async def new_gamemode(self, ctx: ApplicationContext, name: str):
        error = ServerManager._get_name_error(name)
        if error is not None:
            await ctx.send_response(
                embed=Embed(
                    title=f"Could not create gamemode named `{name}`",
                    description=error,
                    color=Color.from_rgb(255, 0, 0)
                ),
                ephemeral=True
            )
            return
        display_name = name
        name = ServerManager._escaped_name(name)
        if name in self.gamemodes:
            await ctx.send_response(
                embed=Embed(
                    title=f"Could not create gamemode named `{name}`",
                    description=("This could be because there is a "
                                 "gamemode with this name already, "
                                 "or this name is reserved for "
                                 "internal usage."),
                    color=Color.from_rgb(255, 0, 0)
                ),
                ephemeral=True
            )
            return
        cfg = GamemodeConfig(
            self.path.joinpath(f"./{name}.txt"), self.task_handler)
        cfg.set_value(GamemodeConfig.DISPLAY_NAME, display_name)
        self.gamemodes[name] = cfg
        self.sync_discord_commands()
        self.edit_gamemode(ctx, name)

    async def edit_gamemode(self, ctx: ApplicationContext | Interaction,
                            name: str | None):
        if name is None:
            if isinstance(ctx, Interaction):
                self.logger.error(f"Selector called edit with no value")
                return
            # Gamemode not selected, send gamemode selector
            await ctx.send_response(
                embed=Embed(
                    title=ServerManager.SELECT_GAMEMODE_MSG,
                    color=Color.from_rgb(0, 255, 0)
                ),
                view=ServerManager.GamemodeSelectorView(
                    self, 
                    self.edit_gamemode),
                ephemeral=True
            )
            return
        name = ServerManager._escaped_name(name)
        interaction: Interaction
        if isinstance(ctx, ApplicationContext):
            interaction = ctx.interaction
        else:
            interaction = ctx
        await interaction.response.send_message(
            content=f"Editing config for {name}",
            ephemeral=True)

    async def update(self, msg: Message, bot: Bot):
        for game in self.running_games:
            await game.update(msg, bot)
