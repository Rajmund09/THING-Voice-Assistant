"""
llm_intent_classifier.py — THING v4.5
Phase 1: LLM-Driven Intent Classifier

Invoked when the fast regex layer in intent_router.py returns None.
Calls Groq (llama-3.1-8b-instant) with a structured system prompt built from
intent_schema.json, and returns a normalized intent dict in the same format
the rest of the pipeline expects.

Return shape:
    {
        "action":     str,                  # maps to intent "name" in schema
        "entities":   dict,                 # extracted key-value entities
        "confidence": float,                # 0.0 – 1.0
        "multi_step": list[dict] | None,    # populated for compound commands
        "_source":    "llm"                 # metadata tag
    }

    OR None if the LLM returns unknown / confidence < MIN_CONFIDENCE.
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List

from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────

MIN_CONFIDENCE  = 0.55   # Discard results below this threshold
LLM_MODEL       = "llama-3.1-8b-instant"
MAX_TOKENS      = 128
TIMEOUT_SECONDS = 5.0    # Hard deadline for LLM call

_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "intent_schema.json"
)

# ─────────────────────────────────────────────────────────────────
#  Schema + Prompt (loaded once at import time)
# ─────────────────────────────────────────────────────────────────

def _load_schema() -> Dict[str, Any]:
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("intent_schema.json not found at %s", _SCHEMA_PATH)
        return {"intents": []}


def _build_system_prompt(schema: Dict[str, Any]) -> str:
    """Build a compact, token-efficient system prompt from the schema."""
    intent_lines: List[str] = []
    for intent in schema.get("intents", []):
        entities_str = ", ".join(
            f'"{k}": {v}' for k, v in intent.get("entities", {}).items()
        )
        examples_str = " | ".join(intent.get("examples", [])[:3])
        intent_lines.append(
            f'- "{intent["name"]}": {intent["description"]}'
            + (f' [entities: {{{entities_str}}}]' if entities_str else "")
            + (f' [e.g. {examples_str}]' if examples_str else "")
        )

    intents_block = "\n".join(intent_lines)

    return f"""You are a precise intent classification engine for a voice assistant called THING.

Your goal is to map user commands to specific system actions. You will be provided with a "Conversation Context" representing the last few turns of the chat. Use this context to resolve pronouns (e.g., "it", "him", "her", "there", "that").

### OUTPUT FORMAT
Return ONLY a valid JSON object with these exact keys:
  "intent":     string, one of the valid intent names listed below.
  "entities":   object, extracted values. Use null for optional missing fields.
  "confidence": float, 0.0 to 1.0.
  "multi_step": array of {{intent, entities}} objects if the command chains multiple actions, else null.

### VALID INTENTS
{intents_block}

