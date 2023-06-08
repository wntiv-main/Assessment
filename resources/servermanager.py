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
    """
    Resource manager to handle all resources for all servers in the
    servers config dirs.
    """
    logger = Logger("ServerManager")

    def __init__(self, bot: 'hangmanbot.HangmanBot',
            file_path_provider:  Callable[[], Path]):
        super().__init__()
        self._bot = bot
        self._file_path = file_path_provider
        self._servers: dict[int, ServerConfigManager] = {}
        self.default_configs: list[Path] = []

    def _reload_inner(self):
        """
        Reload all servers' configs

        Should never be called outside of bot first init,
        call the respective server's ConfigManager itself
        """
        # Close all old resources
        for key in self._servers.keys():
            self._servers.pop(key).remove_command_from(self._bot)
        for guild in self._bot.guilds:
            self.new_guild(guild.id)
        # Make sure root configs dir exists
        root = self._file_path()
        os.makedirs(root, exist_ok=True)
        # Iterate children
        for child in root.iterdir():
            if child.is_dir() and child.name.isnumeric():
                # Guild subdirectory
                if self._bot.get_guild(int(child.name)) is not None:
                    guild = int(child.name)
                    manager = ServerConfigManager(child, guild)
                    manager.add_command_to(self._bot)
                    self._servers[guild] = manager
                    manager.reload()
                else:
                    # Guild no longer exists, delete dir
                    self.logger.info(f"Deleting configs for {child.name}")
                    os.remove(child.absolute())
            elif child.is_file() or child.is_dir():
                # File in root dir, treat as config for default gamemode
                self.default_configs.append(child)
            else:
                # Not supported yet.
                pass
        self._bot.sync_commands()

    def reload_for_guild(self, guild_id: int):
        """
        Reload a single guild's config manager.

        Reloads the guild's config manager if found, making sure to keep
        the discord state of the commands in sync.
        """
        if guild_id in self._servers:
            self._servers[guild_id].reload()
            self._bot.sync_commands()

    def new_guild(self, guild_id: int):
        """
        Create a ServerConfigManager for a new guild w defaults.

        Creates a ServerConfigManager for a guild if it isn't already in
        our server list, and initialise it with the default config files
        in the root configs directory.
        """
        if guild_id not in self._servers:
            manager = ServerConfigManager(
                self._file_path().joinpath(f"/{guild_id}"), guild_id)
            manager.load_defaults()
            self._servers[guild_id] = manager
