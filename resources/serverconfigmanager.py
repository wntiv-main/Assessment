import os
import pathlib
from pathlib import Path
import shutil
from typing import Callable, Iterable, Mapping

from discord import (
    ApplicationContext, Color, Embed, EmbedField, Guild, Option, OptionChoice,
    SlashCommand, ApplicationCommandMixin
)
from games.game import Game
import resources.config as config
from logger import Logger
from resources.resourcemanager import ResourceManager


class ServerConfigManager(ResourceManager):
    logger = Logger("ServerConfigManager")

    def __init__(self, path: Path, guild_id: int):
        super().__init__()
        self.path = path
        self.id = guild_id
        self.gamemodes: dict[str, config.GamemodeConfig] = {}
        self.play_command = SlashCommand(
            self.play,
            name="play",
            description="Start a game of hangman!",
            guild_ids=[self.id],
            guild_only=True,
            options=[Option(
                str,
                name="gamemode",
                description="The gamemode you want to play",
                choices=[]
            )]
        )

    def _reload_inner(self):
        # Recursive walk of dir tree
        for child in self.path.rglob("*"):
            # Only open config files
            if child.is_file():
                if child.stem not in self.gamemodes:
                    # New files in dir
                    self.gamemodes[child.stem] = config.GamemodeConfig(child)
                else:
                    # Changes to old files in dir
                    self.gamemodes[child.stem].check_file_changes()
                    # Deleted files in dir
                    if (self.gamemodes[child.stem].state
                        == ResourceManager.State.REMOVED):
                        del self.gamemodes[child.stem]
        self.play_command.options[0].choices = [
            OptionChoice(name, cfg.get_value(
                config.GamemodeConfig.DESCRIPTION))
            for name, cfg in self.gamemodes.items()]
    
    def load_defaults(self, default_configs: Iterable[Path]):
        if self.state != ResourceManager.State.READY or not self.path.exists():
            self.path.mkdir()
            for file in default_configs:
                new_path = self.path.joinpath(file)
                shutil.copy(file.absolute(), new_path)
                cfg = config.GamemodeConfig(new_path)
                self.gamemodes[file.stem] = cfg
            self.play_command.options[0].choices = [
                OptionChoice(name, cfg.get_value(
                    config.GamemodeConfig.DESCRIPTION))
                for name, cfg in self.gamemodes.items()]
            self.state = ResourceManager.State.READY

    def add_command_to(self, bot: ApplicationCommandMixin):
        bot.add_application_command(self.play_command)

    def remove_command_from(self, bot: ApplicationCommandMixin):
        bot.remove_application_command(self.play_command)

    async def play(self, ctx: ApplicationContext, gamemode: str):
        if gamemode not in self.gamemodes:
            await ctx.send(
                embed=Embed(
                    title="Invalid option!",
                    description="That gamemode doesn't exist (yet). "
                    "Please try again, or if you think that this is "
                    "an error, contact an administrator. Valid "
                    "options are:",
                    color=Color.from_rgb(255, 0, 0),
                    fields=[
                        EmbedField(
                            name=name,
                            value=config.get_value(
                                config.GamemodeConfig.DESCRIPTION)
                        )
                        for name, config in self.gamemodes.items()
                    ],
                )
            )
            return
        gamemode_config = self.gamemodes[gamemode]
        # Game play...
        game_ctor: type[Game] = gamemode_config.get_value(
            config.GamemodeConfig.GAME_TYPE).value
        game = game_ctor(gamemode)
        # TODO: game.run()


# TODO: REMOVE
class GamemodeConfigsManager(ResourceManager):
    """Resource Manager for the gamemode configs directory, which
    handles the configs for every single gamemode in a server.
    """
    logger = Logger("GamemodesConfigManager")

    def __init__(self, file_path_provider: Callable[[], str],
            on_update_config: Callable[
                [int, Mapping[str, 'config.GamemodeConfig']], None]):
        super().__init__()
        self.file_path = file_path_provider
        self.gamemodes: Mapping[str, Mapping[str, config.GamemodeConfig]] = {}
        self.path_cache = None
        self.update_config_callback = on_update_config

    def _reload_inner(self):
        root = self.path_cache = pathlib.Path(self.file_path())
        os.makedirs(root, exist_ok=True)
        for path, subdirs, files in os.walk(root.absolute()):
            path = pathlib.Path(path).relative_to(root.absolute())
            # If in root dir, is a default gamemode added to new guilds
            if not path.parts:
                guild = "default"
            else:
                guild = path.parts[0]
            self.logger.debug(f"Walked to {path} (guild {guild}),"\
                              f" has {files}")
            # Load all config files in dir
            for file in files:
                full_path = pathlib.Path(root, path, file)
                name = os.path.basename(full_path.stem)
                cfg = config.GamemodeConfig(full_path)
                if guild not in self.gamemodes:
                    self.gamemodes[guild] = {}
                self.gamemodes[guild][name] = cfg
            if guild != "default":
                self.update_config_callback(int(guild), self.gamemodes[guild])

    def init_for_guilds(self, guilds: Iterable[Guild]):
        """Initialize potentially new guilds with a config folder
        filled with any existing default gamemode configs.
        """
        self.hook_ready()
        for guild in guilds:
            guild_id = str(guild.id)
            path = self.path_cache.joinpath(f"./{guild_id}")
            if not path.exists():
                self.logger.info(f"Initializing for {guild_id} with default"\
                                 f" gamemodes")
                # Create dir and init with default gamemodes
                self.gamemodes[guild_id] = {}
                path.mkdir()
                for file in self.path_cache.iterdir():
                    if file.is_file():
                        new_path = pathlib.Path(self.path_cache, guild_id,
                                                file.name)
                        shutil.copy(file.absolute(), new_path.absolute())
                        name = os.path.basename(file.stem)
                        cfg = config.GamemodeConfig(new_path)
                        self.gamemodes[guild_id][name] = cfg
                        self.update_config_callback(guild_id, name, cfg)