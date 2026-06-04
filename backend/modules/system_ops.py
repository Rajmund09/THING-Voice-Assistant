"""
system_ops.py — THING v4.0
System-level operations: volume, brightness, power, apps, time, search.
"""

import os
import subprocess
import time
from datetime import datetime

import pyautogui
import screen_brightness_control as sbc
import requests
from backend.engine.memory_engine import memory


# ─────────────────────────────────────────────
#  App Registry
# ─────────────────────────────────────────────

DESKTOP_APPS = {
    "vscode": "code",
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "calculator": "calc",
    "notepad": "notepad",
    "terminal": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "whatsapp": "whatsapp:",
    "camera": "start microsoft.windows.camera:",
    "spotify": "spotify",
    "vlc": "vlc",
    "explorer": "explorer",
    "taskmgr": "taskmgr",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}

WEBSITES = {
    "google": "https://google.com",
    "youtube": "https://youtube.com",
    "instagram": "https://instagram.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "facebook": "https://facebook.com",
    "amazon": "https://amazon.in",
    "flipkart": "https://flipkart.com",
    "twitter": "https://twitter.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "netflix": "https://netflix.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
}

# Process names for taskkill
APP_PROCESSES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calculator.exe",
    "spotify": "spotify.exe",
    "vlc": "vlc.exe",
    "vscode": "code.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "whatsapp": "whatsapp.exe",
}


# ─────────────────────────────────────────────
#  App Control
# ─────────────────────────────────────────────

def open_app(name: str) -> str:
    if not name:
        return "App name not specified."

    name_lower = name.lower().strip()

    # 1. Check websites first
    for key, url in WEBSITES.items():
        if key in name_lower:
            subprocess.Popen(f'start {url}', shell=True)
            memory.update_context("active_app", "browser")
            return f"Opening {key}."

    # 2. Check desktop apps
    for key, cmd in DESKTOP_APPS.items():
        if key in name_lower:
            if cmd.endswith(":"):
                subprocess.Popen(f'start {cmd}', shell=True)
            else:
                subprocess.Popen(f'start "" "{cmd}"', shell=True)
            memory.update_context("active_app", key)
            return f"Opening {key}."

    # 3. Fallback: Search Google
    query = name_lower.replace(" ", "+")
    subprocess.Popen(f'start https://www.google.com/search?q={query}', shell=True)
    return f"Couldn't find '{name}' locally. Searching online instead."


