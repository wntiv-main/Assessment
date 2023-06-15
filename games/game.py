"""Class representing an ongoing game object."""

from abc import ABC, abstractmethod
import datetime
from enum import IntEnum
from typing import Callable, Coroutine
from discord import (Bot, Interaction, Member, Message, PartialMessageable,
                     Thread, User)

import resources.config as cfg
from logger import Logger


class Game(ABC):
    """Represents an ongoing game of hangman."""

    logger = Logger()

    class State(IntEnum):
        """The running state of the game."""

        READY = 0
        RUNNING = 1
        COMPLETE = 2

    def __init__(self, config: 'cfg.GamemodeConfig',
                 task_handler: Callable[[Coroutine], None]):
        """Initialise the game object with a config."""
        self.config = config
        self.task_handler = task_handler
        self.state = Game.State.READY
        self.started = datetime.datetime.utcnow()
        self.channel: PartialMessageable | None = None
        self.user: User | Member | None = None

    async def run(self, ctx: Interaction):
        """Initialise and set up the game."""
        self.state = Game.State.RUNNING
        display_name = self.config.get_value(cfg.GamemodeConfig.DISPLAY_NAME)
        self.user = ctx.user
        await ctx.response.send_message(f"Starting game of {display_name} "
                                        f"hangman")
        if self.config.get_value(cfg.GamemodeConfig.CREATE_THREAD):
            # Create thread
            response = await ctx.original_response()
            self.channel = await response.create_thread(
                name=f"Hangman ({display_name} mode)")
            await self.channel.add_user(self.user)
        else:
            self.channel = ctx.channel

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
        pass

    async def close(self):
        """Clean up after game has ended."""
        if isinstance(self.channel, Thread):
            # If thread, run the configured thread closing action
            action = self.config.get_value(
                cfg.GamemodeConfig.CLOSE_THREAD_ACTION)
            # Newer Python functionality: match statement, not supported
            # by PEP8 checker (https://www.codewof.co.nz/style/python3/)
            match action:
                case cfg.GamemodeConfig.ClosingThreadActions.NOTHING:
                    pass
                case cfg.GamemodeConfig.ClosingThreadActions.ARCHIVE:
                    await self.channel.archive()
                case cfg.GamemodeConfig.ClosingThreadActions.LOCK:
                    await self.channel.archive(True)
                case cfg.GamemodeConfig.ClosingThreadActions.DELETE:
                    await self.channel.delete()
                case _:
                    self.logger.error(
                        f"Unexpected value for "
                        f"{cfg.GamemodeConfig.CLOSE_THREAD_ACTION}, "
                        f"doing nothing")
                    # Set config value to nothing to avoid spamming
                    # error in future calls to this gamemode
                    self.config.set_value(
                        cfg.GamemodeConfig.CLOSE_THREAD_ACTION,
                        cfg.GamemodeConfig.ClosingThreadActions.NOTHING)
