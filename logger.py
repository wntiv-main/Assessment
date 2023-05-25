from enum import IntEnum
import os
import sys
import pathlib

# Ensure terminal is correctly set up to handle ANSI escape sequences
os.system("")

class Logger:
    """
    Util class for creating organised and clear output logs
    """
    class Level(IntEnum):
        DEBUG = 0
        INFO = 1
        WARN = 2
        ERROR = 3
        DEFAULT = 4
    COLORS = {
        Level.DEBUG: "\033[96m",
        Level.INFO: "",
        Level.WARN: "\033[93m",
        Level.ERROR: "\033[91m"
    }

    def __init__(self, name: str, level: Level = Level.DEFAULT):
        """
        Initialize with a name (shown in all log messages), and optionally a log level,
        where only messages with a level equal or higher than this will be displayed.
        """
        self.name = name
        self.level = level

    def get_level(self):
        """
        Returns the effective level that this logger will display messages for, taking
        consideration of the default level which may vary if the program is running in a dev env.
        """
        if self.level == Logger.Level.DEFAULT:
            return Logger.Level.DEBUG
        return self.level

    def _traceback(self):
        """
        Util function for retreiving the function name and line number of the call to logger
        """
        caller = sys._getframe().f_back.f_back.f_back
        match self.get_level():
            case Logger.Level.DEBUG:
                return f"{caller.f_code.co_name} at ./{pathlib.Path(caller.f_code.co_filename).absolute().relative_to(pathlib.Path('./').absolute())}:{caller.f_lineno}"
            case _:
                return f"{caller.f_code.co_name}"

    def _out(self, level: Level, *args, **kwargs):
        """
        All logger output is sent to this function, may be overidden to output to file, etc.
        """
        if self.get_level() <= level:
            print(f"{Logger.COLORS[level]}[{self.name}:{level.name} in {self._traceback()}]", *args, "\033[0m", **kwargs)

    def is_debug(self):
        """
        Returns whether logger should display debug messages
        """
        return self.get_level() <= self.Level.DEBUG

    def debug(self, *args, **kwargs):
        self._out(Logger.Level.DEBUG, *args, **kwargs)

    def is_info(self):
        """
        Returns whether logger should display info messages
        """
        return self.get_level() <= self.Level.INFO

    def info(self, *args, **kwargs):
        self._out(Logger.Level.INFO, *args, **kwargs)

    def is_warn(self):
        """
        Returns whether logger should display warning messages
        """
        return self.get_level() <= self.Level.WARN

    def warn(self, *args, **kwargs):
        self._out(Logger.Level.WARN, *args, **kwargs)

    def is_error(self):
        """
        Returns whether logger should display error messages
        """
        return self.get_level() <= self.Level.ERROR

    def error(self, *args, **kwargs):
        self._out(Logger.Level.ERROR, *args, **kwargs)
