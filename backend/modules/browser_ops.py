"""
browser_ops.py — THING v4.0
pyautogui-based browser operations.
Improved scrolling logic with keypress fallbacks for maximum reliability.
"""

import pyautogui
import subprocess
import time


def scroll_screen(direction: str, amount: int = 300) -> str:
    """
    Scrolls the active window.
    Combines mouse wheel scroll with arrow key presses for maximum compatibility.
    """
    try:
        direction = direction.lower().strip()
        
        # 1. Edge cases: scroll to top/bottom
        if amount >= 5000:
            key = 'end' if direction == 'down' else 'home'
            pyautogui.press(key)
            return f"Scrolled to the {('bottom' if direction == 'down' else 'top')} of the page."

        # 2. Standard scrolls
        # We use a loop for the scroll to ensure it's "felt" by the OS
        scroll_val = amount if direction == "up" else -amount
        
        # Perform mouse scroll
        pyautogui.scroll(scroll_val)
        time.sleep(0.1)
        pyautogui.scroll(scroll_val) # Double scroll for better response
        
        # 3. Keypress fallback (more reliable in some apps)
        # Use 'pagedown'/'pageup' for significant scrolls
        if amount >= 300:
            pyautogui.press('pagedown' if direction == 'down' else 'pageup')
        else:
            # Use arrow keys for small scrolls
            key = 'down' if direction == 'down' else 'up'
            for _ in range(5):
                pyautogui.press(key)

        return f"Scrolled {direction}."
    except Exception as e:
        print(f"[Scroll] Error: {e}")
        return f"Couldn't scroll {direction}."


def type_and_send(text: str, press_enter: bool = False) -> str:
    """Types text at the current cursor position."""
    if not text:
        return "Nothing to type."
    try:
        time.sleep(0.2)
        pyautogui.write(text, interval=0.02)
        if press_enter:
            pyautogui.press("enter")
        return "Typed."
    except Exception as e:
        return f"Couldn't type: {str(e)}"


def open_url(url: str) -> str:
    """Opens a URL in the default browser."""
    if not url:
        return "No URL provided."
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        subprocess.Popen(f'start {url}', shell=True)
        return f"Opened {url}."
    except Exception as e:
        return f"Couldn't open URL: {str(e)}"


def browser_nav(nav_type: str) -> str:
    """Keyboard-based browser navigation."""
    try:
        if nav_type == "back":
            pyautogui.hotkey("alt", "left")
            return "Going back."
        elif nav_type == "forward":
            pyautogui.hotkey("alt", "right")
            return "Going forward."
        elif nav_type == "refresh":
            pyautogui.hotkey("ctrl", "r")
            return "Refreshed."
        elif nav_type == "new_tab":
            pyautogui.hotkey("ctrl", "t")
            return "New tab opened."
        elif nav_type == "close_tab":
            pyautogui.hotkey("ctrl", "w")
            return "Tab closed."
        return f"Unknown navigation: {nav_type}."
    except Exception as e:
        return f"Navigation failed: {str(e)}"
