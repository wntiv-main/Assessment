"""Class to manage a simple key=value-based config file."""

from abc import abstractmethod
from asyncio import Lock
from io import TextIOWrapper
from pathlib import Path
from threading import Event
from typing import Any, Callable, Coroutine, Iterable, overload

from logger import Logger
import parserutil
from resources.resourcemanager import ResourceManager


def _get_null_event() -> Event:
    event = Event()
    event.set()
    return event


class Config(ResourceManager):
    """
    Manage a basic key=value config file.

    Class to handle and manage a config file at a specified file
    path using a basic TOML-style config file.
    """

    logger = Logger()
    NULL_EVENT = _get_null_event()

    class Entry:
        """Represents an entry within the config file."""

        def __init__(self, name: str, validator: parserutil.AbstractParser,
                     description: str, default_value,
                     task_handler: Callable[[Coroutine | Callable], None]):
            """Create an entry within a config file."""
            self.name = name
            self.validator = validator
            self.description = description
            self.value = default_value
            self.default_value = default_value
            self.task_handler = task_handler
            self._notifiers = []

        def when_changed(self, callback: Callable[[Any, Any], None]):
            """
            Add a listener for when this option is changed.

            This is called with the old value and the new value as
            parameters. When called, the value of Entry.get_value() for
            this option will have already been changed.
            """
            self._notifiers.append(callback)

        def write(self, file: TextIOWrapper | Path):
            """
            Write this entry to the supplied file.

            If supplied a file, appends to the file.
            If supplied a path, clones the file, replacing old values
            for this entry with the new value, and then replaces the old
            file.
            """
            if isinstance(file, TextIOWrapper):
                for line in self.description.split("\n"):
                    file.write(f"# {line}\n")
                file.write(f"{self.name}="
                           f"{self.validator.stringify(self.value)}\n\n")
            elif isinstance(file, Path):
                # Create new temp file named ~oldname
                temp_path = file.with_stem(f"~{file.stem}")
                with temp_path.open("wt") as out:
                    found = False
                    trailing_newlines = 0
                    with file.open("rt") as in_file:
                        # Copy over the entire old file, replacing any
                        # instances of this config entry with the value
                        for line in in_file:
                            # Next lines are fine according to PEP8 but
                            # flagged in PEP8 checker.
                            if ('=' in line and
                                line.strip().startswith(f"{self.name}")):
                                # Replace old value with new, tring to
                                # preserve whitespace
                                equals_index = line.find("=")
                                has_space = line[equals_index + 1] == " "
                                line = line[:equals_index + has_space + 1]
                                line += self.validator.stringify(self.value)
                                line += "\n"
                                found = True
                            if line.isspace():
                                trailing_newlines += 1
                            else:
                                trailing_newlines = 0
                            out.write(line)
                    if not found:
                        # Config entry was not found in file, append
                        out.write(
                            ((2 - trailing_newlines) * "\n") +
                            f"{self.name}="
                            f"{self.validator.stringify(self.value)}"
                            f"\n\n")
                while True:
                    try:
                        temp_path.replace(file)
                        break
                    except IOError:
                        pass
            else:
                # Unreachable
                pass

        def parse(self, value: str) -> Any | ValueError:
            """
            Parse the given value.

            Return the parsed value, or None if there is an error
            parsing.
            """
            # Early check for equivilent value
            if value == self.validator.stringify(self.value):
                return self.value
            try:
                if isinstance(self.validator, parserutil.ComplexParser):
                    # Complex parsers need extra information
                    parsed_value = self.validator.parse(value, self)
                else:
                    parsed_value = self.validator.parse(value)
            except ValueError as e:
                # Error parsing, log return error
                Config.logger.error(f"Could not parse {value}:", *e.args)
                return e
            return parsed_value

        def parse_and_set(self, value: str):
            """Parse the value and set it, if it has changed."""
            parsed_value = self.parse(value)
            if (parsed_value != self.value and
                    not isinstance(parsed_value, ValueError)):
                Config.logger.debug(
                    f"Config value '{self.name}' changed to "
                    f"'{parsed_value}' from '{self.value}'")
                self._set_value(parsed_value)

        def _set_value(self, value):
            old_value = self.value
            self.value = value
            # Notify listeners
            for notifier in self._notifiers:
                notifier(old_value, value)

        def reset(self):
            """Reset the value to it's default."""
            self._set_value(self.default_value)

    def __init__(self, config_location: Path,
                 task_handler: Callable[[Coroutine | Callable], None]):
        """
        Create a config manager from a file path.

        Accepts the Path object pointing to the path, as well as a task
        handler function which should handle any async tasks that need
        to be executed in the future.
        """
        super().__init__(task_handler)
        self._path = config_location
        self._config_cache: dict[str, Config.Entry] = {}
        self._add_config_options()
        self._last_read = None
        self._lock = Lock()
        self.logger.debug(f"Loading config from file '{self._path}'")
        self.reload()

    def name(self) -> str:
        """Return the name of this config file."""
        return self._path.stem
    
    def entries(self) -> Iterable[Entry]:
        """Return all entries in this config."""
        return self._config_cache.values()

    @abstractmethod
    def _add_config_options(self):
        """
        Initialize all config entries (Subclasses should override).

        Use _add_config_option to add an option.
        """
        pass

    @overload
    def _add_config_option(self, entry: Entry) -> None: ...

    @overload
    def _add_config_option(self,
                           name: str,
                           validator: parserutil.AbstractParser,
                           description: str,
                           default_value) -> None: ...

    def _add_config_option(self, *args) -> None:
        match args:
            case (Config.Entry(),):
                option = args[0]
            case (str(), parserutil.AbstractParser(), str(), _):
                option = Config.Entry(*args, self.task_handler)
            case _:
                self.logger.error("Failed to initialize config option"
                                  "from:", args)
                return
        self._config_cache[option.name] = option

    async def _reload_inner(self) -> None:
        """Read the entire file and populate the config cache."""
        async with self._lock:
            # Create a default config file if one does not exist
            if not self._path.exists():
                self.logger.info(f"No config file found for "
                                 f"{self._path}, creating default")
                with self._path.open("x") as file:
                    for entry in self._config_cache.values():
                        entry.reset()
                        entry.write(file)
                self._last_read = self._path.stat().st_mtime
                return
            # Open file
            with self._path.open("rt") as file:
                self.logger.debug(
                    f"Parsing config file at '{self._path}'")
                for line in file.readlines():
                    line = line.removesuffix("\n")
                    # Comments, empty lines in config file
                    if line.startswith("#") or not line.strip():
                        continue
                    # Does not follow key=value syntax
                    if "=" not in line:
                        self.logger.warn(
                            f"Invalid syntax in '{self._path}', "
                            f"line reads '{line}'!")
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.removeprefix(" ")
                    if key in self._config_cache:
                        # Detecting changes
                        self._config_cache[key].parse_and_set(value)
                    else:
                        self.logger.warn(
                            f"Unknown config option '{key}', with "
                            f"value '{value}'!")
            self._last_read = self._path.stat().st_mtime

    def check_file_changes(self) -> Event:
        """Reload the config file if it changed since we last read."""
        # Check if config file has been updated
        if (not self._path.exists() or
                self._path.stat().st_mtime != self._last_read):
            return self.reload()
        return Config.NULL_EVENT

    def get_option(self, key: str, safe=False) -> Entry:
        """
        Get an entry in the config file.

        Parameters:
        key - The name of the entry to get.
        safe - Should we wait for pending file changes to be parsed
               before proceeding.
        """
        if not safe:
            self.on_ready().wait()
        event = self.check_file_changes()
        if safe:
            event.wait()
        return self._config_cache[key]

    def get_value(self, key: str, safe=False) -> Any:
        """
        Get the set value for an option in the config file.

        Parameters:
        key - The name of the entry to get.
        safe - Should we wait for pending file changes to be parsed
               before proceeding.
        """
        return self.get_option(key, safe).value

    def set_value(self, key: str, value: Any) -> None:
        """Change the value for an option in the config file."""
        option = self.get_option(key, True)
        option._set_value(value)
        self.logger.debug(f"Queuing write changes to {self._path}.{key}")
        # Queue saving changes to file
        self.task_handler(self._set_value_update_file(option))

    async def _set_value_update_file(self, option: Entry):
        # Make sure any outside pending changes are accounted for first
        self.check_file_changes().wait()
        self.logger.info(f"Writing config changes to '{self._path}': "
                         f"{option.name} changed to '{option.value}'")
        # Lock and make changes
        async with self._lock:
            option.write(self._path)
            self._last_read = self._path.stat().st_mtime