### STRICT RULES
1. Return ONLY valid JSON. No markdown, no explanation, no code fences.
2. Resolve Pronouns: If the user says "send it to him", check the context for what "it" (e.g., a file, message, or link) and "him" (e.g., a contact name) refer to.
3. Multi-Step: For compound commands (e.g. "do X and then Y"), set "intent" to "multi_step" and populate the "multi_step" array.
4. Casual Talk: For greetings, jokes, or factual questions, use "chat".
5. Confidence: If you cannot classify with confidence >= 0.55, use "unknown".
6. Entity Values: Must match the user's intent or the contextually resolved value.
7. Slang: "crank up the tunes" → play_youtube, "kill the lights" → brightness_down, "dim it" → brightness_down.
"""


_schema        = _load_schema()
_system_prompt = _build_system_prompt(_schema)
_client        = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────

from functools import lru_cache

@lru_cache(maxsize=100)
def _classify_intent_cached(command: str, context_str: str) -> Optional[str]:
    """Internal cached call to Groq API."""
    user_input_with_context = f"Conversation Context: {context_str}\nUser Command: {command}"
    
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _system_prompt},
            {"role": "user",   "content": user_input_with_context},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.0,
        timeout=TIMEOUT_SECONDS,
    )
    return response.choices[0].message.content.strip()


def classify_intent_llm(command: str) -> Optional[Dict[str, Any]]:
    """
    Classify a command using the LLM with conversational context.
    """
    t0 = time.perf_counter()
    try:
        # Fetch conversation history for context
        from backend.engine.memory_engine import memory
        history = memory.get_chat_history()
        
        context_str = "None"
        if history:
            # Format last 4 turns: [User: hello] [Assistant: hi]
            context_str = " | ".join([f"[{h['speaker'].capitalize()}: {h['text']}]" for h in history[-4:]])

        user_input_with_context = f"Conversation Context: {context_str}\nUser Command: {command}"

        from backend.core.connectivity_monitor import monitor as connectivity_monitor
        if connectivity_monitor.is_online():
            raw = _classify_intent_cached(command, context_str)
        else:
            from backend.engine.local_llm_provider import classify_intent_local
            logger.info("Using local LLM for intent classification.")
            raw = classify_intent_local(command, _system_prompt, context_str)
            if not raw:
                return None
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug("LLM classifier: %.0fms | context=%s | cmd=%s", elapsed_ms, context_str, command)

        result = _parse_llm_response(raw)
        if result is None:
            return None

        # Log slow calls (target < 800ms per roadmap)
        if elapsed_ms > 1000: # Slightly relaxed for context processing
            logger.warning("LLM classifier exceeded target latency: %.0fms", elapsed_ms)

        return result

    except Exception as exc:
        # ── 1-retry on transient errors (503 / 504 / RateLimit) ──
        err_str = str(exc).lower()
        is_transient = any(code in err_str for code in ["503", "504", "rate_limit", "ratelimit", "timeout", "overloaded"])
        if is_transient:
            logger.warning("LLM transient error, retrying once: %s", exc)
            try:
                _classify_intent_cached.cache_clear()
                raw = _classify_intent_cached(command, context_str)
                result = _parse_llm_response(raw)
                if result:
                    result["_retried"] = True
                return result
            except Exception as retry_exc:
                logger.error("LLM retry also failed: %s", retry_exc)
                return None

        logger.error("LLM classifier error: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> Optional[Dict[str, Any]]:
    """Parse and validate the LLM JSON response into a normalized intent dict."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to salvage JSON from response if wrapped in extra text
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(raw[start:end])
            except json.JSONDecodeError:
                logger.warning("LLM returned unparseable JSON: %s", raw[:200])
                return None
        else:
            logger.warning("LLM returned no JSON: %s", raw[:200])
            return None

    intent_name = data.get("intent", "unknown")
    confidence  = float(data.get("confidence", 0.0))
    entities    = data.get("entities") or {}
    multi_step  = data.get("multi_step")

    # Reject unknown or low-confidence results
    if intent_name == "unknown" or confidence < MIN_CONFIDENCE:
        logger.debug(
            "LLM classifier: low confidence (%.2f) or unknown intent=%s",
            confidence, intent_name
        )
        return None

    # ── Normalize to action-dict format used by the rest of the pipeline ──
    normalized = _normalize_to_action_dict(intent_name, entities, multi_step)
    if normalized is None:
        return None

    normalized["confidence"] = confidence
    normalized["_source"]    = "llm"
    return normalized


