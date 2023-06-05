import resources.config as config
from logger import Logger
from resources.resourcemanager import ResourceManager

from discord import Guild

import os
import pathlib
import shutil
from typing import Callable, Iterable, Mapping


class GamemodeConfigsManager(ResourceManager):
    """Resource Manager for the gamemode configs directory,
    which handles the configs for every single gamemode in
    every single server.
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

    def reload_inner(self):
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