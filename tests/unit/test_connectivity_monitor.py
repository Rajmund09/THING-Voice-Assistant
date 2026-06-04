import pytest
from unittest.mock import patch, MagicMock
from backend.core.connectivity_monitor import ConnectivityMonitor

@patch("backend.core.connectivity_monitor.urllib.request.urlopen")
def test_connectivity_monitor_online(mock_urlopen):
    # Mock successful connection
    mock_urlopen.return_value = MagicMock()
    
    monitor = ConnectivityMonitor(check_interval=0.1)
    # simulate a single check cycle
    status = monitor._check_connection()
    assert status is True

@patch("backend.core.connectivity_monitor.urllib.request.urlopen")
def test_connectivity_monitor_offline(mock_urlopen):
    # Mock connection failure
    mock_urlopen.side_effect = Exception("Network unreachable")
    
    monitor = ConnectivityMonitor(check_interval=0.1)
    status = monitor._check_connection()
    assert status is False

@patch("backend.core.connectivity_monitor.urllib.request.urlopen")
def test_connectivity_monitor_socketio_emit(mock_urlopen):
    mock_urlopen.return_value = MagicMock()
    
    mock_socketio = MagicMock()
    monitor = ConnectivityMonitor(socketio=mock_socketio, check_interval=0.1)
    
    # Simulate setting socketio which should trigger an immediate emit
    monitor.set_socketio(mock_socketio)
    mock_socketio.emit.assert_called_with("connectivity_status", {"online": True})
