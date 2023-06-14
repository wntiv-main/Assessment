from abc import ABC, abstractmethod
import random
from resources.wordlistmanager import WordListManager


class WordProvider(ABC):
    """Something that can provide a word"""
    @abstractmethod
    def get_word(self) -> str:
        """Return a word"""
        pass

class RandomWordProvider(WordProvider):
    def __init__(self, word_list: WordListManager) -> None:
        self.word_list = word_list

    def get_word(self):
        """Provide a random word from the list"""
        # Make sure we are ready
        self.word_list.on_ready().wait()
        return random.choice(self.word_list.words)