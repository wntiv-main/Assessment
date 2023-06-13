from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from threading import Event
from enum import IntEnum
import time
from typing import Callable, Coroutine

from logger import Logger


class ResourceManager(ABC):
    """Class that handles loading and manages a resource"""
    logger = Logger()

    class State(IntEnum):
        """The state of the resource"""
        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2
        REMOVED = 3

    def __init__(self, task_handler: Callable[[Coroutine], None]):
        self.task_handler = task_handler
        self._ready_event = Event()
        self.state = ResourceManager.State.UNINITIALIZED

    def reload(self) -> Event:
        """
        Reload the resource on the resource loading thread.
        
        This is expected to take a long time as it may need to perform
        heavy operations. Returns an event which completes when resource
        reloading is complete.
        """
        if self.state != ResourceManager.State.INITIALIZING:
            self.state = ResourceManager.State.INITIALIZING
            self._ready_event.clear()
            self.task_handler(self._reload())
        return self._ready_event

    async def _reload(self):
        start_time = time.perf_counter()
        await self._reload_inner()
        if self.state == ResourceManager.State.INITIALIZING:
            self.state = ResourceManager.State.READY
            self.logger.info(f"Reloading resources for "
                            f"{self.__class__.__name__}, took "
                            f"{(time.perf_counter() - start_time) * 1000}ms")
            self._ready_event.set()
        else:
            self.logger.warn(f"Reloading resources for "
                             f"{self.__class__.__name__} encountered "
                             f"unexpected state change to {self.state.name}")

    @abstractmethod
    async def _reload_inner(self):
        """Method that subclasses should override to
        implement their task.
        """
        pass

    def on_ready(self) -> Event:
        """Return event waiting for resource ready."""
        if self.state == ResourceManager.State.UNINITIALIZED:
            self.reload()
        return self._ready_event
