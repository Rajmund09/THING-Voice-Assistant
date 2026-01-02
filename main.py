import speech_recognition as sr
import webbrowser
import MymusicLibrary
import requests
import time
import win32com.client
import subprocess
import datetime
import os
import json
import threading
import re

from clint import get_groq_response

# ================= CONFIG =================
WAKE_WORD = "hey thing"
WAKE_WORDS = ["hey thing", "hey buddy", "hey bro", "thing"]

NEWS_API_KEY = "your-news-api"
MEMORY_FILE = "memory.json"

# ================= SETUP =================
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8
recognizer.energy_threshold = 300

speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Rate = 1
speaker.Volume = 100

SPEAK_THREAD = None

# ================= MEMORY =================
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

memory = load_memory()

# ================= SPEAK (INTERRUPT SAFE) =================
def _speak_async(text):
    speaker.Speak(text, 1)  # async

def speak(text):
    global SPEAK_THREAD
    stop_speaking()
    print("THING:", text)
    SPEAK_THREAD = threading.Thread(target=_speak_async, args=(text,))
    SPEAK_THREAD.start()

def stop_speaking():
    try:
        speaker.Speak("", 2)  # purge instantly
    except:
        pass

# ================= INPUT =================
def take_voice_command():
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=5)
            return recognizer.recognize_google(audio).lower()
    except:
        return None

def take_text_command():
    cmd = input("⌨ Type command (or Enter to speak): ").strip()
    return cmd.lower() if cmd else None

# ================= HELPERS =================
def confirm_action(text):
    speak(text + " Say yes or no.")
    reply = take_text_command() or take_voice_command()
    return reply and any(w in reply for w in ["yes", "haan", "ok", "sure"])

def is_news(cmd):
    return any(w in cmd for w in ["news", "samachar", "khabar", "latest"])

def match_any(command, keywords):
    return any(k in command for k in keywords)

def strip_wake_word(command):
    for w in WAKE_WORDS:
        if w in command:
            return command.replace(w, "").strip()
    return command

# ================= SYSTEM =================
def open_desktop_app(app):
    apps = {
    "vscode": "code",
    "visual studio code": "code",
    "code": "code",

    "chrome": "chrome",
    "google chrome": "chrome",

    "edge": "msedge",

    "calculator": "calc",
    "calc": "calc",

    "notepad": "notepad",

    "terminal": "cmd",
    "cmd": "cmd",

    "powershell": "powershell",

    "explorer": "explorer"
}

    

    if app in apps:
        subprocess.Popen(
            f'start "" {apps[app]}',
            shell=True
        )

        speak(f"Opening {app}")
        return

    speak(f"{app} is not installed. Do you want to open it in browser?")
    if confirm_action("Should I open it online"):
        webbrowser.open(f"https://www.google.com/search?q={app}+download")

def open_file(filename):
    for folder in ["Desktop", "Documents", "Downloads"]:
        path = os.path.join(os.path.expanduser("~"), folder)
        for root, _, files in os.walk(path):
            if filename in files:
                os.startfile(os.path.join(root, filename))
                speak(f"Opening {filename}")
                return
    speak("File not found")

def open_camera():
    speak("Opening camera")
    os.system("start microsoft.windows.camera:")

# ================= VOLUME =================
import pyautogui

def handle_volume(cmd):
    if "up" in cmd:
        pyautogui.press("volumeup")
        speak("Volume increased")

    elif "down" in cmd:
        pyautogui.press("volumedown")
        speak("Volume decreased")

    elif "mute" in cmd:
        pyautogui.press("volumemute")
        speak("Muted")




# ================= BRIGHTNESS =================
import screen_brightness_control as sbc

def handle_brightness(cmd):
    try:
        if "up" in cmd or "increase" in cmd:
            sbc.set_brightness(min(100, sbc.get_brightness()[0] + 10))
            speak("Brightness increased")

        elif "down" in cmd or "decrease" in cmd:
            sbc.set_brightness(max(10, sbc.get_brightness()[0] - 10))
            speak("Brightness decreased")

        else:
            m = re.search(r'(\d+)', cmd)
            if m:
                sbc.set_brightness(int(m.group(1)))
                speak(f"Brightness set to {m.group(1)} percent")
    except:
        speak("Brightness control not supported")


# ================= WEB =================
def open_web(cmd):
    sites = {
        "google": "https://google.com",
        "youtube": "https://youtube.com",
        "instagram": "https://instagram.com",
        "facebook": "https://facebook.com",
        "github": "https://github.com",
        "linkedin": "https://linkedin.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chat.openai.com"
    }

    for k, v in sites.items():
        if k in cmd:
            webbrowser.open(v)
            speak(f"Opening {k}")
            return True
    return False

# ================= MAIN =================
if __name__ == "__main__":
    speak("Thing initialized. Say hey thing to start.")

    while True:
        command = take_text_command() or take_voice_command()
        if not command:
            continue

        # STOP SPEAKING
        if match_any(command, ["stop", "cancel", "enough", "ruk ja", "bas"]):
            stop_speaking()
            continue

        command = strip_wake_word(command)

        # EXIT
        if match_any(command, ["exit", "bye", "goodbye", "band kar"]):
            speak("Goodbye")
            break

        # MEMORY
        elif command.startswith("remember"):
            fact = command.replace("remember", "").strip()
            memory.append(fact)
            save_memory(memory)
            speak("I will remember that")

        elif match_any(command, ["what did you remember", "memory"]):
            if memory:
                speak("Here is what I remember")
                for m in memory:
                    speak(m)
            else:
                speak("I don't remember anything yet")

        # MUSIC
        elif match_any(command, ["play", "bajao", "song"]):
            song = command.replace("play", "").replace("bajao", "").strip()
            if song in MymusicLibrary.voice_alias:
                speak(f"Playing {song}")
                webbrowser.open(MymusicLibrary.music[MymusicLibrary.voice_alias[song]])
            else:
                speak("Song not found")

        # NEWS
        elif is_news(command):
            speak("Fetching news")
            r = requests.get(
                f"https://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey={NEWS_API_KEY}"
            )
            for a in r.json().get("articles", [])[:3]:
                speak(a.get("title"))

        # FILE / APP
        elif command.startswith("open file"):
            open_file(command.replace("open file", "").strip())

        elif match_any(command, ["open camera", "camera kholo", "camera open"]):
            open_camera()

        elif command.startswith("open"):
                if not open_web(command):
                    open_desktop_app(command.replace("open", "").strip())


        elif match_any(command, ["open camera", "camera kholo"]):
            open_camera()

        # VOLUME / BRIGHTNESS
        elif "volume" in command or "sound" in command:
            handle_volume(command)

        elif any(w in command for w in ["brightness", "brighness", "bright"]):
            handle_brightness(command)


        # SHUTDOWN
        elif match_any(command, ["shutdown computer", "pc band kar"]):
            if confirm_action("Are you sure you want to shutdown"):
                os.system("shutdown /s /t 10")

        # AI (LAST)
        else:
            speak(get_groq_response(command))

