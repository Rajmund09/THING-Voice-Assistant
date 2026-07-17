"""
hallucination_guard.py — THING Jarvis Upgrade
Prevents fabrication of sensitive data and inconsistent identity responses using an LLM.
"""

import os
import json
import logging
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv
from backend.modules.identity_manager import IDENTITY

load_dotenv(override=True)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
LLM_MODEL = "llama-3.1-8b-instant"

def validate_response(response: str, query: str) -> str:
    """
    Checks if the assistant's response contains hallucinations.
    Uses an LLM to dynamically evaluate the response.
    Returns a safe fallback if hallucinations or sensitive data leaks are detected.
    """
    try:
        from backend.core.connectivity_monitor import monitor as connectivity_monitor
        if not connectivity_monitor.is_online():
            # If offline, just return response since LLM check won't work
            return response
            
        SYSTEM_PROMPT = f"""You are a security validation module for an AI assistant.
Your job is to detect if the assistant's response contains hallucinations, fabricates sensitive data (like fake bank balances, credit card numbers, or SSNs), or hallucinates an incorrect identity.
The assistant's name is THING, and its creator is {IDENTITY.get('creator', 'Raj')}.

User Query: {query}
Assistant Response: {response}

Output format: Return ONLY a JSON object with two keys:
"is_safe": boolean (true if safe, false if it contains hallucinations or sensitive data fabrication)
"reason": short string explanation

Consider it NOT SAFE if:
1. It claims to be an AI from OpenAI, Anthropic, Google, or Meta instead of THING.
2. It hallucinates private financial data, account numbers, or balances that weren't in the user's prompt (unless the user asked to send a message containing those).
"""
        
        res = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": SYSTEM_PROMPT}],
            response_format={"type": "json_object"},
            max_tokens=150,
            temperature=0.0
        )
        
        raw_result = res.choices[0].message.content
        result = json.loads(raw_result)
        
        if not result.get("is_safe", True):
            logger.warning("Hallucination guard blocked response. Reason: %s", result.get("reason"))
            reason_lower = result.get("reason", "").lower()
            if "identity" in reason_lower or "creator" in reason_lower or "name" in reason_lower:
                return f"I am THING, your personal AI assistant created for {IDENTITY.get('creator', 'Raj')}'s project."
            return "I don't have verified information about private data or bank accounts."
            
        return response
    except Exception as e:
        logger.error("Hallucination guard LLM error: %s", e)
        # Fallback to returning the response if the check fails
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
