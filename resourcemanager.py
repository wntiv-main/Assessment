from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Callable
import pathlib

from logger import Logger
from config import GamemodeConfig


class ResourceManager(ABC):
    logger = Logger("ResourceManager")
    class State(IntEnum):
        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2

    def __init__(self):
        self.state = ResourceManager.State.UNINITIALIZED

    def reload(self):
        self.logger.info(f"Reloading resources for {self.__class__.__name__}")
        self.state = ResourceManager.State.INITIALIZING
        self.reload_inner()
        self.state = ResourceManager.State.READY

    @abstractmethod
    def reload_inner(self):
        pass

    def hook_ready(self):
        # For future threading possibility:
        # May need to synchronize and await for resource to finish loading so we can use it
        match self.state:
            case ResourceManager.State.UNINITIALIZED:
                self.reload()
            case ResourceManager.State.INITIALIZING:
                while self.state != ResourceManager.State.READY:
                    pass
            case ResourceManager.State.READY:
                pass


class GamemodeConfigsManager(ResourceManager):
    def __init__(self, file_paths_provider: Callable[[], list[str]]):
        super().__init__()
        self.file_paths = file_paths_provider
        self.gamemodes = {}

    def reload_inner(self):
        for config_path in self.file_paths():
            self.gamemodes[pathlib.Path(config_path).name] = GamemodeConfig(config_path)
