"""
action_planner.py — THING v4.0
Multi-step command planner using Groq LLM.
Fixed: removed response_format json_object (caused array wrapping bug).
Uses regex JSON extraction for reliable parsing.
"""

import re
import json
from typing import List, Dict, Any
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PLANNER_SYSTEM = """You are THING's Action Planner. Break complex commands into simple action sequences.
Respond ONLY with a raw JSON array (no markdown, no explanation, no wrapping object).

Valid action types:
- {"action": "open_app", "app_name": "..."}
- {"action": "close_app", "app_name": "..."}
- {"action": "play_youtube", "query": "..."}
- {"action": "control_system", "type": "volume_up|volume_down|volume_mute|brightness_up|brightness_down|lock|shutdown|restart|media_playpause|media_next|media_previous|take_screenshot|open_camera"}
- {"action": "send_whatsapp", "contact_name": "...", "message": "..."}
- {"action": "send_email", "contact_name": "...", "content": "...", "prompt_body": false}
- {"action": "scroll_screen", "direction": "up|down", "amount": 300}
- {"action": "type_and_send", "text": "...", "press_enter": true}
- {"action": "search_web", "query": "..."}
- {"action": "get_time"}
- {"action": "get_date"}
- {"action": "open_url", "url": "https://..."}
- {"action": "vision_query", "query": "..."}
- {"action": "ui_click", "target": "..."}

Examples:
User: open youtube and play punjabi songs
Output: [{"action": "open_app", "app_name": "youtube"}, {"action": "play_youtube", "query": "punjabi songs"}]

User: open whatsapp and message mom i will be late
Output: [{"action": "open_app", "app_name": "whatsapp"}, {"action": "send_whatsapp", "contact_name": "mom", "message": "i will be late"}]

User: take a screenshot and open notepad
Output: [{"action": "control_system", "type": "take_screenshot"}, {"action": "open_app", "app_name": "notepad"}]

User: describe my screen and then lock my pc
Output: [{"action": "vision_query", "query": "describe what is on the screen"}, {"action": "control_system", "type": "lock"}]

User: increase volume and brightness
Output: [{"action": "control_system", "type": "volume_up"}, {"action": "control_system", "type": "brightness_up"}]

CRITICAL RULES:
- Return ONLY the JSON array. No text before or after.
- If unsure, return: [{"action": "search_web", "query": "<the command>"}]
- Never invent actions not listed above.
"""


def plan_actions(command: str) -> List[Dict[str, Any]]:
    """
    Uses Groq to decompose a multi-step command into action list.
    Returns empty list on failure (never hallucinates a fake success).
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM},
                {"role": "user", "content": command},
            ],
            temperature=0.0,
            max_tokens=300,
            # No response_format here — it causes array wrapping bugs
        )

        raw = response.choices[0].message.content.strip()
        return _extract_json_array(raw)

    except Exception as e:
        print(f"[ActionPlanner] Error: {e}")
        return []


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    """
    Robustly extracts a JSON array from text.
    Handles: raw array, wrapped in object, wrapped in markdown code block.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()

    # 1. Direct parse attempt
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return _validate_actions(data)
        if isinstance(data, dict):
            # Look for list value
            for v in data.values():
                if isinstance(v, list):
                    return _validate_actions(v)
            # Single action object
            if "action" in data:
                return _validate_actions([data])
    except json.JSONDecodeError:
        pass

    # 2. Regex extraction — find the first [...] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return _validate_actions(data)
        except json.JSONDecodeError:
            pass

    print(f"[ActionPlanner] Could not parse JSON from: {text[:200]}")
    return []


def _validate_actions(actions: list) -> List[Dict[str, Any]]:
    """Filters out malformed action dicts."""
    valid = []
    valid_types = {
        # Core app & system
        "open_app", "close_app", "control_system", "stop",
        # Media
        "play_youtube", "media_control",
        # Web & typing
        "search_web", "open_url", "type_and_send",
        # Scrolling & time
        "scroll_screen", "get_time", "get_date", "get_weather",
        # Messaging
        "send_whatsapp", "send_sms", "send_number_msg", "send_email",
        # Browser navigation
        "browser_nav",
        # Memory
        "query_about_me", "remember_fact", "forget_fact",
        # Phase 2 — Vision
        "vision_query", "ui_click",
        # Compound (Phase 1)
        "multi_step",
    }
    for a in actions:
        if isinstance(a, dict) and a.get("action") in valid_types:
            valid.append(a)
    return valid
