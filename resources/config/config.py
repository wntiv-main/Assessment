from abc import ABC, abstractmethod
from io import TextIOWrapper
import os
from pathlib import Path
from typing import Any, Callable

from logger import Logger
from parserutil import ParserUtil
from resources.resourcemanager import ResourceManager


class Config(ResourceManager):
    """
    Class to handle and manage a config file at a specified file
    path using a basic TOML-style config file
    """
    logger = Logger("Config")

    class Entry:
        """Represents an entry within the config file"""
        def __init__(
            self,
            name: str,
            validator: ParserUtil.AbstractParser,
            description: str,
            default_value,
        ):
            self.name = name
            self.validator = validator
            self.description = description
            self.value = default_value
            self.default_value = default_value
            self.notifiers = []

        def when_changed(self, callback: Callable[[str, str], None]):
            """Add a listener for when this option is changed. This is called
            with the old value and the new value as parameters. When called,
            the value of Entry.get_value() for this option will have already
            been changed.
            """
            self.notifiers.append(callback)

        def write(self, file: TextIOWrapper):
            """Write this entry to the supplied file"""
            # TODO: check for already existing line with this config option
            # and handle appropriately
            for line in self.description.split("\n"):
                file.write(f"# {line}\n")
            file.write(f"{self.name}={self.validator.stringify(self.value)}"\
                       f"\n\n")

        def parse(self, value):
            """Parse the given value and check for change"""
            try:
                parsed_value = self.validator.parse(value)
            except ValueError as e:
                # Error parsing, log and use old value
                Config.logger.error(f"Could not parse {value}:", *e.args)
                parsed_value = self.value
            if parsed_value != self.value:
                Config.logger.debug(
                    f"Config value '{self.name}' changed to '{parsed_value}'"\
                    f" from '{self.value}'"
                )
                old_value = self.value
                self.value = parsed_value
                # Notify listeners
                for notifier in self.notifiers:
                    notifier(old_value, parsed_value)
            return self.value

    def __init__(self, config_location: Path):
        self._path = config_location
        # Options
        self._config_cache = {}
        self._add_config_options()
        self._last_read = None
        # Create a default config file if one does not exist
        if not self._path.exists():
            self.logger.info("No config file found, creating default")
            with self._path.open("x") as file:
                for entry in self._config_cache.values():
                    entry.write(file)
            self._last_read = self._path.stat().st_mtime
        else:
            self.logger.debug(f"Loading config from file "\
                             f"'{self._path}'")
            self.reload()

    @abstractmethod
    def _add_config_options(self):
        """
        Subclasses should override this to initialize all their
        config entries
        """

    def _add_config_option(self, *args):
        match args:
            case (Config.Entry(),):
                option = args[0]
            case (str(), ParserUtil.AbstractParser(), str(), _):
                option = Config.Entry(*args)
            case _:
                self.logger.error("Failed to initialize config option from:",
                                  args)
                return
        self._config_cache[option.name] = option

    def _reload_inner(self) -> None:
        """Reads the entire file and populates the config cache"""
        try:
            # Open file
            with self._path.open("rt") as file:
                self.logger.debug(f"Parsing config file at '{self._path}'")
                for line in file.readlines():
                    line = line.removesuffix("\n")
                    # Comments, empty lines in config file
                    if line.startswith("#") or not line.strip():
                        continue
                    # Does not follow key=value syntax
                    if "=" not in line:
                        self.logger.warn(
                            f"Invalid syntax in '{self._path}', "\
                            f"line reads '{line}'!")
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.removeprefix(" ")
                    if key in self._config_cache:
                        # Detecting changes
                        self._config_cache[key].parse(value)
                    else:
                        self.logger.warn(
                            f"Unknown config option '{key}', with value '{value}'!"
                        )
            self._last_read = self._path.stat().st_mtime
        except FileNotFoundError as f:
            self.logger.error(f"File does not exist at {self._path}: {f}")
            self.state = ResourceManager.State.REMOVED

    def check_file_changes(self) -> None:
        """Reload the config file if it has changed since we last read"""
        # Check if config file has been updated
        if not self._path.exists():
            self.logger.warn(f"File does not exist at {self._path}")
            self.state = ResourceManager.State.REMOVED
        if self._path.stat().st_mtime > self._last_read:
            self.reload()

    def get_option(self, key: str) -> Entry:
        """Get an entry in the config file"""
        self.check_file_changes()
        return self._config_cache[key]

    def get_value(self, key: str) -> Any:
        """Get the set value for an option in the config file"""
        return self.get_option(key).value
