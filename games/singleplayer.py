"""Class for the singleplayer gamemode."""

from typing import Callable, Coroutine

from discord import Bot, Interaction, Message

import resources.config as cfg
from wordproviders import RandomWordProvider
from games.game import Game
from discord.utils import escape_markdown


class SingleplayerGame(Game):
    """
    Represents an ongoing game with a single word and life count.

    Slight misnomer, as multiple people can play the game, but they are
    all treated as the same player with the same life count, guessing
    the same word, etc.
    """

    def __init__(self, config: 'cfg.GamemodeConfig',
                 task_handler: Callable[[Coroutine], None]):
        """Initialise the game from the given config."""
        super().__init__(config, task_handler)
        # When word_list is updated, update random provider
        config.get_option(cfg.GamemodeConfig.WORD_LIST).when_changed(
            self._on_word_list_change)
        word_list = self.config.get_value(cfg.GamemodeConfig.WORD_LIST)
        self.random = RandomWordProvider(word_list)
        self.word = self.random.get_word()
        self.lives = self.config.get_value(cfg.GamemodeConfig.NUMBER_LIVES)
        self.guesses = 0
        self.guessed = []
        self.progress = ["_"] * len(self.word)

    def _on_word_list_change(self, _, new_list):
        self.random.word_list = new_list

    async def _update_inner(self, msg: Message, bot: Bot):
        guess = msg.content.lower().strip()
        await self._handle_guess(guess, msg)
        await self.channel.send(escape_markdown(" ".join(self.progress))
                                + f"\nYou have {self.lives} lives remaining.")
        self.lives = max(self.lives, 0)
        # Game end conditions
        if "_" not in self.progress:
            await self.channel.send(f"You WON in {self.guesses} guesses!")
            self.state = Game.State.COMPLETE
        if self.lives <= 0:
            await self.channel.send(f"You LOST! The word was: "
                                    f"{self.word.upper()}")
            self.state = Game.State.COMPLETE

    async def _handle_guess(self, guess: str, msg: Message):
        if not guess.isalpha():
            await msg.reply(f"Your guess '{guess}' should only contain "
                            f"letters",
                            mention_author=False)
            return
        if len(guess) == 1:
            # Single letter guess
            if guess in self.guessed:
                await msg.reply(f"You have already guessed '{guess.upper()}', "
                                f"try another letter.",
                                mention_author=False)
                return
            self.guesses += 1
            self.guessed.append(guess)
            if guess in self.word:
                await msg.reply(f"The letter '{guess.upper()}' is in "
                                f"the word!",
                                mention_author=False)
                # Replace all instances of letter
                for i in range(len(self.word)):
                    if self.word[i] == guess:
                        self.progress[i] = guess.upper()
            else:
                await msg.reply(f"The letter '{guess.upper()}' is not "
                                f"in the word",
                                mention_author=False)
                self.lives -= 1
        else:
            if len(guess) > len(self.word):
                await msg.reply(f"Guess '{guess}' cannot be longer "
                                f"than word ({len(self.word)} letters)",
                                mention_author=False)
                return
            self.guesses += 1
            full_word = len(guess) == len(self.word)
            if guess in self.word:
                # Full word guess
                if full_word:
                    await msg.reply(f"Correct, the word was "
                                    f"'{self.word.upper()}'!",
                                    mention_author=False)
                    self.progress = list(self.word.upper())
                else:
                    await msg.reply(f"The sequence '{guess.upper()}' "
                                    f"is in the word!",
                                    mention_author=False)
                    # Replace all instances of each char in guess
                    for char in guess:
                        self.guessed.append(char)
                        for i in range(len(self.word)):
                            if self.word[i] == char:
                                self.progress[i] = char.upper()
            else:
                await msg.reply(
                    "The word "
                    + ('is not' if full_word else 'does not contain')
                    + f" '{guess.upper()}'!",
                    mention_author=False)
                self.lives -= len(guess)

    async def run(self, ctx: Interaction):
        """Run the game."""
        await super().run(ctx)
        await self.channel.send(escape_markdown(" ".join(self.progress)))
        await self.channel.send(f"You have {self.lives} lives.")
