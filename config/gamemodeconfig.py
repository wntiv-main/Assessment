from config.config import Config
from parserutil import ParserUtil
import games


class GamemodeConfig(Config):
    GAME_TYPE = "gamemode"
    DESCRIPTION = "description"
    COMMAND_COOLDOWN_RATE = "command_cooldown_rate"
    COMMAND_COOLDOWN_PER = "command_cooldown_per"
    NUMBER_LIVES = "number_of_lives"
    WORD_LIST_PATHS = "word_list_paths"

    def _add_config_options(self):
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
            GamemodeConfig.COMMAND_COOLDOWN_RATE,
            ParserUtil.FLOAT_PARSER,
            f"Cooldown (in seconds) that a user must wait before using this "\
            f"command after using it [{GamemodeConfig.COMMAND_COOLDOWN_PER}]"\
            f" times",
            0
        )
        self._add_config_option(
            GamemodeConfig.COMMAND_COOLDOWN_PER,
            ParserUtil.INT_PARSER,
            f"Amount of times a user can use this command before being on "\
            f"cooldown for [{GamemodeConfig.COMMAND_COOLDOWN_RATE}] seconds",
            1
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