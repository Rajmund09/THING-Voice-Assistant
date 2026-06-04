"""
youtube_controller.py — THING v4.0
Direct-Link YouTube Engine.
Now uses system default browser to ensure user is logged in.
Resolves Video ID first, then opens the direct watch URL.
"""

import subprocess
import urllib.parse
import time
import os
import sys
import pyautogui
from backend.engine.state_manager import state_manager
from backend.utils.media_matcher import normalize_query

class YouTubeController:
    def __init__(self):
        pass

    def play_video(self, query: str) -> str:
        """
        ZERO-CLICK STRATEGY:
        1. Normalize Query (remove pipes, feat, etc.)
        2. Resolve Video ID via yt-dlp.
        3. Open the watch URL directly in default browser.
        """
        state_manager.acquire_lock()
        try:
            # Step 1: Normalize
            clean_query = normalize_query(query)
            print(f"[YouTube] Original: {query}")
            print(f"[YouTube] Normalized: {clean_query}")
            
            # Step 2: Use yt-dlp to get the first video ID
            video_id = None
            try:
                # Use sys.executable -m to ensure we use the correct environment
                cmd = f'"{sys.executable}" -m yt_dlp --get-id "ytsearch1:{clean_query}"'
                print(f"[YouTube] Running: {cmd}")
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=15)
                
                if result.returncode == 0:
                    video_id = result.stdout.strip()
                    # Sometimes yt-dlp returns multiple IDs if not careful, take first
                    if "\n" in video_id:
                        video_id = video_id.split("\n")[0].strip()
                else:
                    print(f"[YouTube] yt-dlp stderr: {result.stderr}")
            except Exception as e:
                print(f"[YouTube] yt-dlp execution error: {e}")

            if not video_id:
                print("[YouTube] Falling back to search URL due to ID resolution failure.")
                encoded = urllib.parse.quote(clean_query)
                video_url = f"https://www.youtube.com/results?search_query={encoded}"
                msg = f"Searching for {clean_query} on YouTube."
            else:
                video_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
                msg = f"Playing {clean_query} on YouTube."

            print(f"[YouTube] Opening URL in default browser: {video_url}")

            # Step 3: Open browser directly using OS 'start'
            # We use &autoplay=1 and also try to trigger play via keyboard if needed
            subprocess.Popen(f'start "" "{video_url}"', shell=True)

            return msg

        except Exception as e:
            print(f"[YouTube] Playback Error: {repr(e)}")
            return f"I encountered an error trying to play that video."
        finally:
            state_manager.release_lock()

    def control(self, action: str) -> str:
        """Standard media controls using pyautogui shortcuts."""
        try:
            # Note: These keys only work if the browser window is active.
            # YouTube Keyboard Shortcuts:
            # k: play/pause, f: fullscreen, m: mute, n: next video
            # up/down: volume, j/l: skip back/forward
            
            if action in ["pause", "play", "resume"]:
                pyautogui.press("k")
            elif action == "next":
                pyautogui.press("n")
            elif action == "fullscreen":
                pyautogui.press("f")
            elif action == "mute":
                pyautogui.press("m")
            elif "volume_up" in action:
                pyautogui.press("up")
            elif "volume_down" in action:
                pyautogui.press("down")
            elif "skip_forward" in action:
                pyautogui.press("l")
            elif "skip_backward" in action:
                pyautogui.press("j")
            
            return "Done."
        except Exception as e:
            print(f"[YouTube] Control Error: {e}")
            return "Failed to control media."

# Singleton
yt_controller = YouTubeController()
