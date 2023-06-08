from abc import ABC, abstractmethod
from enum import IntEnum
import time

from logger import Logger


class ResourceManager(ABC):
    """Class that handles loading and manages a resource"""
    logger = Logger("ResourceManager")

    class State(IntEnum):
        """The state of the resource"""
        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2
        REMOVED = 3

    def __init__(self):
        self.state = ResourceManager.State.UNINITIALIZED

    def reload(self):
        """Reload the resource. This is expected to take a long
        time as it may need to perform heavy operations. Consider
        reloading on a seperate thread to the main thread to avoid
        hanging the entire program runtime.
        """
        start_time = time.perf_counter()
        self.state = ResourceManager.State.INITIALIZING
        self._reload_inner()
        if self.state == ResourceManager.State.INITIALIZING:
            self.state = ResourceManager.State.READY
            self.logger.info(f"Reloading resources for "
                            f"{self.__class__.__name__}, took "
                            f"{(time.perf_counter() - start_time) * 1000}ms")
        else:
            self.logger.warn(f"Reloading resources for "
                             f"{self.__class__.__name__} encountered "
                             f"unexpected state change to {self.state}")

    @abstractmethod
    def _reload_inner(self):
        """Method that subclasses should override to
        implement their task.
        """
        pass

    def hook_ready(self):
        """Ensure the resource is ready, if not, wait for it"""
        # For future threading possibility:
        # May need to synchronize and await for resource
        # to finish loading so we can use it
        match self.state:
            case ResourceManager.State.UNINITIALIZED:
                self.reload()
            case ResourceManager.State.INITIALIZING:
                while self.state != ResourceManager.State.READY:
                    pass
            case ResourceManager.State.READY:
                pass
