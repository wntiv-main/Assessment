from enum import IntEnum
from resources.config.config import Config
from parserutil import ParserUtil
import games


class GamemodeConfig(Config):
    class Publicity(IntEnum):
        PRIVATE = 0
        PUBLIC = 1

    DISPLAY_NAME = "display_name"
    GAME_TYPE = "gamemode"
    DESCRIPTION = "description"
    NUMBER_LIVES = "number_of_lives"
    WORD_LIST_PATHS = "word_list_paths"
    CREATE_THREAD = "create_thread"
    GUESSERS = "guessers"

    def _add_config_options(self):
        self._add_config_option(
            GamemodeConfig.DISPLAY_NAME,
            ParserUtil.EnumParser(games.Gamemode),
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
            GamemodeConfig.WORD_LIST_PATHS,
            ParserUtil.STRING_LIST_PARSER,
            "Paths to the word lists the game uses",
            ["./words.txt", "./words_alpha.txt",
             "-./profanity-list.txt", "-./word-blacklist.txt"]
        )
        self._add_config_option(
            GamemodeConfig.CREATE_THREAD,
            ParserUtil.BOOL_PARSER,
            "Whether or not a thread should be created to play the game",
            True
        )
        self._add_config_option(
            GamemodeConfig.GUESSERS,
            ParserUtil.EnumParser(GamemodeConfig.Publicity),
            "Can all users guess or only the user who started the game",
            GamemodeConfig.Publicity.PRIVATE
        )