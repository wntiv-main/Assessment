"""Class representing an ongoing game object."""

from abc import ABC, abstractmethod
from typing import Callable, Coroutine
from discord import (ApplicationContext, Bot, Interaction, Member, Message,
                     PartialMessageable, TextChannel, User)

import resources.config as cfg
from logger import Logger


class Game(ABC):
    """Represents an ongoing game of hangman."""
    logger = Logger()

    def __init__(self, config: 'cfg.GamemodeConfig',
                 task_handler: Callable[[Coroutine], None]):
        """Initialise the game object with a config."""
        self.config = config
        self.task_handler = task_handler
        self.channel: PartialMessageable | None = None
        self.user: User | Member | None = None

    async def update(self, msg: Message, bot: Bot):
        """Handle message that *may* affect the game state."""
        # Message is not in game channel, ignore
        if self.channel is None or msg.channel.id != self.channel.id:
            return
        # Message is sent by bot, ignore
        if msg.author.id == bot.user.id:
            return
        # Game only accepts guesses from the user who started the game
        if (self.config.get_value(cfg.GamemodeConfig.GUESSERS)
            != cfg.GamemodeConfig.Publicity.PUBLIC
            and msg.author.id != self.user.id):
            return
        await self._update_inner(msg, bot)

    @abstractmethod
    async def _update_inner(self, msg: Message, bot: Bot):
        self.logger.debug(f"Game received message: {msg.content}")

    async def run(self, ctx: Interaction):
        """Initialise and set up the game."""
        msg = await ctx.response.send_message(
            f"Starting game of {self.config.name()} hangman")
        if self.config.get_value(cfg.GamemodeConfig.CREATE_THREAD):
            self.channel = await (await ctx.original_response()).create_thread(
                name=f"Hangman ({self.config.name()} mode)")
        else:
            self.channel = ctx.channel
        self.user = ctx.user
