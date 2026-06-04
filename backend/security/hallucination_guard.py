"""
hallucination_guard.py — THING Jarvis Upgrade
Prevents fabrication of sensitive data and inconsistent identity responses.
"""

import re
from backend.modules.identity_manager import IDENTITY

# Patterns for sensitive data that should NEVER be fabricated
SENSITIVE_PATTERNS = [
    r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit Card
    r"\b\d{11,18}\b",                            # Generic Bank Account Number (11+ digits)
    r"balance is \d+",                           # Fake bank balance
    r"account number:? \d+",                     # Explicit account number claim
]

# Identity keywords that might trigger a conflict
IDENTITY_KEYWORDS = ["made you", "developed you", "created you", "your developer", "who are you"]

def validate_response(response: str, query: str) -> str:
    """
    Checks if the assistant's response contains hallucinations.
    If it does, returns a safe fallback.
    """
    res_lower = response.lower()
    
    # 1. Check for fabricated sensitive data
    # Bypass check if the user is clearly performing a messaging action (legitimate number usage)
    MESSAGING_KEYWORDS = ["send", "message", "msg", "text", "whatsapp", "sms", "email"]
    is_messaging = any(k in query.lower() for k in MESSAGING_KEYWORDS)
    
    if not is_messaging:
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, response):
                return "I don't have verified information about private data or bank accounts."

    # 2. Check for Identity conflicts
    # If the user asked about identity and the response mentions something other than Raj
    query_lower = query.lower()
    if any(k in query_lower for k in IDENTITY_KEYWORDS):
        if "raj" not in res_lower and any(wrong in res_lower for wrong in ["meta", "google", "openai", "openai", "anthropic"]):
            return f"I am THING, your personal AI assistant created for {IDENTITY['creator']}'s project."

    return response

def get_confidence_score(response: str) -> float:
    """
    Placeholder for more advanced confidence scoring.
    Returns 1.0 for now if no red flags are found.
    """
    # If response is too short or contains weird characters, lower score
    if len(response) < 2: return 0.1
    return 1.0


def validate_click_coordinates(coords: dict, screen_w: int, screen_h: int) -> bool:
    """
    Phase 2 Safety Gate — validates coordinates from Gemini Vision before executing a click.

    Returns True if safe to click, False if the coordinates are suspicious.

    Guards against:
    - None / missing coordinates
    - Coordinates outside the actual screen resolution
    - Coordinates exactly at (0, 0) — likely a hallucination
    - Coordinates in the extreme top-left corner (failsafe zone)
    """
    if not coords:
        return False

    x = coords.get("x")
    y = coords.get("y")

    if x is None or y is None:
        return False

    # Reject (0, 0) — highly likely a hallucination or default value
    if x == 0 and y == 0:
        return False

    # Reject top-left 10px corner — PyAutoGUI FAILSAFE zone
    if x < 10 and y < 10:
        return False

    # Reject out-of-bounds
    if not (0 <= x < screen_w and 0 <= y < screen_h):
        return False

    return True
