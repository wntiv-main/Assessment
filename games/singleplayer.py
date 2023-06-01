from enum import IntEnum

import config as cfg
from wordproviders import RandomWordProvider
from games.game import Game


class Player:
    """Represents a player"""
    # TODO: rewrite and ise to make multiplayer support etc. cleaner
    class State(IntEnum):
        PLAYING = 0
        WON = 1
        DEAD = 2
    def __init__(self, word, lives):
        self.word = word
        self.lives = lives
        self.progress = ["_"] * len(word)
        self.guessed = []
        self.state = Player.State.PLAYING
    def output_progress(self):
        """Print the unrevealed word with spaces between letters"""
        print(" ".join(self.progress))
    def turn(self):
        """Logic for player to take a turn at guessing their word"""
        self.output_progress()
        guess: str
        while guess := input("Enter your guess: ").strip().lower():
            if not guess.isalpha(): 
                print(f"Your guess '{guess}' should only contain letters")
                continue
            if len(guess) == 1:
                # Single letter guess
                if guess in self.guessed:
                    print(f"You have already guessed '{guess.upper()}',\
                          try another.")
                    continue
                self.guessed.append(guess)
                if guess in self.word:
                    print(f"The letter '{guess.upper()}' is in the word!")
                    for i in range(len(self.word)):
                        if self.word[i] == guess:
                            self.progress[i] = guess.upper()
                    if "_" not in self.progress:
                        self.state = Player.State.WON
                else:
                    print(f"The letter '{guess.upper()}' is not in the word")
                    self.lives -= 1
                break
            else:
                if len(guess) > len(self.word):
                    print(f"Guess '{guess}' cannot be longer than word\
                          ({len(self.word)} letters)!")
                    continue
                full_word = len(guess) == len(self.word)
                if guess in self.word:
                    # Full word guess
                    if full_word:
                        print("Correct!")
                        self.progress = list(self.word.upper())
                        self.state = Player.State.WON
                    else:
                        print(f"The sequence '{guess.upper()}' is in the\
                              word!")
                        for char in guess:
                            self.guessed.append(char)
                            for i in range(len(self.word)):
                                if self.word[i] == char:
                                    self.progress[i] = char.upper()
                else:
                    print("The word",
                          'is not' if full_word else 'does not contain',
                          f"'{guess.upper()}'!")
                    self.lives -= len(guess)
                break
        if "_" not in self.progress:
            self.state = Player.State.WON
        if self.lives <= 0:
            self.state = Player.State.DEAD


class SingleplayerGame(Game):
    """Represents an ongoing singleplayer game"""
    def __init__(self, config: 'cfg.GamemodeConfig'):
        super().__init__(config)
        self.random = RandomWordProvider(
            lambda: self.config.get_value(
                cfg.GamemodeConfig.DICTIONARY_LOCATION))
        self.player = Player(self.random.get_word(),
            self.config.get_value(cfg.GamemodeConfig.NUMBER_LIVES))

    def run(self):
        """Run the game"""
        while self.player.state == Player.State.PLAYING:
            print(f"You have {self.player.lives} lives remaining")
            self.player.turn()
            self.config.check_file_changes()
        match self.player.state:
            case Player.State.WON:
                self.player.output_progress()
                print("YOU WIN!!!")
            case Player.State.DEAD:
                print(f"YOU LOST! The word was '{self.player.word}'")