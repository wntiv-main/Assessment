"""Manager for all servers that the bot has access to."""

import functools
import os
from pathlib import Path
from typing import Callable, Coroutine

from discord import Bot, Message

from logger import Logger
from resources.resourcemanager import ResourceManager
from resources.servermanager import ServerManager
import hangmanbot


class ServerListManager(ResourceManager):
    """Resource manager to handle all resources for all servers."""

    logger = Logger()

    def __init__(
            self, bot: 'hangmanbot.HangmanBot',
            file_path_provider:  Callable[[], Path],
            task_handler: Callable[[Coroutine | Callable], None]):
        """
        Create a manager for a given hangman discord bot.

        Also accepts a provider for the file path that the config files
        for all of the servers should be loaded from and saved to, and
        a task handler to pass to the resource manager.
        """
        super().__init__(task_handler)
        self._bot = bot
        self._file_path = file_path_provider
        self._servers: dict[int, ServerManager] = {}
        self.default_configs: list[Path] = []

    async def _reload_inner(self):
        """
        Reload all servers' configs.

        Should never be called outside of bot first init, instead call
        the respective server's ConfigManager itself.
        """
        # Close all old resources
        for key in tuple(self._servers.keys()):
            self._servers.pop(key).remove_command_from(self._bot)
        # Make sure root configs dir exists
        root = self._file_path()
        os.makedirs(root, exist_ok=True)
        # Iterate children
        for child in root.iterdir():
            if child.is_dir() and child.name.isnumeric():
                # Guild subdirectory
                if self._bot.get_guild(int(child.name)) is not None:
                    guild = int(child.name)
                    self.logger.info(f"Initing configs for guild {guild}")
                    manager = ServerManager(
                        child,
                        guild,
                        self.task_handler,
                        functools.partial(self.reload_for_guild, guild))
                    self._servers[guild] = manager
                    manager.add_command_to(self._bot)
                    # Manual reload to keep on same thread
                    manager.state = ResourceManager.State.INITIALIZING
                    await manager._reload()
                else:
                    # Guild no longer exists, delete dir
                    self.logger.info(f"Deleting configs for {child.name}")
                    os.remove(child.absolute())
            elif child.is_file():
                # File in root dir, treat as config for default gamemode
                self.default_configs.append(child)
            else:
                # Not supported yet.
                pass
        # Initialise any new guilds who have no config dir
        for guild in self._bot.guilds:
            await self.new_guild(guild.id, False)
        # Sync commands with discord
        self._bot.loop.create_task(self._bot.sync_commands())

    def reload_for_guild(self, guild_id: int):
        """
        Reload a single guild's config manager.

        Reloads the guild's config manager if found, making sure to keep
        the discord state of the commands in sync.
        """
        if guild_id in self._servers:
            self._servers[guild_id].reload()
            self._bot.loop.create_task(self._bot.sync_commands(
                check_guilds=[guild_id]))
        elif self._bot.get_guild(guild_id) is not None:
            self.task_handler(self.new_guild(guild_id))

    async def new_guild(self, guild_id: int, update_commands=True):
        """
        Create a ServerConfigManager for a new guild with defaults.

        Creates a ServerConfigManager for a guild if it isn't already in
        our server list, and initialise it with the default config files
        in the root configs directory.
        """
        guild_dir = self._file_path().joinpath(f"./{guild_id}")
        if guild_id not in self._servers:
            manager = ServerManager(
                guild_dir,
                guild_id,
                self.task_handler,
                functools.partial(self.reload_for_guild, guild_id))
            manager.load_defaults(self.default_configs)
            self._servers[guild_id] = manager
            if update_commands:
                self._bot.loop.create_task(
                    self._bot.sync_commands(check_guilds=[guild_id]))
        elif not guild_dir.exists():
            self._servers[guild_id].load_defaults(self.default_configs)
            if update_commands:
                self._bot.loop.create_task(
                    self._bot.sync_commands(check_guilds=[guild_id]))

    async def update_servers(self, msg: Message, bot: Bot):
        """Update the relevant server when a message is received."""
        if msg.guild is not None and msg.guild.id in self._servers:
            await self._servers[msg.guild.id].update(msg, bot)