def close_app(name: str) -> str:
    if not name:
        return "App name not specified."

    name_lower = name.lower().strip()

    for key, process in APP_PROCESSES.items():
        if key in name_lower:
            result = subprocess.run(
                f'taskkill /f /im {process}',
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"Closed {key}."
            else:
                return f"{key.capitalize()} is not running."

    return f"I don't know how to close '{name}'."


# ─────────────────────────────────────────────
#  System Control
# ─────────────────────────────────────────────

def control_system(action: str, value=None) -> str:
    """Handles volume, brightness, power, media, camera, screenshot."""
    try:
        # ── Volume ──────────────────────────────────────────────
        if action == "volume_up":
            steps = int(value) if value else 5
            for _ in range(min(steps, 20)):
                pyautogui.press("volumeup")
            return "Volume increased."

        elif action == "volume_down":
            steps = int(value) if value else 5
            for _ in range(min(steps, 20)):
                pyautogui.press("volumedown")
            return "Volume decreased."

        elif action == "volume_mute":
            pyautogui.press("volumemute")
            return "Muted."

        elif action == "volume_unmute":
            pyautogui.press("volumemute")
            return "Unmuted."

        # ── Brightness ──────────────────────────────────────────
        elif action == "brightness_up":
            current = sbc.get_brightness(display=0)[0]
            new_val = min(100, current + (int(value) if value else 10))
            sbc.set_brightness(new_val, display=0)
            return f"Brightness increased to {new_val}%."

        elif action == "brightness_down":
            current = sbc.get_brightness(display=0)[0]
            new_val = max(0, current - (int(value) if value else 10))
            sbc.set_brightness(new_val, display=0)
            return f"Brightness decreased to {new_val}%."

        # ── Media Keys ──────────────────────────────────────────
        elif action == "media_playpause":
            pyautogui.press("playpause")
            return "Toggled playback."

        elif action == "media_next":
            pyautogui.press("nexttrack")
            return "Next track."

        elif action == "media_previous":
            pyautogui.press("prevtrack")
            return "Previous track."

        elif action == "media_stop":
            pyautogui.press("stop")
            return "Playback stopped."

        # ── Camera ──────────────────────────────────────────────
        elif action == "open_camera":
            subprocess.Popen("start microsoft.windows.camera:", shell=True)
            return "Camera opened."

        elif action == "take_photo":
            time.sleep(0.5)
            pyautogui.press("enter")
            return "Photo captured."

        # ── Screenshot ──────────────────────────────────────────
        elif action == "take_screenshot":
            folder = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
            os.makedirs(folder, exist_ok=True)
            filename = f"THING_{int(time.time())}.png"
            filepath = os.path.join(folder, filename)
            pyautogui.screenshot(filepath)
            os.startfile(folder)
            return "Screenshot saved."

        # ── Power ───────────────────────────────────────────────
        elif action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "PC locked."

        elif action == "shutdown":
            os.system("shutdown /s /t 5")
            return "Shutting down in 5 seconds."

        elif action == "restart":
            os.system("shutdown /r /t 5")
            return "Restarting in 5 seconds."

        return f"Unknown system action: {action}."

    except Exception as e:
        return f"System control failed: {str(e)}"


# ─────────────────────────────────────────────
#  Time / Date / Search
# ─────────────────────────────────────────────

def get_time() -> str:
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    period = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 or 12
    return f"It's {hour_12}:{minute:02d} {period}."


def get_date() -> str:
    now = datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


def get_weather() -> str:
    try:
        # format=3 returns 'Location: Condition +Temp'
        response = requests.get("https://wttr.in/?format=3", timeout=5)
        if response.status_code == 200:
            return f"The current weather is: {response.text.strip()}"
        return "I couldn't fetch the weather right now."
    except Exception as e:
        return "Weather service is currently offline."


def search_web(query: str) -> str:
    if not query:
        return "No search query provided."
    encoded = query.strip().replace(" ", "+")
    subprocess.Popen(f'start https://www.google.com/search?q={encoded}', shell=True)
    return f"Searching for '{query}'."


def get_cpu_usage() -> str:
    import psutil
    cpu_pct = psutil.cpu_percent(interval=0.1)
    procs = []
    for proc in psutil.process_iter(['name', 'cpu_percent']):
        try:
            info = proc.info
            if info['cpu_percent'] is not None and info['name']:
                procs.append((info['name'], info['cpu_percent']))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    procs.sort(key=lambda x: x[1], reverse=True)
    top_procs = procs[:3]
    top_str = ", ".join([f"{name} ({pct:.1f}%)" for name, pct in top_procs])
    return f"Your CPU usage is currently at {cpu_pct:.1f}%. The top processes are: {top_str}."


def get_ram_usage() -> str:
    import psutil
    mem = psutil.virtual_memory()
    ram_pct = mem.percent
    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    
    procs = []
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            info = proc.info
            if info['memory_info'] and info['name']:
                rss = info['memory_info'].rss / (1024 ** 2) # MB
                procs.append((info['name'], rss))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    procs.sort(key=lambda x: x[1], reverse=True)
    top_procs = procs[:3]
    top_str = ", ".join([f"{name} ({rss:.1f} MB)" for name, rss in top_procs])
    return f"Your RAM usage is at {ram_pct:.1f}% ({used_gb:.1f} GB of {total_gb:.1f} GB used). The heaviest processes are: {top_str}."


def summarize_day() -> str:
    import json
    from backend.engine.memory_engine import memory
    from backend.engine.chat_engine import client
    
    cmd_hist = memory.memory.get("command_history", [])
    chat_hist = memory.memory.get("chat_history", [])
    
    if not cmd_hist and not chat_hist:
        return "You haven't performed any actions or had any chats with me yet today."
        
    prompt = f"""Summarize the user's activities today with THING voice assistant based on the history below.
Be concise, helpful, and natural (1-3 sentences max).

Command History:
{json.dumps(cmd_hist, indent=2)}

Chat History:
{json.dumps(chat_hist, indent=2)}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are THING, summarizing the user's day based on historical interactions. Be concise and conversational."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I had trouble generating your day summary: {str(e)}"
