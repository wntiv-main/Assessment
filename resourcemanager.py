from abc import ABC, abstractmethod
from enum import IntEnum
import os
import shutil
import time
from typing import Callable, Iterable, Mapping
import pathlib

from discord import Guild

from logger import Logger
import config


class ResourceManager(ABC):
    """Class that handles loading and manages a resource"""
    logger = Logger("ResourceManager")

    class State(IntEnum):
        """The state of the resource"""
        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2

    def __init__(self):
        self.state = ResourceManager.State.UNINITIALIZED

    def reload(self):
        """Reload the resource. This is expected to take a long
        time as it may need to perform heavy operations. Consider
        reloading on a seperate thread to the main thread to avoid
        hanging the entire program runtime.
        """
        start_time = time.perf_counter()
        self.state = ResourceManager.State.INITIALIZING
        self.reload_inner()
        self.state = ResourceManager.State.READY
        self.logger.info(f"Reloading resources for "\
                         f"{self.__class__.__name__}, took "\
                         f"{(time.perf_counter() - start_time) * 1000}ms")

    @abstractmethod
    def reload_inner(self):
        """Method that subclasses should override to
        impliment their task.
        """
        pass

    def hook_ready(self):
        """Ensure the resource is ready, if not, wait for it"""
        # For future threading possibility:
        # May need to synchronize and await for resource
        # to finish loading so we can use it
        match self.state:
            case ResourceManager.State.UNINITIALIZED:
                self.reload()
            case ResourceManager.State.INITIALIZING:
                while self.state != ResourceManager.State.READY:
                    pass
            case ResourceManager.State.READY:
                pass


class GamemodeConfigsManager(ResourceManager):
    """Resource Manager for the gamemode configs directory,
    which handles the configs for every single gamemode in
    every single server.
    """
    logger = Logger("GamemodesConfigManager")

    def __init__(self, file_path_provider: Callable[[], str],
            on_new_config: Callable[
                [str, str, 'config.GamemodeConfig'], None]):
        super().__init__()
        self.file_path = file_path_provider
        self.gamemodes: Mapping[str, Mapping[str, config.GamemodeConfig]] = {}
        self.path_cache = None
        self.new_config_callback = on_new_config

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
                    self.new_config_callback(guild, name, cfg)

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
                        self.new_config_callback(guild_id, name, cfg)

