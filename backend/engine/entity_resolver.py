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
    "wats app": "whatsapp",
    "watts app": "whatsapp",
    "u tube": "youtube",
    "you too": "youtube",
    "googles": "google",
    "chrome ium": "chromium",
    "brite ness": "brightness",
    "voule": "volume",
    "scrol": "scroll",
    "screenshoot": "screenshot",
    "screen shot": "screenshot",
    "shut down": "shutdown",
    "re start": "restart",
    "power point": "powerpoint",
}

# ─────────────────────────────────────────────
#  Time/date entity patterns
# ─────────────────────────────────────────────
_TIME_PATTERNS = [
    r"\b(what(?:'s| is) the time|current time|time now)\b",
    r"\b(what(?:'s| is) today(?:'s)? date|today(?:'s)? date|current date)\b",
]


def resolve_entities(command: str) -> str:
    """
    Cleans and normalizes a raw STT command string.
    1. Lowercase + strip
    2. Fix STT misrecognitions
    3. Normalize app name synonyms
    4. Expand aliases (wp, vs, etc.)
    5. Canonicalize time/date queries
    """
    cmd = command.lower().strip()

    # Fix STT misrecognitions
    for wrong, right in STT_CORRECTIONS.items():
        cmd = cmd.replace(wrong, right)

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
