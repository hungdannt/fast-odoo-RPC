"""Base test classes and utilities."""

import asyncio
import pytest
from typing import Optional
from datetime import datetime
from unittest import IsolatedAsyncioTestCase

from .helpers import TimeFreezer


class BaseAsyncTest(IsolatedAsyncioTestCase):
    """Base class for async tests with common utilities."""

    async def asyncSetUp(self):
        """Set up test case."""
        # Create a new event loop for each test
        self.loop = asyncio.get_event_loop()

    async def asyncTearDown(self):
        """Tear down test case."""
        # Cancel all pending tasks
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        for task in tasks:
            task.cancel()

        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def wait_for(self, coro, timeout: float = 5.0):
        """Wait for a coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)

    async def assert_async_raises(self, exception_type, coro):
        """Assert that an async function raises an exception."""
        with pytest.raises(exception_type):
            await coro

    @staticmethod
    def run_async(coro):
        """Run an async coroutine in a test."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


def freeze_time(frozen_time: Optional[datetime] = None):
    """
    Decorator/context manager to freeze time in tests.

    Usage:
        # As a decorator
        @freeze_time(datetime(2023, 1, 1))
        async def test_something():
            ...

        # As a context manager
        async def test_something():
            with freeze_time(datetime(2023, 1, 1)) as frozen:
                # Time is frozen here
                frozen.tick(10)  # Move forward 10 seconds
    """
    if frozen_time is None:
        frozen_time = datetime.now()

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with TimeFreezer(frozen_time):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with TimeFreezer(frozen_time):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    # If used as a context manager directly
    if callable(frozen_time):
        # frozen_time is actually the function being decorated
        func = frozen_time
        frozen_time = datetime.now()
        return decorator(func)

    # Return the decorator or TimeFreezer for context manager usage
    return TimeFreezer(frozen_time)
