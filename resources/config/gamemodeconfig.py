"""Config manager for a hangman gamemode."""

from enum import IntEnum
from resources.config.config import Config
from parserutil import ParserUtil
import games
from resources.wordlistmanager import WordListManager

_GUESSERS_MSG = """
Can all users guess or only the user who started the game?

Valid options:
private - (default) Only the user who started the game can guess
public - Any user can guess
"""

_CLOSE_THREAD_MSG = """
What should happen to the thread when the game is over?
Only applies if create_thread is true.

Valid options:
nothing - Do nothing
archive - Archive the thread, removing it from the sidebar UI
lock - (default) Lock the thread, archiving it and preventing further
       messages from being sent in it.
delete - Delete the thread. WARNING: This action is irreversible
"""


class GamemodeConfig(Config):
    """Config manager for a hangman gamemode."""

    class Publicity(IntEnum):
        """Enum representing the level of publicity."""

        PRIVATE = 0
        PUBLIC = 1

    class ClosingThreadActions(IntEnum):
        """Enum of actions to be performed when closing a thread."""

        NOTHING = 0
        ARCHIVE = 1
        LOCK = 2
        DELETE = 3

    DISPLAY_NAME = "display_name"
    GAME_TYPE = "gamemode"
    DESCRIPTION = "description"
    NUMBER_LIVES = "number_of_lives"
    WORD_LIST = "word_list_paths"
    CREATE_THREAD = "create_thread"
    CLOSE_THREAD_ACTION = "close_thread_action"
    GUESSERS = "guessers"

    def _add_config_options(self):
        self._add_config_option(
            GamemodeConfig.DISPLAY_NAME,
            ParserUtil.STRING_PARSER,
            "Displayed name of this gamemode",
            "Hangman"
        )
        self._add_config_option(
            GamemodeConfig.GAME_TYPE,
            ParserUtil.EnumParser(games.Gamemode),
            "Gamemode this game should be",
            games.Gamemode.SINGLEPLAYER
        )
        self._add_config_option(
            GamemodeConfig.DESCRIPTION,
            ParserUtil.STRING_PARSER,
            "Description of gamemode (shown in discord UI)",
            "Just hangman"
        )
        self._add_config_option(
            GamemodeConfig.NUMBER_LIVES,
            ParserUtil.INT_PARSER,
            "Number of lives the player has",
            8
        )
        self._add_config_option(
            GamemodeConfig.WORD_LIST,
            ParserUtil.WORD_LIST_PARSER,
            "Paths to the word lists the game uses",
            WordListManager("./words.txt"
                            "|./words_alpha.txt"
                            "|-./profanity-list.txt"
                            "|-./word-blacklist.txt",
                            self.task_handler)
        )
        self._add_config_option(
            GamemodeConfig.CREATE_THREAD,
            ParserUtil.BOOL_PARSER,
            "Whether or not a thread should be created to play the game",
            True
        )
        self._add_config_option(
            GamemodeConfig.CLOSE_THREAD_ACTION,
            ParserUtil.EnumParser(GamemodeConfig.ClosingThreadActions),
            _CLOSE_THREAD_MSG,
            GamemodeConfig.ClosingThreadActions.LOCK
        )
        self._add_config_option(
            GamemodeConfig.GUESSERS,
            ParserUtil.EnumParser(GamemodeConfig.Publicity),
            _GUESSERS_MSG,
            GamemodeConfig.Publicity.PRIVATE
        )
