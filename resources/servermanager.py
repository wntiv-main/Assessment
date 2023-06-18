"""Manager for the resources of a single discord server."""

import datetime
from enum import Enum
import functools
from pathlib import Path
import shutil
from typing import Callable, Coroutine, Iterable

from discord import (
    ApplicationContext, Bot, ButtonStyle, Color, Embed, EmbedField,
    Interaction, Message, Option, OptionChoice, Permissions, SelectOption,
    SlashCommand, ApplicationCommandMixin, SlashCommandGroup
)
from discord.interactions import Interaction
from discord.ui import View, Select, string_select, Button, Item, Modal
from discord.ui.input_text import InputText

from games.game import Game
from resources.config import GamemodeConfig
from logger import Logger
from resources.config import Config
from resources.resourcemanager import ResourceManager
import parserutil


def _all_same_case(value: str):
    return value == value.lower() or value == value.upper()


def _prettify(name: str):
    words = []
    if "_" in name:
        # Snake case handling
        words = name.split("_")
    elif _all_same_case(name):
        # Single word, not camel case
        return name.title()
    else:
        # Camel case parsing
        for char in name:
            if char != char.lower() or not words:
                # Uppercase, or first char in str
                words.append(char)
            else:
                # Lowercase
                words[-1] += char
    return " ".join(words).title()


def _stringify(value):
    match value:
        case type():
            return value.__name__
        case Enum():
            return value.name.lower()
        case _:
            return str(value)


