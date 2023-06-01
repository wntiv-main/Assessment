from enum import IntEnum

import config as cfg
from wordproviders import RandomWordProvider
from .game import Game


class Player:
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
        print(" ".join(self.progress))
    def turn(self):
        self.output_progress()
        while guess := input("Enter your guess: ").strip().lower():
            if not guess.isalpha(): 
                print(f"Your guess '{guess}' should only contain letters")
                continue
            if len(guess) == 1:
                if guess in self.guessed:
                    print(f"You have already guessed '{guess.upper()}', try another.")
                    continue
                self.guessed.append(guess)
                if guess in self.word:
                    print(f"The letter '{guess.upper()}' is in the word!")
                    for i in range(len(self.word)):
                        if self.word[i] == guess:
                            self.progress[i] = guess.upper()
                    if "_" not in self.progress:
                        self.output_progress()
                        self.state = Player.State.WON
                else:
                    print(f"The letter '{guess.upper()}' is not in the word!")
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = Player.State.DEAD
                break


class SingleplayerGame(Game):
    def __init__(self, config: 'cfg.GamemodeConfig'):
        super().__init__(config)
        self.random = RandomWordProvider(lambda: self.config.get_value(cfg.GamemodeConfig.DICTIONARY_LOCATION))
        
        self.player = Player(self.random.get_word(), self.config.get_value(cfg.GamemodeConfig.NUMBER_LIVES))

    def run(self):
        while self.player.state == Player.State.PLAYING:
            self.player.turn()
            self.config.check_file_changes()
        match self.player.state:
            case Player.State.WON:
                print("YOU WIN!!!")
            case Player.State.DEAD:
                print(f"YOU LOST! The word was '{self.player.word}'")