"""
Abstract class representing a manager of a resource.

This resource is expected to be performance heavy to (re)load, and
should mostly be loaded on a seperate thread.
"""

from abc import ABC, abstractmethod
from threading import Event
from enum import IntEnum
import time
from typing import Callable, Coroutine

from logger import Logger


class ResourceManager(ABC):
    """Class that handles loading and manages a resource."""

    logger = Logger()

    class State(IntEnum):
        """The state of the resource."""

        UNINITIALIZED = 0
        INITIALIZING = 1
        READY = 2
        REMOVED = 3

    def __init__(self, task_handler: Callable[[Coroutine | Callable], None]):
        """
        Initialize the resource manager, accepting a task handler.

        The task handler is a function that should accept an async task
        that needs to be completed at *some* point, and queues it for
        execution (preferably on a seperate thread).
        """
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
            # Queue reload in resource threads
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
            # State was changed in _reload_inner, assume something went
            # wrong. Leaves manager in this potentially invalid state.
            self.logger.warn(f"Reloading resources for "
                             f"{self.__class__.__name__} encountered "
                             f"unexpected state change to {self.state.name}")

    @abstractmethod
    async def _reload_inner(self):
        """
        Load the resource.

        Subclasses should override this to implement their resource
        loading. (Ideally) runs async in a seperate thread.
        """
        pass

    def on_ready(self) -> Event:
        """Return event waiting for resource ready."""
        if self.state == ResourceManager.State.UNINITIALIZED:
            self.reload()
        return self._ready_event
