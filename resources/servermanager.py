import os
from pathlib import Path
from typing import Callable

from logger import Logger
import resources.config as config
from resources.resourcemanager import ResourceManager
from resources.serverconfigmanager import ServerConfigManager
import hangmanbot

class ServerManager(ResourceManager):
    """Resource manager to handle all resources for all servers in the
    servers config dirs."""
    logger = Logger("ServerManager")

    def __init__(self, bot: 'hangmanbot.HangmanBot',
            file_path_provider:  Callable[[], str]):
        super().__init__()
        self.file_path = file_path_provider
        self.servers: dict[int, ServerConfigManager] = {}
        self.default_configs: list[config.GamemodeConfig] = []

    def reload_inner(self):
        """
        Reload all servers' configs

        Should never be called outside of bot first init,
        call the respective server's ConfigManager itself
        """
        # Close all old resources
        for key in self.servers.keys():
            self.servers.pop(key).close()
        # Make sure root configs dir exists
        root = Path(self.file_path())
        os.makedirs(root, exist_ok=True)
        # Iterate children
        for child in root.iterdir():
            if child.is_dir() and child.name.isnumeric():
                # Guild subdirectory
                guild = int(child.name)
                self.servers[guild] = ServerConfigManager(child, guild)
            elif child.is_file():
                # File in root dir, treat as config for default gamemode
                # TODO: Config should accept Path not str
                self.default_configs.append(
                    config.GamemodeConfig(child.absolute()))
            else:
                # Not supported yet.
                pass
