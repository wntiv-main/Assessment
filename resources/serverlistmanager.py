from asyncio import AbstractEventLoop
import os
from pathlib import Path
from typing import Callable, Coroutine

from discord import Bot, Message, SlashCommand

from logger import Logger
import resources.config as config
from resources.resourcemanager import ResourceManager
from resources.servermanager import ServerManager
import hangmanbot

class ServerListManager(ResourceManager):
    """
    Resource manager to handle all resources for all servers in the
    servers config dirs.
    """
    logger = Logger("ServerListManager")

    def __init__(self, bot: 'hangmanbot.HangmanBot',
            file_path_provider:  Callable[[], Path],
            task_handler: Callable[[Coroutine], None]):
        super().__init__(task_handler)
        self._bot = bot
        self._file_path = file_path_provider
        self._servers: dict[int, ServerManager] = {}
        self.default_configs: list[Path] = []

    async def _reload_inner(self):
        """
        Reload all servers' configs

        Should never be called outside of bot first init,
        call the respective server's ConfigManager itself
        """
        # Close all old resources
        for key in tuple(self._servers.keys()):
            self._servers.pop(key).remove_command_from(self._bot)
        for guild in self._bot.guilds:
            await self.new_guild(guild.id)
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
                    manager = ServerManager(child, guild,
                                                  self.task_handler)
                    manager.add_command_to(self._bot)
                    self._servers[guild] = manager
                    # Manual reload to keep on same thread
                    manager.state = ResourceManager.State.INITIALIZING
                    await manager._reload()
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
        self._bot.loop.create_task(self._bot.sync_commands())

    def reload_for_guild(self, guild_id: int):
        """
        Reload a single guild's config manager.

        Reloads the guild's config manager if found, making sure to keep
        the discord state of the commands in sync.
        """
        if guild_id in self._servers:
            self._servers[guild_id].reload()
            self.task_handler(self._bot.sync_commands(
                check_guilds=[guild_id]))
        elif self._bot.get_guild(guild_id) is not None:
            self.new_guild(guild_id)

    async def new_guild(self, guild_id: int):
        """
        Create a ServerConfigManager for a new guild w defaults.

        Creates a ServerConfigManager for a guild if it isn't already in
        our server list, and initialise it with the default config files
        in the root configs directory.
        """
        if guild_id not in self._servers:
            manager = ServerManager(
                self._file_path().joinpath(f"/{guild_id}"),
                guild_id,
                self.task_handler)
            manager.load_defaults(self.default_configs)
            self._servers[guild_id] = manager
            self._bot.loop.create_task(
                self._bot.sync_commands(check_guilds=[guild_id]))

    async def update_servers(self, msg: Message, bot: Bot):
        if msg.guild is not None and msg.guild.id in self._servers:
            await self._servers[msg.guild.id].update(msg, bot)