def _normalize_to_action_dict(
    intent_name: str,
    entities: Dict[str, Any],
    multi_step: Optional[List[Dict]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Convert (intent_name, entities) → the action dict format that
    action_planner.py and intent_priority_router.py already understand.
    """

    # ── Multi-step compound command ────────────────────────────────────────
    if intent_name == "multi_step" and multi_step:
        steps = []
        for step in multi_step:
            step_action = _normalize_to_action_dict(
                step.get("intent", "unknown"),
                step.get("entities") or {},
            )
            if step_action:
                steps.append(step_action)
        if not steps:
            return None
        return {"action": "multi_step", "steps": steps}

    # ── Chat / fallthrough ─────────────────────────────────────────────────
    if intent_name in ("chat", "unknown"):
        return None  # Caller will forward to chat_engine

    # ── Direct action mappings ─────────────────────────────────────────────
    if intent_name == "open_app":
        return {"action": "open_app", "app_name": entities.get("app_name", "")}

    if intent_name == "close_app":
        return {"action": "close_app", "app_name": entities.get("app_name", "")}

    if intent_name == "play_youtube":
        return {"action": "play_youtube", "query": entities.get("query", "")}

    if intent_name == "media_control":
        return {"action": "media_control", "type": entities.get("type", "pause")}

    if intent_name == "control_system":
        return {
            "action": "control_system",
            "type":   entities.get("type", ""),
            "value":  entities.get("value"),
        }

    if intent_name == "scroll_screen":
        return {
            "action":    "scroll_screen",
            "direction": entities.get("direction", "down"),
            "amount":    int(entities.get("amount") or 300),
        }

    if intent_name == "get_time":
        return {"action": "get_time"}

    if intent_name == "get_date":
        return {"action": "get_date"}

    if intent_name == "get_weather":
        return {"action": "get_weather", "location": entities.get("location")}

    if intent_name == "check_cpu_usage":
        return {"action": "check_cpu_usage"}

    if intent_name == "check_ram_usage":
        return {"action": "check_ram_usage"}

    if intent_name == "summarize_day":
        return {"action": "summarize_day"}

    if intent_name == "search_web":
        return {"action": "search_web", "query": entities.get("query", "")}

    if intent_name == "open_url":
        url = entities.get("url", "")
        if url and not url.startswith("http"):
            url = f"https://{url}"
        return {"action": "open_url", "url": url}

    if intent_name == "type_and_send":
        return {
            "action":      "type_and_send",
            "text":        entities.get("text", ""),
            "press_enter": bool(entities.get("press_enter", False)),
        }

    if intent_name == "send_whatsapp":
        return {
            "action":       "send_whatsapp",
            "contact_name": entities.get("contact_name", ""),
            "message":      entities.get("message", ""),
        }

    if intent_name == "send_sms":
        return {
            "action":       "send_sms",
            "phone_number": entities.get("phone_number", ""),
            "message":      entities.get("message", ""),
        }

    if intent_name == "send_email":
        return {
            "action":       "send_email",
            "contact_name": entities.get("contact_name", ""),
            "content":      entities.get("content", ""),
        }

    if intent_name == "query_about_me":
        return {"action": "query_about_me", "query": entities.get("query", "")}

    if intent_name == "remember_fact":
        return {"action": "remember_fact", "fact": entities.get("fact", "")}

    if intent_name == "forget_fact":
        return {"action": "forget_fact", "fact": entities.get("fact", "")}

    if intent_name == "browser_nav":
        return {"action": "browser_nav", "type": entities.get("type", "back")}

    if intent_name == "stop":
        return {"action": "stop"}

    if intent_name == "vision_query":
        return {"action": "vision_query", "query": entities.get("query", "Describe what is on the screen.")}

    if intent_name == "camera_recognition":
        return {"action": "camera_recognition", "query": entities.get("query", "")}

    if intent_name == "ui_click":
        import re as _re
        raw_target = entities.get("target", "")
        # Strip common filler phrases like "on the", "where you see"
        for _pat in [r"^on\s+the\s+", r"^on\s+", r"^where\s+you\s+see\s+", r"^the\s+"]:
            raw_target = _re.sub(_pat, "", raw_target, flags=_re.IGNORECASE).strip()
        return {"action": "ui_click", "target": raw_target}

    # Unknown intent name not in schema
    logger.warning("LLM returned unmapped intent: %s", intent_name)
    return None