class ServerManager(ResourceManager):
    """Manager for the configs used by a singular discord server."""

    logger = Logger()
    _SELECT_GAMEMODE_MSG = "Please select a gamemode"
    _ALPHABET = "abcdefghijklmnopqrstuvwxyz"
    _DIGITS = "0123456789"
    _ALLOWED_FIRST_CHARS = frozenset(_ALPHABET + _ALPHABET.upper())
    _ALLOWED_CHARS = frozenset(_ALPHABET + _ALPHABET.upper() + _DIGITS + "-_ ")

    class GamemodeSelectorView(View):
        """A discord UI View with a select box for a gamemode."""

        def __init__(self, server: 'ServerManager',
                     callback: Callable[[Interaction, str], Coroutine]):
            """Initilise the view with callback for after selection."""
            super().__init__(timeout=None)
            self.callback = callback
            select: Select = self.get_item("gamemode_select")
            # Add all gamemodes to select box
            for name, cfg in server.gamemodes.items():
                select.add_option(
                    label=cfg.get_value(GamemodeConfig.DISPLAY_NAME),
                    description=cfg.get_value(GamemodeConfig.DESCRIPTION),
                    value=name
                )

        @string_select(
                custom_id="gamemode_select",
                placeholder="Select Gamemode...",
                min_values=1,
                max_values=1,
                options=[])
        async def on_select(self, select: Select, ctx: Interaction):
            """User made selection, close View."""
            self.disable_all_items()
            self.stop()
            await self.callback(ctx, select.values[0])

    class GamemodeEditorView(View):
        """A Discord UI View allowing editing of a gamemode config."""

        class TextEditorModal(Modal):
            """A Discord UI Modal to get a text input for an entry."""

            def __init__(self, parent: 'ServerManager.GamemodeEditorView',
                         entry: Config.Entry) -> None:
                """
                Create a text input modal for the given entry.

                Also requires the parent view that opened the modal.
                """
                key = entry.name
                super().__init__(
                    title=f"Set value for {_prettify(key)}:")
                self.parent = parent
                self.entry = entry
                self.input = InputText(
                    label=_prettify(key),
                    placeholder=_stringify(entry.default_value),
                    value=(None if entry.value == entry.default_value
                           else entry.value),
                    required=False
                )
                self.add_item(self.input)

            async def callback(self, interaction: Interaction):
                """Handle submission of the modal."""
                value = self.entry.parse(self.input.value)
                if isinstance(value, ValueError):
                    await interaction.response.send_message(
                        embed=Embed(
                            title=f"Invalid value for "
                                  f"{_prettify(self.entry.name)}",
                            description=f"{'. '.join(value.args)}",
                            color=Color.from_rgb(255, 0, 0)),
                        ephemeral=True,
                        delete_after=60)
                else:
                    await self.parent._callback(self.entry.name, value,
                                                interaction)
                self.stop()

        def __init__(self, config: GamemodeConfig, respond_to: Interaction):
            """Initialize the view and send the response to the user."""
            super().__init__(timeout=3600)
            self._config = config
            self._interaction = respond_to
            # Add view items based on config entries
            for entry in config.entries():
                item: Item
                match entry.validator:
                    case parserutil.BOOL_PARSER:
                        # Create toggle button
                        item = Button(
                            custom_id=entry.name,
                            label=_prettify(entry.name),
                            style=(ButtonStyle.green if entry.value
                                   else ButtonStyle.red),
                            emoji=("✅" if entry.value else "❎"))
                        item.callback = functools.partial(
                            self._bool_callback, entry.name)
                        entry.when_changed(functools.partial(
                            self._toggle_bool_button, item))
                    case parserutil.EnumParser():
                        # Create select box for the available options
                        enum = entry.validator.enum
                        # Put spaces between words and make non-plural
                        enum_name = _prettify(enum.__name__).removesuffix("s")
                        # English moment
                        grammer = "n" if enum_name[0] in "aeiou" else ""
                        item = Select(
                            custom_id=entry.name,
                            placeholder=f"Select a{grammer} {enum_name}...",
                            min_values=1,
                            max_values=1,
                            options=[
                                SelectOption(
                                    label=_prettify(name),
                                    value=name,
                                    description=_stringify(value.value),
                                    # Selected if this value is the
                                    # currently selected value
                                    default=(value == entry.value))
                                for name, value in enum.__members__.items()])
                        item.callback = functools.partial(
                            self._enum_callback, entry.name)
                    case _:
                        # Anything without a specific parser yet
                        # Create button to open text modal
                        item = Button(
                            custom_id=entry.name,
                            label=_prettify(entry.name),
                            style=ButtonStyle.gray,
                            emoji="📝")
                        item.callback = functools.partial(
                            self._text_callback, entry.name)
                self.add_item(item)

        async def send(self):
            """Send message containing the config view to the user."""
            disply_name = self._config.get_value(GamemodeConfig.DISPLAY_NAME)
            # Send view to user
            self._msg = await self._interaction.response.send_message(
                embed=Embed(
                    color=Color.from_rgb(0, 200, 200),
                    title=f"Editing config for {disply_name} "
                          f"({self._config.name()}):",
                    fields=[
                        EmbedField(
                            _prettify(entry.name), entry.description)
                        for entry in self._config.entries()]
                ),
                view=self,
                ephemeral=True)

        def _toggle_bool_button(self, button: Button, old_value: bool,
                                new_value: bool):
            button.style = (ButtonStyle.green if new_value
                            else ButtonStyle.red)
            button.emoji = ("✅" if new_value else "❎")
            self._config.task_handler(self._update())

        async def _bool_callback(self, key: str, interaction: Interaction):
            await self._callback(key, not self._config.get_value(key), interaction)

        async def _enum_callback(self, key: str, interaction: Interaction):
            select: Select = self.get_item(key)
            value = self._config.get_option(key).parse(select.values[0])
            if isinstance(value, ValueError):
                # Error parsing enum, should be impossible
                await interaction.response.send_message(
                    embed=Embed(
                        title=f"Invalid value for {_prettify(key)}",
                        description=f"{'. '.join(value.args)}",
                        color=Color.from_rgb(255, 0, 0)),
                    ephemeral=True,
                    delete_after=60)
                return
            await self._callback(key, value, interaction)

        async def _text_callback(self, key: str, interaction: Interaction):
            await interaction.response.send_modal(self.TextEditorModal(
                self, self._config.get_option(key)))

        async def _callback(self, key: str, value, interaction: Interaction):
            self._config.set_value(key, value)
            await interaction.response.send_message(
                embed=Embed(
                    title=f"Set value for {_prettify(key)}",
                    description=f"Successfully set value to "
                                f"{_stringify(value)}",
                    color=Color.from_rgb(0, 255, 0)),
                ephemeral=True,
                delete_after=60)

        async def _update(self):
            # Send changes in view to user
            self._interaction.client.loop.create_task(
                self._interaction.edit_original_response(view=self))

    def __init__(self, path: Path, guild_id: int,
                 task_handler: Callable[[Coroutine | Callable], None],
                 reload: Callable[[], None]):
        """Create server manager for guild {guild_id} in {path}."""
        super().__init__(task_handler)
        self.sync_discord_commands = reload
        self.path = path
        self.id = guild_id
        self.gamemodes: dict[str, GamemodeConfig] = {}
        self.running_games: list[Game] = []
        # Init /play command
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
        # Init /config commands
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
        # Make name safe to use in file names, etc
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
                    self.gamemodes[child.stem].check_file_changes().wait()
        self.sync_command_choices()

    def load_defaults(self, default_configs: Iterable[Path]) -> None:
        """Place default config files into a server."""
        if self.state != ResourceManager.State.READY or not self.path.exists():
            if not self.path.exists():
                self.path.mkdir()
            for file in default_configs:
                new_path = self.path.joinpath(
                    file.relative_to(self.path.parent))
                shutil.copy(file, new_path)
                cfg = GamemodeConfig(new_path, self.task_handler)
                self.gamemodes[file.stem] = cfg
            self.sync_command_choices()
            self.state = ResourceManager.State.READY

    def sync_command_choices(self) -> None:
        """Update the gamemode options in the discord commands."""
        options = [OptionChoice(name) for name, cfg in self.gamemodes.items()]
        self.play_command.options[0].choices = options
        self.config_edit_command.options[0].choices = options

    def add_command_to(self, bot: ApplicationCommandMixin) -> None:
        """Add the discord commands to the bot."""
        bot.add_application_command(self.play_command)
        bot.add_application_command(self.config_command)

    def remove_command_from(self, bot: ApplicationCommandMixin) -> None:
        """Remove the discord commands from the bot."""
        bot.remove_application_command(self.play_command)
        bot.remove_application_command(self.config_command)

    async def _play_from_select(self, inter: Interaction,
                                *args):
        # Callback for GamemodeSelectView
        await inter.delete_original_response()
        await self.play(*args)

    async def play(self, ctx: ApplicationContext | Interaction,
                   gamemode: str | None):
        """Start a game of hangman in the given context."""
        if gamemode is None:
            # Open gamemode selector UI (GamemodeSelectView)
            if isinstance(ctx, Interaction):
                self.logger.error(f"Selector called play with no value")
                return
            view = ServerManager.GamemodeSelectorView(
                self, functools.partial(self._play_from_select,
                                              ctx.interaction))
            await ctx.send_response(
                embed=Embed(
                    title=ServerManager._SELECT_GAMEMODE_MSG,
                    color=Color.from_rgb(0, 255, 0)
                ),
                view=view,
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
                            name=config.get_value(GamemodeConfig.DISPLAY_NAME)
                                + f" ({name})",
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

        # Start game
        gamemode_config = self.gamemodes[gamemode]
        # Make sure config is up to date before starting game
        gamemode_config.check_file_changes().wait()
        game_ctor: type[Game] = gamemode_config.get_value(
            GamemodeConfig.GAME_TYPE).value
        game = game_ctor(gamemode_config, self.task_handler)
        self.running_games.append(game)
        await game.run(interaction)

    async def new_gamemode(self, ctx: ApplicationContext, name: str):
        """Create a new hangman gamemode."""
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
                ephemeral=True)
            return
        cfg = GamemodeConfig(
            self.path.joinpath(f"./{name}.txt"), self.task_handler)
        cfg.set_value(GamemodeConfig.DISPLAY_NAME, display_name)
        self.gamemodes[name] = cfg
        self.sync_discord_commands()
        await self.edit_gamemode(ctx, name)

    async def edit_gamemode(self, ctx: ApplicationContext | Interaction,
                            name: str | None):
        """Modify an existing hangman gamemode."""
        if name is None:
            if isinstance(ctx, Interaction):
                self.logger.error(f"Selector called edit with no value")
                return
            # Gamemode not selected, send gamemode selector
            await ctx.send_response(
                embed=Embed(
                    title=ServerManager._SELECT_GAMEMODE_MSG,
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
        view = ServerManager.GamemodeEditorView(
            self.gamemodes[name], interaction)
        await view.send()

    async def update(self, msg: Message, bot: Bot):
        """Update any running games when a message is sent."""
        now = datetime.datetime.utcnow()
        for game in self.running_games:
            await game.update(msg, bot)
            # TODO: make three day timeout configurable
            if (game.state == Game.State.COMPLETE or
                    now - game.started > datetime.timedelta(days=3)):
                await game.close()
                self.running_games.remove(game)
