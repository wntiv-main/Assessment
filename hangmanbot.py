"""Implementation for the actual discord bot."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread
from typing import Callable, Coroutine
from aiohttp import ClientConnectorError
from discord import Bot, Guild, Intents, LoginFailure, Message

import resources.config as cfg
from logger import Logger
from resources.serverlistmanager import ServerListManager


class HangmanBot(Bot):
    """Hangman Discord bot implementation."""

    logger = Logger()

    def __init__(self, config_path: Path):
        """Initialise the bot from a path to a config file."""
        intents = Intents.none()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__("Hangman game for Discord", intents=intents)

        # Stuff for multithreading for resource loading
        self._resources_loop = asyncio.new_event_loop()
        self._tasks = set()
        self._thread = Thread(
            target=self._resources_thread,
            name="Resource Loader")
        self._resources_executor = ThreadPoolExecutor(4, "ResourceLoader")

        self.config = cfg.BotConfig(config_path, self._run_task_on_resources)

        self.server_manager = ServerListManager(
            self,
            lambda: self.config.get_value(cfg.BotConfig.GAMEMODES_DIR),
            self._run_task_on_resources
        )

        self.config.get_option(cfg.BotConfig.GAMEMODES_DIR).when_changed(
            lambda *_: self.server_manager.reload())

    def run(self) -> None:
        """Run the bot. Blocking call."""
        self._thread.start()
        token = self.config.get_value(cfg.BotConfig.DISCORD_TOKEN)
        try:
            super().run(
                token,
                reconnect=True
            )
        except ClientConnectorError as e:
            self.logger.error("Failed to connect to Discord Gateway. "
                              "Do you have internet, or is Discord "
                              "down?",
                              e.strerror)
        except LoginFailure:
            self.logger.error(f"Failed to authenticate with Discord "
                              f"using '{token}' as token. Make sure "
                              f"you are using the correct token (you "
                              f"can change this in config.txt)")

    def _resources_thread(self):
        asyncio.set_event_loop(self._resources_loop)
        self._resources_loop.run_forever()

    def _run_task_on_resources(self, coro: Coroutine | Callable):
        # Run resource loading task
        # Using executor to potentially run multiple tasks concurrently
        if asyncio.iscoroutine(coro):
            self._resources_loop.run_in_executor(
                self._resources_executor,
                asyncio.run,
                coro)
        else:
            self._resources_loop.run_in_executor(
                self._resources_executor,
                coro
            )

    async def on_ready(self):
        """Bot has initialised, load server manager."""
        self.logger.info("Bot is connected to Discord Gateway")
        self.server_manager.reload()

    async def on_guild_join(self, guild: Guild):
        """Update server manager with new server."""
        self.logger.info(f"Joined guild {guild.id}")
        self.server_manager.new_guild(guild.id)

    async def on_message(self, msg: Message):
        """Update server with message that may affect game."""
        await self.server_manager.update_servers(msg, self)
