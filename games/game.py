from abc import ABC, abstractmethod
from typing import Callable, Coroutine
from discord import ApplicationContext, Bot, Interaction, Member, Message, PartialMessageable, TextChannel, User

import resources.config as cfg
from logger import Logger


class Game(ABC):
    logger = Logger("Game")

    def __init__(self, config: 'cfg.GamemodeConfig',
                 task_handler: Callable[[Coroutine], None]):
        self.config = config
        self.task_handler = task_handler
        self.channel: PartialMessageable | None = None
        self.user: User | Member | None = None

    async def update(self, msg: Message, bot: Bot):
        if self.channel is None or msg.channel.id != self.channel.id:
            return
        if msg.author.id == bot.user.id:
            return
        await self._update_inner(msg, bot)

    @abstractmethod
    async def _update_inner(self, msg: Message, bot: Bot):
        self.logger.debug(f"Game received message: {msg.content}")

    async def run(self, ctx: Interaction):
        msg = await ctx.response.send_message(
            f"Starting game of {self.config.name()} hangman")
        if self.config.get_value(cfg.GamemodeConfig.CREATE_THREAD):
            self.channel = await (await ctx.original_response()).create_thread(
                name=f"Hangman ({self.config.name()} mode)")
        else:
            self.channel = ctx.channel
        self.user = ctx.user
