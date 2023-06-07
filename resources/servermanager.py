import os
from pathlib import Path
from typing import Callable

from discord import SlashCommand

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
        self._bot = bot
        self._file_path = file_path_provider
        self._servers: dict[int, ServerConfigManager] = {}
        self._default_configs: list[config.GamemodeConfig] = []

    def reload_inner(self):
        """
        Reload all servers' configs

        Should never be called outside of bot first init,
        call the respective server's ConfigManager itself
        """
        # Close all old resources
        for key in self._servers.keys():
            self._servers.pop(key).remove_command_from(self._bot)
        # Make sure root configs dir exists
        root = Path(self._file_path())
        os.makedirs(root, exist_ok=True)
        # Iterate children
        for child in root.iterdir():
            if child.is_dir() and child.name.isnumeric():
                # Guild subdirectory
                guild = int(child.name)
                manager = ServerConfigManager(child, guild)
                manager.add_command_to(self._bot)
                self._servers[guild] = manager
                manager.reload()
            elif child.is_file():
                # File in root dir, treat as config for default gamemode
                self._default_configs.append(config.GamemodeConfig(child))
            else:
                # Not supported yet.
                pass
        self._bot.sync_commands()
