"""
test_spotify_sdk.py — Phase 4B Tests
Unit tests for spotify_sdk.py — mocks spotipy and oauth_manager.
"""

import pytest
from unittest.mock import patch, MagicMock


# ─── Shared mock setup ────────────────────────────────────────────────

@pytest.fixture
def mock_spotify_connected(monkeypatch):
    """Patch oauth_manager so Spotify appears connected with a fake token."""
    with patch("backend.core.oauth_manager.get_token", return_value="fake_sp_token"), \
         patch("backend.core.oauth_manager.is_connected", return_value=True):
        yield


@pytest.fixture
def mock_spotify_client(mock_spotify_connected):
    """Return a mock spotipy.Spotify client."""
    mock_sp = MagicMock()
    with patch("backend.modules.spotify_sdk._get_spotify", return_value=mock_sp):
        yield mock_sp


# ─── play_track ───────────────────────────────────────────────────────

class TestPlayTrack:
    def test_plays_track_by_name(self, mock_spotify_client):
        from backend.modules.spotify_sdk import play_track

        mock_spotify_client.devices.return_value = {
            "devices": [{"id": "dev1", "is_active": True}]
        }
        mock_spotify_client.search.return_value = {
            "tracks": {"items": [{
                "uri": "spotify:track:abc",
                "name": "Blinding Lights",
                "artists": [{"name": "The Weeknd"}],
            }]}
        }

        result = play_track("Blinding Lights")
        assert "Blinding Lights" in result
        assert "The Weeknd" in result
        mock_spotify_client.start_playback.assert_called_once()

    def test_plays_playlist(self, mock_spotify_client):
        from backend.modules.spotify_sdk import play_track

        mock_spotify_client.devices.return_value = {
            "devices": [{"id": "dev1", "is_active": True}]
        }
        mock_spotify_client.search.return_value = {
            "playlists": {"items": [{"uri": "spotify:playlist:xyz", "name": "Discover Weekly"}]}
        }

        result = play_track("Discover Weekly playlist")
        assert "Discover Weekly" in result

    def test_returns_helpful_msg_when_no_device(self, mock_spotify_client):
        from backend.modules.spotify_sdk import play_track

        mock_spotify_client.devices.return_value = {"devices": []}
        result = play_track("Blinding Lights")
        assert "No active Spotify device" in result

    def test_returns_not_found_when_no_results(self, mock_spotify_client):
        from backend.modules.spotify_sdk import play_track

        mock_spotify_client.devices.return_value = {
            "devices": [{"id": "dev1", "is_active": True}]
        }
        mock_spotify_client.search.return_value = {
            "tracks": {"items": []},
            "albums": {"items": []},
        }
        result = play_track("xyzzy gibberish track that doesn't exist")
        assert "Couldn't find" in result or "couldn't find" in result.lower()

    def test_error_when_not_connected(self, monkeypatch):
        monkeypatch.setattr("backend.core.oauth_manager.is_connected", lambda s: False)
        monkeypatch.setattr("backend.core.oauth_manager.get_token", lambda s: None)
        from backend.modules.spotify_sdk import play_track
        result = play_track("any song")
        # Result is either "not connected" (oauth check) or "not installed" (import check)
        assert any(phrase in result.lower() for phrase in ["not connected", "connect", "not installed"])


# ─── pause / resume ───────────────────────────────────────────────────

class TestPlaybackControls:
    def test_pause(self, mock_spotify_client):
        from backend.modules.spotify_sdk import pause
        result = pause()
        mock_spotify_client.pause_playback.assert_called_once()
        assert "paused" in result.lower()

    def test_resume(self, mock_spotify_client):
        from backend.modules.spotify_sdk import resume
        mock_spotify_client.devices.return_value = {"devices": [{"id": "dev1", "is_active": True}]}
        result = resume()
        mock_spotify_client.start_playback.assert_called_once()
        assert "resumed" in result.lower()

    def test_skip(self, mock_spotify_client):
        from backend.modules.spotify_sdk import skip
        result = skip()
        mock_spotify_client.next_track.assert_called_once()
        assert "next" in result.lower() or "skip" in result.lower()

    def test_previous(self, mock_spotify_client):
        from backend.modules.spotify_sdk import previous
        result = previous()
        mock_spotify_client.previous_track.assert_called_once()
        assert "previous" in result.lower()

    def test_pause_failure_returns_friendly_message(self, mock_spotify_client):
        from backend.modules.spotify_sdk import pause
        mock_spotify_client.pause_playback.side_effect = Exception("Player command failed")
        result = pause()
        assert "Could not" in result or "failed" in result.lower()


# ─── set_volume ───────────────────────────────────────────────────────

class TestSetVolume:
    def test_sets_volume(self, mock_spotify_client):
        from backend.modules.spotify_sdk import set_volume
        result = set_volume(75)
        mock_spotify_client.volume.assert_called_once_with(75)
        assert "75%" in result

    def test_clamps_volume_to_0_100(self, mock_spotify_client):
        from backend.modules.spotify_sdk import set_volume
        set_volume(150)
        mock_spotify_client.volume.assert_called_once_with(100)
        mock_spotify_client.volume.reset_mock()
        set_volume(-10)
        mock_spotify_client.volume.assert_called_once_with(0)


# ─── get_current_track ───────────────────────────────────────────────

class TestGetCurrentTrack:
    def test_returns_track_info(self, mock_spotify_client):
        from backend.modules.spotify_sdk import get_current_track
        mock_spotify_client.current_playback.return_value = {
            "is_playing": True,
            "progress_ms": 60000,
            "item": {
                "name": "Shape of You",
                "artists": [{"name": "Ed Sheeran"}],
                "album": {"name": "Divide"},
                "duration_ms": 234000,
            },
        }
        info = get_current_track()
        assert info["track_name"] == "Shape of You"
        assert info["artist"] == "Ed Sheeran"
        assert info["is_playing"] is True

    def test_returns_error_when_nothing_playing(self, mock_spotify_client):
        from backend.modules.spotify_sdk import get_current_track
        mock_spotify_client.current_playback.return_value = {"item": None}
        info = get_current_track()
        assert "error" in info
