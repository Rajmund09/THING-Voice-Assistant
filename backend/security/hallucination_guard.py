"""
hallucination_guard.py — THING v6.1
Fast rule-based response validator — no LLM call, no API key needed.
Checks for identity impersonation and sensitive data fabrication via regex.
"""

import re
import logging
from backend.modules.identity_manager import IDENTITY

logger = logging.getLogger(__name__)

# Patterns that indicate the AI is claiming a wrong identity
_IDENTITY_HALLUCINATION = re.compile(
    r"\b(i am|i'm|this is)\s+(gpt|chatgpt|claude|gemini|llama|openai|anthropic|google|meta|bard)\b",
    re.IGNORECASE,
)

# Patterns that indicate fabricated sensitive data
_SENSITIVE_DATA = re.compile(
    r"\b(?:\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}|"  # credit card
    r"\d{3}-\d{2}-\d{4}|"                            # SSN
    r"account\s*(?:number|#|no)?\s*:?\s*\d{6,})\b",  # account numbers
    re.IGNORECASE,
)


def validate_response(response: str, query: str) -> str:
    """
    Fast rule-based validation — no API call needed.
    Blocks identity impersonation and sensitive data fabrication.
    Returns a safe fallback string if a violation is detected.
    """
    try:
        if not response or len(response) < 2:
            return response

        # Check identity impersonation
        if _IDENTITY_HALLUCINATION.search(response):
            logger.warning("[Guard] Identity hallucination detected — correcting")
            creator = IDENTITY.get('creator', 'Raj')
            return f"I am THING, your personal AI assistant created for {creator}'s project."

        # Check sensitive data fabrication (only if not explicitly in the query)
        if _SENSITIVE_DATA.search(response) and not _SENSITIVE_DATA.search(query):
            logger.warning("[Guard] Sensitive data pattern detected in response")
            return "I don't have verified information about private financial data."

        return response

    except Exception as exc:
        logger.error("[Guard] Validation error: %s", exc)
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
