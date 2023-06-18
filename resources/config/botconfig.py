"""Config manager for the Hangmen Discord bot."""

from pathlib import Path

from resources.config.config import Config
import parserutil


class BotConfig(Config):
    """Config options for the discord bot."""

    GAMEMODES_DIR = "gamemodes_directory"
    DISCORD_TOKEN = "discord_token"

    def _add_config_options(self):
        self._add_config_option(
            BotConfig.GAMEMODES_DIR,
            parserutil.PATH_PARSER,
            "Directory to load gamemode configs from",
            Path("./config/")
        )
        self._add_config_option(
            BotConfig.DISCORD_TOKEN,
            parserutil.STRING_PARSER,
            "Token for the discord bot",
            "<TOKEN>"
        )
