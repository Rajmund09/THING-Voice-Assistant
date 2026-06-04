import time
import pyautogui
import psutil
from backend.modules.youtube_controller import yt_controller
from backend.engine.memory_engine import memory
from backend.modules.system_ops import open_app

def is_spotify_running() -> bool:
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'spotify' in proc.info['name'].lower():
                return True
    except Exception:
        pass
    return False


def play_youtube(query: str) -> str:
    """Delegates to professional Playwright controller."""
    return yt_controller.play_video(query)


def control_media(action: str) -> str:
    """
    Intelligent media control manager.
    Handles YouTube Playwright shortcuts or system-wide media hotkeys (Spotify/Windows media).
    """
    action_lower = action.lower().strip()
    
    # 1. Handle explicit Spotify playback launch
    if "spotify" in action_lower:
        if "play" in action_lower or "resume" in action_lower:
            if not is_spotify_running():
                open_app("spotify")
                time.sleep(2.0)
            pyautogui.press("playpause")
            return "Playing Spotify."
        elif "pause" in action_lower:
            if is_spotify_running():
                pyautogui.press("playpause")
                return "Paused Spotify."
            return "Spotify is not running."

    # 2. General Media Mapping
    mapping = {
        "pause": "pause",
        "play": "resume",
        "resume": "resume",
        "next": "next",
        "fullscreen": "fullscreen",
        "mute": "mute",
        "volume up": "volume_up",
        "volume down": "volume_down",
        "skip": "skip_forward",
        "back": "skip_backward"
    }
    
    # Extract root action keyword (e.g. "resume" from "resume_music")
    root_action = action_lower
    for k in ["_video", "_music", "_song", "_playback"]:
        if root_action.endswith(k):
            root_action = root_action.replace(k, "")
            
    action_key = mapping.get(root_action, root_action)

    # 3. Determine if we control the browser or system-wide player
    active_app = memory.get_context("active_app") or ""
    
    # If browser is active, delegate to YouTube browser controller
    if active_app.lower() == "browser":
        return yt_controller.control(action_key)
        
    # Otherwise, fallback gracefully to global Windows media keys
    try:
        if action_key in ["pause", "resume"]:
            pyautogui.press("playpause")
            return "Toggled system media playback."
        elif action_key == "next":
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action_key in ["prev", "back", "skip_backward"]:
            pyautogui.press("prevtrack")
            return "Went to previous track."
        elif action_key == "stop":
            pyautogui.press("stop")
            return "Stopped system media."
    except Exception as e:
        print(f"[Media Ops] Fallback control failed: {e}")
        
    # Default to YouTube controller if all else fails
    return yt_controller.control(action_key)

