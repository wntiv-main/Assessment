import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread
from typing import Coroutine
from discord import Bot, Guild, Intents, Message

import resources.config as cfg
from logger import Logger
from resources.serverlistmanager import ServerListManager


class HangmanBot(Bot):
    """Discord bot implementation"""
    logger = Logger()

    def __init__(self, config_path: Path):
        intents = Intents.none()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__("Hangman game for Discord", intents=intents)

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

    def run(self) -> None:
        """Run the bot. Blocking call."""
        self._thread.start()
        super().run(
            self.config.get_value(cfg.BotConfig.DISCORD_TOKEN),
            reconnect=True
        )

    def _resources_thread(self):
        asyncio.set_event_loop(self._resources_loop)
        self._resources_loop.run_forever()

    def _run_task_on_resources(self, coro: Coroutine):
        self._resources_loop.run_in_executor(
            self._resources_executor,
            asyncio.run,
            coro)

    async def on_ready(self):
        """Called when bot is connected to the Discord Gateway and ready"""
        self.logger.info(f"Bot is connected to Discord Gateway")
        self.server_manager.reload()

    async def on_guild_join(self, guild: Guild):
        self.logger.info(f"Joined guild {guild.id}")
        self.server_manager.new_guild(guild.id)

    async def on_message(self, msg: Message):
        await self.server_manager.update_servers(msg, self)
