import config.config
from parserutil import ParserUtil
import games

class GamemodeConfig(config.Config):
    GAME_TYPE = "gamemode"
    DESCRIPTION = "description"
    COMMAND_COOLDOWN = "command_cooldown"
    NUMBER_LIVES = "number_of_lives"
    DICTIONARY_LOCATION = "dictionary_location"

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
            GamemodeConfig.COMMAND_COOLDOWN,
            ParserUtil.INT_PARSER,
            "Cooldown (in seconds) that a user must wait before using this command again",
            0
        )
        self._add_config_option(
            GamemodeConfig.NUMBER_LIVES,
            ParserUtil.INT_PARSER,
            "Number of lives the player has",
            8
        )
        self._add_config_option(
            GamemodeConfig.DICTIONARY_LOCATION,
            ParserUtil.STRING_LIST_PARSER,
            "Path to the word list the game uses",
            ["./words.txt", "./words_alpha.txt", "-./profanity-list.txt", "-./word-blacklist.txt"]
        )