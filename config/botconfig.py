from .config import Config
from parserutil import ParserUtil


class BotConfig(Config):
    # TODO: phase these out, move to gamemode system
    GAMEMODES_DIR = "gamemodes_directory"
    DISCORD_TOKEN = "discord_token"
    DICTIONARY_LOCATION = "dictionary_location"
    NUMBER_LIVES = "number_of_lives"

    def _add_config_options(self):
        self._add_config_option(
            BotConfig.GAMEMODES_DIR,
            ParserUtil.STRING_PARSER,
            "Directory to load gamemode configs from",
            "./gamemodes/"
        )
        self._add_config_option(
            BotConfig.DISCORD_TOKEN,
            ParserUtil.STRING_PARSER,
            "Token for the discord bot",
            "<TOKEN>"
        )
        self._add_config_option(
            BotConfig.DICTIONARY_LOCATION,
            ParserUtil.STRING_LIST_PARSER,
            "Path to the word list the game uses",
            ["./words.txt", "./words_alpha.txt", "-./profanity-list.txt", "-./word-blacklist.txt"]
        )
        self._add_config_option(
            BotConfig.NUMBER_LIVES,
            ParserUtil.INT_PARSER,
            "Number of lives the player has",
            8
        )