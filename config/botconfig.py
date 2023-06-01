from config.config import Config
from parserutil import ParserUtil


class BotConfig(Config):
    GAMEMODES_DIR = "gamemodes_directory"
    DISCORD_TOKEN = "discord_token"

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