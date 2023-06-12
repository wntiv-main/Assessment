from pathlib import Path

from resources.config.config import Config
from parserutil import ParserUtil


class BotConfig(Config):
    """Config options for the discord bot"""
    GAMEMODES_DIR = "gamemodes_directory"
    DISCORD_TOKEN = "discord_token"

    def _add_config_options(self):
        self._add_config_option(
            BotConfig.GAMEMODES_DIR,
            ParserUtil.PATH_PARSER,
            "Directory to load gamemode configs from",
            Path("./config/")
        )
        self._add_config_option(
            BotConfig.DISCORD_TOKEN,
            ParserUtil.STRING_PARSER,
            "Token for the discord bot",
            "<TOKEN>"
        )