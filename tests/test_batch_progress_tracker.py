import pytest
import asyncio
from unittest.mock import AsyncMock
from src.zenoo_rpc.batch.context import BatchProgressTracker


@pytest.mark.asyncio
async def test_batch_progress_tracker_callbacks():
    tracker = BatchProgressTracker()
    mock_callback = AsyncMock()

    tracker.add_callback(mock_callback)

    progress = {"percentage": 50.0}

    await tracker.callback(progress)

    mock_callback.assert_called_with(progress)
    assert tracker.get_current_progress() == progress


def test_batch_progress_tracker_history():
    tracker = BatchProgressTracker()

    progress1 = {"percentage": 30.0}
    tracker.history.append(progress1.copy())
    tracker.current_progress = progress1

    progress2 = {"percentage": 60.0}
    tracker.history.append(progress2.copy())
    tracker.current_progress = progress2

    history = tracker.get_history()

    assert history == [progress1, progress2]


def test_batch_progress_tracker_clear_history():
    tracker = BatchProgressTracker()
    progress = {"percentage": 100.0}

    tracker.history.append(progress.copy())
    tracker.clear_history()

    assert tracker.get_history() == []
    assert tracker.current_progress is None
