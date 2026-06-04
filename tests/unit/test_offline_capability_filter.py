import pytest
from backend.core.offline_capability_filter import can_execute, get_offline_error_message

def test_can_execute_offline_safe_actions():
    assert can_execute("volume_control") is True
    assert can_execute("brightness_up") is True
    assert can_execute("take_screenshot") is True
    assert can_execute("lock") is True

def test_can_execute_online_required_actions():
    assert can_execute("search_web") is False
    assert can_execute("play_youtube") is False
    assert can_execute("spotify_play") is False
    assert can_execute("calendar_query") is False
    assert can_execute("slack_send") is False
    assert can_execute("vision_query") is False
    assert can_execute("camera_recognition") is False

def test_get_offline_error_message():
    msg_spotify = get_offline_error_message("spotify_pause")
    assert "Spotify" in msg_spotify
    
    msg_calendar = get_offline_error_message("calendar_create")
    assert "Calendar" in msg_calendar
    
    msg_slack = get_offline_error_message("slack_read")
    assert "Slack" in msg_slack
    
    msg_web = get_offline_error_message("search_web")
    assert "search the web" in msg_web
    
    msg_yt = get_offline_error_message("play_youtube")
    assert "YouTube" in msg_yt
    
    msg_vision = get_offline_error_message("vision_query")
    assert "vision" in msg_vision
    
    msg_generic = get_offline_error_message("some_random_action")
    assert "cannot perform this action" in msg_generic
