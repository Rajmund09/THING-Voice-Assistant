"""
test_context_observer.py — THING v5.0
Unit tests for ContextObserver background thread and cooldown logic.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from backend.core.context_observer import ContextObserver

@pytest.fixture
def mock_socketio():
    return MagicMock()

@pytest.fixture
def observer(mock_socketio):
    with patch.dict("os.environ", {"PROACTIVE_ENABLED": "true"}):
        obs = ContextObserver(mock_socketio)
        return obs

def test_observer_cooldown_logic(observer, mock_socketio):
    suggestion = {"id": "test_id", "message": "hello", "action": "test", "icon": "test", "dismissible": True}
    
    # First emit
    observer._emit_suggestion(suggestion)
    assert mock_socketio.emit.call_count == 1
    
    # Immediate second emit (should be suppressed by cooldown)
    observer._emit_suggestion(suggestion)
    assert mock_socketio.emit.call_count == 1
    
    # Fast-forward cooldown
    with patch("time.time", return_value=time.time() + 700):
        observer._emit_suggestion(suggestion)
        assert mock_socketio.emit.call_count == 2

def test_observer_clipboard_check(observer, mock_socketio):
    with patch("pyperclip.paste", return_value="https://zoom.us/j/123"):
        observer._check_clipboard()
        assert mock_socketio.emit.call_count == 1
        assert observer.last_clipboard == "https://zoom.us/j/123"
        
        # Second check with same content (should not emit)
        observer._check_clipboard()
        assert mock_socketio.emit.call_count == 1

def test_observer_idle_check(observer, mock_socketio):
    with patch("backend.engine.state_manager.state_manager.get_idle_minutes", return_value=25.0):
        observer._check_idle()
        assert mock_socketio.emit.call_count == 1

def test_observer_disabled_skips_start(mock_socketio):
    with patch.dict("os.environ", {"PROACTIVE_ENABLED": "false"}):
        observer = ContextObserver(mock_socketio)
        observer.start()
        assert observer._thread is None


def test_observer_active_apps_check(observer, mock_socketio):
    mock_proc = MagicMock()
    mock_proc.info = {"name": "zoom.exe"}
    
    with patch("psutil.process_iter", return_value=[mock_proc]):
        observer._check_active_apps()
        assert mock_socketio.emit.call_count == 1
        args, kwargs = mock_socketio.emit.call_args
        assert args[0] == "proactive_suggestion"
        assert args[1]["id"] == "meeting_app_detected"
        assert "Zoom" in args[1]["message"]
        assert args[1]["action"] == "mute_notifications"


def test_observer_system_load_personalized(observer, mock_socketio):
    mock_cpu_proc = MagicMock()
    mock_cpu_proc.info = {"name": "chrome.exe", "cpu_percent": 95.0}
    
    with patch("psutil.cpu_percent", return_value=95.0), \
         patch("psutil.virtual_memory") as mock_mem, \
         patch("psutil.process_iter", return_value=[mock_cpu_proc]):
        
        mock_mem.return_value.percent = 50.0
        observer.load_enabled = True
        
        observer._check_system_load()
        assert mock_socketio.emit.call_count == 1
        args, kwargs = mock_socketio.emit.call_args
        assert args[0] == "proactive_suggestion"
        assert args[1]["id"] == "high_cpu_usage"
        assert "chrome.exe" in args[1]["message"]
