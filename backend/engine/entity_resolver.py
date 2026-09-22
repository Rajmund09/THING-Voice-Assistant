"""
entity_resolver.py — THING v4.0
Normalizes raw STT text before routing.
Fixes speech recognition artifacts and maps app name synonyms.
"""

import re
import json
import os
from typing import Optional
from backend.engine.alias_engine import expand_command

# ─────────────────────────────────────────────
#  App name normalization map
# ─────────────────────────────────────────────
APP_SYNONYMS = {
    "whats app": "whatsapp",
    "what's app": "whatsapp",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "visual studio": "vscode",
    "you tube": "youtube",
    "you-tube": "youtube",
    "chrome browser": "chrome",
    "google chrome": "chrome",
    "microsoft edge": "edge",
    "ms edge": "edge",
    "ms word": "word",
    "microsoft word": "word",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "file manager": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "command prompt": "cmd",
    "terminal": "cmd",
    "power shell": "powershell",
    "windows terminal": "cmd",
    "note pad": "notepad",
    "paint brush": "mspaint",
    "ms paint": "mspaint",
}

# ─────────────────────────────────────────────
#  Common STT misrecognitions to fix
# ─────────────────────────────────────────────
STT_CORRECTIONS = {
    # WhatsApp
    "wats app": "whatsapp", "watts app": "whatsapp", "whats app": "whatsapp",
    # YouTube
    "u tube": "youtube", "you too": "youtube", "utube": "youtube", "youtub": "youtube",
    # Browsers
    "googles": "google", "chorme": "chrome", "chrme": "chrome", "chrome ium": "chromium",
    # System
    "brite ness": "brightness", "brigtness": "brightness", "brigthness": "brightness",
    "voule": "volume", "volune": "volume", "volum": "volume",
    "shut down": "shutdown", "shudown": "shutdown", "shutdwon": "shutdown",
    "re start": "restart", "rsteart": "restart",
    "lok": "lock", "lcok": "lock",
    # Scroll
    "scrol": "scroll", "scrole": "scroll", "scrool": "scroll",
    "srcoll": "scroll", "scroling": "scrolling", "sroll": "scroll",
    # Apps
    "screenshoot": "screenshot", "screen shot": "screenshot",
    "power point": "powerpoint", "powepoint": "powerpoint",
    "spotify": "spotify", "spotfy": "spotify", "spotifi": "spotify",
    "notepd": "notepad", "note pd": "notepad",
    # Open/Close
    "opne": "open", "oen": "open", "openn": "open",
    "clsoe": "close", "cloze": "close", "colse": "close",
    # Play
    "palay": "play", "paly": "play",
    # Increase/Decrease
    "incrase": "increase", "increae": "increase",
    "decrase": "decrease", "decreae": "decrease",
}

# ─────────────────────────────────────────────
#  Time/date entity patterns
# ─────────────────────────────────────────────
_TIME_PATTERNS = [
    r"\b(what(?:'s| is) the time|current time|time now)\b",
    r"\b(what(?:'s| is) today(?:'s)? date|today(?:'s)? date|current date)\b",
]

# Common known vocabulary for fuzzy matching
_KNOWN_WORDS = [
    "open", "close", "play", "pause", "stop", "scroll", "lock", "restart",
    "shutdown", "volume", "brightness", "screenshot", "youtube", "spotify",
    "whatsapp", "chrome", "notepad", "increase", "decrease", "mute", "unmute",
    "search", "weather", "time", "date", "email", "send", "type",
]


def _fuzzy_correct(word: str) -> str:
    """Returns the closest known word if within edit distance, else original."""
    from difflib import get_close_matches
    if len(word) < 4:
        return word
    matches = get_close_matches(word, _KNOWN_WORDS, n=1, cutoff=0.82)
    return matches[0] if matches else word


def resolve_entities(command: str) -> str:
    """
    Cleans and normalizes a raw STT command string.
    1. Lowercase + strip
    2. Fix STT misrecognitions (exact map)
    3. Fuzzy-correct unknown words against known vocabulary
    4. Normalize app name synonyms
    5. Expand aliases (wp, vs, etc.)
    6. Canonicalize time/date queries
    """
    cmd = command.lower().strip()

    # Fix STT misrecognitions (exact map first — fastest)
    for wrong, right in STT_CORRECTIONS.items():
        cmd = cmd.replace(wrong, right)

    # Fuzzy-correct individual words not in the known map
    words = cmd.split()
    corrected = []
    for w in words:
        # Only attempt fuzzy on likely-unknown words (not short stopwords)
        if len(w) >= 4 and w not in _KNOWN_WORDS:
            corrected.append(_fuzzy_correct(w))
        else:
            corrected.append(w)
    cmd = " ".join(corrected)

    # Normalize app synonyms
    for synonym, canonical in APP_SYNONYMS.items():
        cmd = cmd.replace(synonym, canonical)

    # Expand aliases (wp -> whatsapp, vs -> vscode)
    cmd = expand_command(cmd)

    # Canonicalize time queries → single form
    for pattern in _TIME_PATTERNS:
        if re.search(pattern, cmd):
            if "date" in cmd:
                cmd = "get date"
            else:
                cmd = "get time"
            break

    return cmd


def load_contacts() -> dict:
    """
    Loads the contacts.json mapping {name → phone}.
    Returns empty dict if file doesn't exist.
    """
    contacts_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "contacts.json"
    )
    contacts_path = os.path.normpath(contacts_path)
    if os.path.exists(contacts_path):
        try:
            with open(contacts_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def resolve_contact(name: str) -> Optional[str]:
    """
    Resolves a contact name to a phone number.
    Returns None if not found.
    Checks memory for creator identity first.
    """
    # Priority 1: Check if the name is 'Raj' (the creator)
    from backend.modules.identity_manager import IDENTITY
    if name.lower().strip() == IDENTITY["creator"].lower():
        # Even if not in contacts, treat Raj specially
        return "CREATOR"

    contacts = load_contacts()
    name_lower = name.lower().strip()
    for key, value in contacts.items():
        if key.lower() == name_lower:
            return value
    return None
