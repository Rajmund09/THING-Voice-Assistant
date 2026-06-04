"""
response_manager.py — THING v4.0
Single factory for all response packets.
Guarantees voice text == display text at all times.
"""

import uuid
import time
import re
from typing import Optional


# ─────────────────────────────────────────────
#  Patterns that signal hallucinated/verbose AI bloat
# ─────────────────────────────────────────────
_BLOAT_PATTERNS = [
    r"^(Sure|Certainly|Of course|Absolutely|Great|No problem)[,!]?\s*",
    r"^(As an AI|As a language model|I am an AI)[,.]?\s*",
    r"^(Based on the context|Based on the information)[,.]?\s*",
    r"^(I'd be happy to|I would be happy to)\s*",
    r"^(Let me|Allow me to)\s*(help|assist)\s*(you)?\s*",
]

_BLOAT_RE = [re.compile(p, re.IGNORECASE) for p in _BLOAT_PATTERNS]


def format_premium_response(text: str) -> str:
    """
    Strips verbose AI preamble and enforces THING's short, sharp style.
    Ensures the text is suitable for both display and TTS.
    """
    if not text:
        return ""

    text = text.strip()

    # Strip bloat openers
    for pattern in _BLOAT_RE:
        text = pattern.sub("", text)

    text = text.strip()

    # Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # Trim extremely long responses to keep TTS snappy
    sentences = text.split(". ")
    if len(sentences) > 4:
        text = ". ".join(sentences[:4]).rstrip(".") + "."

    return text


def build_response_packet(
    action: str,
    final_response: str,
    success: bool,
    speak_text: Optional[str] = None,
    data: Optional[dict] = None,
) -> dict:
    """
    Builds the canonical ResponsePacket that is:
      1. Emitted via socket to frontend (for display)
      2. Passed to audio.speak() (for TTS)

    This is the SINGLE source of truth — voice and text are ALWAYS in sync.

    Schema:
    {
        "id": str (UUID4),
        "timestamp": float (unix),
        "action": str,
        "final_response": str,   ← what frontend displays
        "speak_text": str,       ← what TTS speaks (same unless overridden)
        "success": bool
    }
    """
    cleaned = format_premium_response(final_response)

    # speak_text defaults to final_response if not overridden
    speak = format_premium_response(speak_text) if speak_text else cleaned

    return {
        "id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "action": action,
        "final_response": cleaned,
        "speak_text": speak,
        "success": success,
        "data": data,
    }


def error_packet(action: str, error_msg: str) -> dict:
    """Convenience builder for honest failure responses."""
    return build_response_packet(
        action=action,
        final_response=error_msg,
        success=False,
    )


def success_packet(action: str, message: str) -> dict:
    """Convenience builder for successful action responses."""
    return build_response_packet(
        action=action,
        final_response=message,
        success=True,
    )
