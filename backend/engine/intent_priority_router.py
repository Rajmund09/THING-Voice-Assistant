"""
intent_priority_router.py — THING v4.5
Priority-based routing with FSM state awareness.
Now handles multi_step compound intents from the LLM classifier (Phase 1).
"""

import re
from typing import Dict, Any, Optional
from backend.engine.state_manager import state_manager, AssistantState
from backend.engine.intent_router import get_local_intent
from backend.engine.query_classifier import classify_query, is_fast_chat


def route_intent(command: str) -> Dict[str, Any]:
    """
    Routes a cleaned command based on current FSM state and content.
    Priority order:
      1. Global stop/cancel (always handled)
      2. Confirmation state (yes/no responses)
      3. App context (WhatsApp/YouTube shortcuts)
      4. Local regex intent
      5. Query classifier (LIVE_DATA / KNOWLEDGE / CHAT)
    """
    cmd = command.lower().strip()
    
    # ── 0. Fast Chat Path (GREETINGS) ────────────────────────────
    # Bypass all logic for simple greetings to reduce latency (< 5ms)
    if is_fast_chat(cmd):
        return {"type": "CHAT"}

    # ── 1. Global stop/cancel ────────────────────────────────────
    STOP_WORDS = ["stop", "cancel", "abort", "never mind", "forget it", "ruk", "band karo"]
    if any(cmd == w or cmd.startswith(w + " ") for w in STOP_WORDS):
        state_manager.clear_pending_action()
        return {"type": "LOCAL", "intent": {"action": "stop"}, "response": "Stopped."}

    # ── 2. Confirmation state ────────────────────────────────────
    if state_manager.current_state == AssistantState.WAIT_CONFIRMATION:
        YES_WORDS = ["yes", "yeah", "yep", "sure", "ok", "okay", "proceed", "do it",
                     "send", "confirm", "haan", "ha", "ji"]
        NO_WORDS = ["no", "nope", "don't", "dont", "cancel", "nahin", "nahi", "abort"]

        if any(w in cmd for w in YES_WORDS):
            action = state_manager.pending_action
            state_manager.clear_pending_action()
            return {"type": "EXECUTE_PENDING", "action": action}

        if any(w in cmd for w in NO_WORDS):
            state_manager.clear_pending_action()
            return {"type": "CANCEL_PENDING", "response": "Cancelled."}

        # Ambiguous — ask again (skip LLM to avoid latency in tight confirmation loop)
        return {
            "type": "CHAT",
            "response": "Please say yes to proceed or no to cancel.",
        }

    # ── 3. App context shortcuts ─────────────────────────────────
    if state_manager.active_app == "whatsapp":
        wa_intent = _parse_whatsapp_context(cmd)
        if wa_intent:
            return {"type": "LOCAL", "intent": wa_intent}

    if state_manager.active_app == "youtube":
        yt_intent = _parse_youtube_context(cmd)
        if yt_intent:
            return {"type": "LOCAL", "intent": yt_intent}

    # ── 4. Hybrid intent match (regex → fuzzy → LLM) ────────────
    local_intent = get_local_intent(cmd)
    if local_intent:
        # Handle multi-step compound commands from LLM classifier
        if local_intent.get("action") == "multi_step":
            return {"type": "MULTI_STEP", "steps": local_intent.get("steps", [])}
        return {"type": "LOCAL", "intent": local_intent}

    # ── 5. Classify and forward ──────────────────────────────────
    query_type = classify_query(cmd)
    return {"type": query_type}


def _parse_whatsapp_context(command: str) -> Optional[Dict[str, Any]]:
    """Context-aware parsing when WhatsApp is the active app."""
    # "type [text]" → type in active chat
    if command.startswith("type "):
        return {"action": "type_and_send", "text": command[5:].strip(), "press_enter": True}

    # "go to [name]" → navigate to contact
    if command.startswith("go to "):
        name = command[6:].strip()
        return {"action": "open_app", "app_name": f"whatsapp {name}"}

    # Generic: if not a system command, treat as message to active contact.
    # Strip leading verb words (message/send/msg/text) so:
    #   "message bro hey" → contact="bro", message="hey"  (NOT contact="message")
    #   "bro hey"         → contact="bro", message="hey"
    if not get_local_intent(command, use_llm_fallback=False):
        words = command.split()
        _VERBS = {"message", "send", "msg", "text"}
        if words and words[0].lower() in _VERBS:
            words = words[1:]  # drop the verb
        if len(words) >= 2:
            return {
                "action": "send_whatsapp",
                "contact_name": words[0],
                "message": " ".join(words[1:]),
            }
        elif len(words) == 1:
            # Only a contact name given, no message — ask for message
            return {
                "action": "send_whatsapp",
                "contact_name": words[0],
                "message": "",
                "prompt_message": True,
            }

    return None


def _parse_youtube_context(command: str) -> Optional[Dict[str, Any]]:
    """Context-aware parsing when YouTube is the active app."""
    if command in ["pause", "play", "resume"]:
        return {"action": "control_system", "type": "media_playpause"}
    if command in ["next", "skip"]:
        return {"action": "control_system", "type": "media_next"}
    if command in ["previous", "prev", "back"]:
        return {"action": "control_system", "type": "media_previous"}
    if command in ["mute"]:
        return {"action": "control_system", "type": "volume_mute"}
    return None
