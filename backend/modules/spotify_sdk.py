"""
spotify_sdk.py — THING Phase 4B
Spotify Web API integration via spotipy.

Provides:
  - play_track(query)        — search and play track/album/playlist
  - pause() / resume()       — playback control
  - skip() / previous()      — track navigation
  - set_volume(percent)      — volume 0–100
  - get_current_track()      — returns currently playing track info
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_spotify():
    """
    Returns an authenticated Spotify client using the stored OAuth token.
    Falls back gracefully if spotipy is not installed or service is not connected.
    """
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        raise RuntimeError(
            "spotipy is not installed. Run: pip install spotipy>=2.23.0"
        )

    from backend.core.oauth_manager import get_token, is_connected
    if not is_connected("spotify"):
        raise RuntimeError(
            "Spotify is not connected. Open THING's Integrations panel and click 'Connect Spotify'."
        )

    token = get_token("spotify")
    auth_manager = spotipy.oauth2.SpotifyOAuth.__new__(spotipy.oauth2.SpotifyOAuth)
    # Inject token directly — oauth_manager handles refresh
    client = spotipy.Spotify(auth=token)
    return client


def _get_active_device_id(sp) -> Optional[str]:
    """Returns the ID of the first active (or available) playback device."""
    try:
        devices = sp.devices()
        device_list = devices.get("devices", [])
        if not device_list:
            return None
        # Prefer an active device
        for d in device_list:
            if d.get("is_active"):
                return d["id"]
        # Fall back to first available
        return device_list[0]["id"]
    except Exception as exc:
        logger.error("[Spotify] Could not fetch devices: %s", exc)
        return None


def play_track(query: str) -> str:
    """
    Searches Spotify for a track/album/playlist matching the query and starts playback.

    Args:
        query: Natural language search string, e.g. "Blinding Lights" or "Discover Weekly".

    Returns:
        Confirmation string for voice output.
    """
    try:
        sp = _get_spotify()
        device_id = _get_active_device_id(sp)
        if not device_id:
            return (
                "No active Spotify device found. Please open Spotify on your PC or phone first, "
                "then try again."
            )

        # Try playlist first (e.g., "Discover Weekly", "Liked Songs")
        playlist_keywords = ["playlist", "discover weekly", "release radar", "daily mix", "liked"]
        is_playlist_query = any(kw in query.lower() for kw in playlist_keywords)

        if is_playlist_query:
            results = sp.search(q=query, type="playlist", limit=5)
            items = results.get("playlists", {}).get("items", [])
            if items:
                uri = items[0]["uri"]
                name = items[0]["name"]
                sp.start_playback(device_id=device_id, context_uri=uri)
                return f"Playing playlist '{name}' on Spotify."

        # Default: search for track
        results = sp.search(q=query, type="track", limit=5)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            # Fallback to album
            results = sp.search(q=query, type="album", limit=3)
            items_album = results.get("albums", {}).get("items", [])
            if items_album:
                uri = items_album[0]["uri"]
                name = items_album[0]["name"]
                sp.start_playback(device_id=device_id, context_uri=uri)
                return f"Playing album '{name}' on Spotify."
            return f"Couldn't find anything on Spotify for '{query}'."

        track = items[0]
        track_uri = track["uri"]
        track_name = track["name"]
        artist_name = track["artists"][0]["name"] if track.get("artists") else "Unknown Artist"

        sp.start_playback(device_id=device_id, uris=[track_uri])
        return f"Playing '{track_name}' by {artist_name} on Spotify."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] play_track error: %s", exc)
        return f"Spotify playback failed: {exc}"


def pause() -> str:
    """Pauses Spotify playback."""
    try:
        sp = _get_spotify()
        sp.pause_playback()
        return "Spotify paused."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] pause error: %s", exc)
        return "Could not pause Spotify."


def resume() -> str:
    """Resumes Spotify playback."""
    try:
        sp = _get_spotify()
        device_id = _get_active_device_id(sp)
        sp.start_playback(device_id=device_id)
        return "Spotify resumed."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] resume error: %s", exc)
        return "Could not resume Spotify."


def skip() -> str:
    """Skips to the next track on Spotify."""
    try:
        sp = _get_spotify()
        sp.next_track()
        return "Skipped to the next track."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] skip error: %s", exc)
        return "Could not skip track."


def previous() -> str:
    """Goes to the previous track on Spotify."""
    try:
        sp = _get_spotify()
        sp.previous_track()
        return "Playing previous track."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] previous error: %s", exc)
        return "Could not go to previous track."


def set_volume(percent: int) -> str:
    """
    Sets Spotify playback volume.

    Args:
        percent: Volume level 0–100.

    Returns:
        Confirmation string.
    """
    try:
        sp = _get_spotify()
        percent = max(0, min(100, int(percent)))
        sp.volume(percent)
        return f"Spotify volume set to {percent}%."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Spotify] set_volume error: %s", exc)
        return "Could not change Spotify volume."


def get_current_track() -> Dict[str, Any]:
    """
    Returns information about the currently playing track.

    Returns:
        Dict with keys: track_name, artist, album, is_playing, progress_ms, duration_ms
        Or {"error": "..."} on failure.
    """
    try:
        sp = _get_spotify()
        current = sp.current_playback()
        if not current or not current.get("item"):
            return {"error": "Nothing is currently playing on Spotify."}

        item = current["item"]
        return {
            "track_name":   item["name"],
            "artist":       item["artists"][0]["name"] if item.get("artists") else "Unknown",
            "album":        item.get("album", {}).get("name", ""),
            "is_playing":   current.get("is_playing", False),
            "progress_ms":  current.get("progress_ms", 0),
            "duration_ms":  item.get("duration_ms", 0),
        }
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.error("[Spotify] get_current_track error: %s", exc)
        return {"error": str(exc)}
