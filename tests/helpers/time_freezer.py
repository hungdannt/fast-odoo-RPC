"""Time freezer for testing."""

from datetime import datetime, timedelta
from typing import Optional, Union
import time
from unittest.mock import patch


class TimeFreezer:
    """Helper class for freezing time in tests."""

    def __init__(self, frozen_time: Optional[datetime] = None):
        self.frozen_time = frozen_time or datetime.now()
        self._patches = []

    def __enter__(self):
        """Enter the context manager."""
        # Patch datetime.now()
        datetime_patch = patch("datetime.datetime")
        mock_datetime = datetime_patch.start()
        mock_datetime.now.return_value = self.frozen_time
        mock_datetime.utcnow.return_value = self.frozen_time
        mock_datetime.today.return_value = self.frozen_time.date()
        self._patches.append(datetime_patch)

        # Patch time.time()
        time_patch = patch("time.time")
        mock_time = time_patch.start()
        mock_time.return_value = self.frozen_time.timestamp()
        self._patches.append(time_patch)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        for patch_obj in self._patches:
            patch_obj.stop()
        self._patches.clear()

    def tick(self, delta: Union[timedelta, float]):
        """Move time forward by a delta."""
        if isinstance(delta, (int, float)):
            delta = timedelta(seconds=delta)
        self.frozen_time += delta

        # Update mocked values
        for patch_obj in self._patches:
            if hasattr(patch_obj.target, "now"):
                patch_obj.target.now.return_value = self.frozen_time
                patch_obj.target.utcnow.return_value = self.frozen_time
                patch_obj.target.today.return_value = self.frozen_time.date()
            elif hasattr(patch_obj.target, "time"):
                patch_obj.target.return_value = self.frozen_time.timestamp()

    def set_time(self, new_time: datetime):
        """Set a new frozen time."""
        self.frozen_time = new_time
        self.tick(timedelta(0))  # Update mocked values

    @staticmethod
    def freeze(frozen_time: Optional[datetime] = None):
        """Create a TimeFreezer instance."""
        return TimeFreezer(frozen_time)
