"""
test_scheduler.py — THING v5.0
Unit tests for the Scheduler.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
import schedule
from backend.core.scheduler import Scheduler

def test_scheduler_init_default():
    callback = MagicMock()
    sch = Scheduler(callback)
    assert sch.eod_hour == 17  # default EOD hour is 17 (5 PM)
    assert sch.enabled is True

def test_scheduler_init_env_override():
    callback = MagicMock()
    with patch.dict("os.environ", {"PROACTIVE_EOD_HOUR": "20", "PROACTIVE_ENABLED": "false"}):
        sch = Scheduler(callback)
        assert sch.eod_hour == 20
        assert sch.enabled is False

def test_scheduler_start_stop():
    callback = MagicMock()
    sch = Scheduler(callback)
    
    with patch("schedule.every") as mock_every:
        mock_job = MagicMock()
        mock_every.return_value.day.at.return_value.do.return_value = mock_job
        
        # Start
        sch.start()
        assert sch._job == mock_job
        assert sch._thread is not None
        
        # Stop
        with patch("schedule.cancel_job") as mock_cancel:
            sch.stop()
            mock_cancel.assert_called_once_with(mock_job)
            assert sch._job is None
            assert sch._stop_event.is_set()

def test_scheduler_callback():
    callback = MagicMock()
    sch = Scheduler(callback)
    sch._run_callback()
    callback.assert_called_once_with("scheduled_time_check")
