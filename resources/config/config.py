from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from io import TextIOWrapper
import os
from pathlib import Path
from threading import Event
from typing import Any, Callable, Coroutine

from logger import Logger
from parserutil import ParserUtil
from resources.resourcemanager import ResourceManager

def _get_null_event() -> Event:
    event = Event()
    event.set()
    return event

class Config(ResourceManager):
    """
    Class to handle and manage a config file at a specified file
    path using a basic TOML-style config file.
    """
    logger = Logger()
    NULL_EVENT = _get_null_event()

    class Entry:
        """Represents an entry within the config file."""
        def __init__(
            self,
            name: str,
            validator: ParserUtil.AbstractParser,
            description: str,
            default_value,
        ):
            """Create an entry within a config file."""
            self.name = name
            self.validator = validator
            self.description = description
            self.value = default_value
            self.default_value = default_value
            self.notifiers = []

        def when_changed(self, callback: Callable[[str, str], None]):
            """
            Add a listener for when this option is changed. 
            
            This is called with the old value and the new value as
            parameters. When called, the value of Entry.get_value() for
            this option will have already been changed.
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

        def reset(self):
            self.value = self.default_value

    def __init__(self, config_location: Path,
                 task_handler: Callable[[Coroutine], None]):
        super().__init__(task_handler)
        self._path = config_location
        # Options
        self._config_cache: dict[str, Config.Entry] = {}
        self._add_config_options()
        self._last_read = None
        self.logger.debug(f"Loading config from file "\
                            f"'{self._path}'")
        self.reload()

    def name(self) -> str:
        return self._path.stem

    @abstractmethod
    def _add_config_options(self):
        """
        Initialize all config entries (Subclasses should override).
        """
        pass

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

    async def _reload_inner(self) -> None:
        """Reads the entire file and populates the config cache"""
        # Create a default config file if one does not exist
        if not self._path.exists():
            self.logger.info(f"No config file found for {self._path}, "
                             "creating default")
            with self._path.open("x") as file:
                for entry in self._config_cache.values():
                    entry.reset()
                    entry.write(file)
            self._last_read = self._path.stat().st_mtime
            return
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

    def check_file_changes(self) -> Event:
        """Reload the config file if it has changed since we last read"""
        # Check if config file has been updated
        if not self._path.exists() or self._path.stat().st_mtime > self._last_read:
            return self.reload()
        return Config.NULL_EVENT

    def get_option(self, key: str, safe=False) -> Entry:
        """Get an entry in the config file"""
        if not safe:
            self.on_ready().wait()
        event = self.check_file_changes()
        if safe:
            event.wait()
        return self._config_cache[key]

    def get_value(self, key: str, safe=False) -> Any:
        """Get the set value for an option in the config file"""
        return self.get_option(key, safe).value

    def set_value(self, key: str, value: Any) -> None:
        """Change the value for an option in the config file"""
        self.get_option(key, True).value = value
        # TODO: SAVE CHANGES TO FILE
