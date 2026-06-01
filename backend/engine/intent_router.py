"""
intent_router.py — THING v4.5
Hybrid intent routing:
  Layer 1 — Fast compiled regex (< 20ms)
  Layer 2 — Fuzzy string correction for near-misses
  Layer 3 — LLM structured-output classifier (< 800ms) [Phase 1]
"""

import re
import logging
from typing import Dict, Any, Optional
from fuzzywuzzy import process as fuzz_process

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Compiled Intent Patterns
# ─────────────────────────────────────────────
# Each entry: (pattern, intent_name)
# Patterns are checked in ORDER — more specific first.

PATTERNS = [
    # ── App Control (Specifics First) ───────────────────────────
    (r"^(open|go to|navigate to|visit)\s+(https?://.+)$",        "open_url"),
    (r"^(open|go to)\s+(www\..+)$",                              "open_url"),
    (r"^(open|go to)\s+([\w-]+\.(?:com|org|net|io|edu|gov|me|in|uk))(?:\/.*)?$", "open_url"),
    (r"^(new\s+tab)$",                                           "browser_new_tab"),
    (r"^(close\s+tab|close\s+this\s+tab|close\s+current\s+tab)$",   "browser_close_tab"),
    # MUST be before close_app — "close [name] tab" → Vision-click the X on that tab
    (r"^close\s+(.+?)\s+tab$",                                       "close_named_tab"),

    # ── App Control (Generic Fallback) ──────────────────────────
    (r"^(open|launch|start)\s+(.+)$",                    "open_app"),
    (r"^(close|kill|quit|exit)\s+(.+)$",                 "close_app"),

    # ── Spotify SDK (Phase 4B) — MUST be before play_youtube / media_control ───
    # These patterns require the explicit word 'spotify' so they can't be
    # confused with generic YouTube / system-media controls.
    (r"^(?:play|put on|start)\s+(.+?)\s+on\s+spotify$",          "spotify_play"),
    (r"^(?:play|put on)\s+(?:my\s+)?(.+?)\s+(?:spotify\s+)?playlist$", "spotify_play"),
    (r"^(?:pause|stop)\s+spotify$",                               "spotify_pause"),
    (r"^spotify\s+(?:pause|stop)$",                               "spotify_pause"),
    (r"^(?:resume|unpause|continue)\s+spotify$",                  "spotify_resume"),
    (r"^spotify\s+(?:resume|unpause)$",                           "spotify_resume"),
    (r"^(?:skip|next)\s+(?:on\s+)?spotify$",                     "spotify_skip"),
    (r"^spotify\s+(?:skip|next)$",                                "spotify_skip"),
    (r"^(?:previous|prev|back)\s+(?:on\s+)?spotify$",            "spotify_previous"),
    (r"^spotify\s+(?:previous|prev|back)$",                       "spotify_previous"),
    (r"^(?:set\s+)?spotify\s+volume\s+(?:to\s+)?(\d+)(?:\s+percent)?$", "spotify_volume"),
    (r"^(?:what(?:'s| is) (?:playing|on) (?:on )?spotify|current spotify(?: track| song)?)$", "spotify_now_playing"),

    # ── Media / YouTube ─────────────────────────────────────────
    (r"^(play|search youtube for|find on youtube)\s+(?!(?:spotify|music|song|playback|video|audio)$)(.+)$", "play_youtube"),
    (r"^(pause|resume|play|unpause)(?:\s+(?:the\s+)?(video|music|song|playback|spotify))?$",  "media_control"),
    (r"^(next|skip)\s*(song|video|track)?$",             "media_control"),
    (r"^(previous|prev|back)\s*(song|video|track)?$",    "media_control"),
    (r"^(stop)\s+(music|video|song|playback)$",          "media_control"),
    (r"^(fullscreen|full screen|maximize video)$",      "media_control"),
    (r"^(skip)\s+(forward|ahead|back|backward)$",        "media_control"),

    # ── Volume ──────────────────────────────────────────────────
    (r"^(volume|vol)\s+(up|down|mute|unmute)(?:\s+(\d+))?$",          "volume_control"),
    (r"^(increase|decrease|reduce|lower|raise)\s+(?:the\s+)?(volume|vol)(?:\s+by\s+(\d+))?$", "volume_control_alt"),
    (r"^(mute|unmute)(?:\s+(?:the\s+)?(?:volume|sound|audio))?$",                "volume_mute"),

    # ── Brightness ──────────────────────────────────────────────
    (r"^(brightness|screen)\s+(up|down|low|high|max|min)(?:\s+(\d+))?$", "brightness_control"),
    (r"^(increase|decrease|reduce|lower|raise)\s+(brightness|screen brightness)(?:\s+by\s+(\d+))?$", "brightness_alt"),

    # ── Screenshot / Camera ─────────────────────────────────────
    (r"^(take|capture|grab)\s+(?:a\s+)?(screenshot|screen shot|snap)$",  "take_screenshot"),
    (r"^(take|capture|click)\s+(?:a\s+)?(photo|pic|picture|selfie)$",    "take_photo"),
    (r"^(open|start|launch)\s+(camera|webcam)$",               "open_camera"),

    # ── Scrolling ────────────────────────────────────────────────
    (r"^(scroll)\s+(up|down)(?:\s+(\d+))?$",             "scroll_screen"),
    (r"^(?:go\s+|scroll\s+)?(to\s+)?(top|bottom)(?:\s+(?:of\s+)?(?:the\s+)?page)?$", "scroll_edge"),

    # ── System / Power ──────────────────────────────────────────
    (r"^(lock)(?:\s+(?:my\s+)?(?:pc|computer|laptop|screen))?$",       "power_control_lock"),
    (r"^(shutdown|shut\s+down|turn\s+off)(?:\s+pc|\s+computer|\s+laptop)?$", "power_control_shutdown"),
    (r"^(restart|reboot)(?:\s+pc|\s+computer|\s+laptop)?$",     "power_control_restart"),

    # ── Time / Date / Weather ───────────────────────────────────
    (r"^(?:what.*time.*|time|whats the time|what's the time|get time)$", "get_time"),
    (r"^(?:what.*date.*|date|whats the date|what's the date|get date|today's date)$", "get_date"),
    (r"^(?:.*weather.*)$", "get_weather"),
    (r"^(?:check|show|get|whats|what is|how is)\s+(?:the\s+)?(?:cpu|processor)(?:\s+usage|\s+load)?$", "check_cpu_usage"),
    (r"^(?:check|show|get|whats|what is|how is)\s+(?:the\s+)?(?:ram|memory)(?:\s+usage|\s+load)?$", "check_ram_usage"),
    (r"^(?:summarize|summary\s+of|how was|show\s+my|get\s+my)\s+(?:my\s+)?day$", "summarize_day"),
    (r"^(?:open|go to)(?:\s+the)?\s+(?:meeting\s+link|url)\s+(?:from|in)\s+(?:my\s+)?clipboard$", "open_clipboard_url"),

    # ── Web Search ──────────────────────────────────────────────
    (r"^(search|google|find|look up|search for)\s+(.+)$",        "search_web"),

    # ── Typing ──────────────────────────────────────────────────
    (r"^(type|write|input)\s+(?:msg|message\s+)?(.+)$",          "type_text"),

    # ── Email ────────────────────────────────────────────
    # NOTE: email patterns MUST appear before send_whatsapp — 'send' verb is shared.
    (r"^(send|compose|write)\s+(?:an?\s+)?(mail|email)\s+to\s+([\w.@+-]+)\s+(.+)$", "send_email"),
    (r"^(send|compose|write)\s+(?:an?\s+)?(mail|email)\s+to\s+([\w.@+-]+)$",       "send_email_prompt"),
    (r"^(send|compose|write)\s+(?:an?\s+)?(mail|email)$",                           "send_email_nocontact"),
    (r"^(open)\s+(?:my\s+)?(mail|email|gmail|inbox)$",                              "open_email"),
    (r"^(email|mail)\s+to\s+([\w.@+-]+)(?:\s+(.+))?$",                             "send_email_short"),

    # ── SMS / Normal Messaging (Explicit) ──────────────────────────────────
    (r"^(?:send\s+)?(?:sms|normal\s+msg|text)\s+(.+)\s+to\s+(\+?\d[\d\s-]{8,})$", "send_sms_reverse"),
    (r"^(?:send\s+)?(?:sms|normal\s+msg|text)\s+(?:to\s+)?(\+?\d[\d\s-]{8,})\s+(.+)$", "send_sms"),
    
    # ── WhatsApp Number Messaging (Default for numbers) ────────────────────
    # Pattern: send [message] to [number] -> WhatsApp Browser
    (r"^(?:send|message|msg|text)\s+(.+)\s+to\s+(\+?\d[\d\s-]{8,})$", "send_number_msg_reverse"),
    # Pattern: send to [number] [message] -> WhatsApp Browser
    (r"^(?:send|message|msg|text)\s+(?:to\s+)?(\+?\d[\d\s-]{8,})\s+(.+)$", "send_number_msg"),

    # ── WhatsApp Contact Messaging ──────────────────────────────────────────
    # Improved pattern to avoid capturing 'message' as a name
    (r"^(?:send|message|msg|text)\s+(?:a?\s*message\s+to\s+|to\s+)?([a-zA-Z]{2,})\s+(.+)$",  "send_whatsapp"),
    (r"^(whatsapp|open\s+whatsapp)$",                                                "open_whatsapp"),

    # ── Memory / About Me ─────────────────────────────────────────
    (r"^(who\s+is|who\s+am|tell\s+me\s+about)\s+(me|my|raj|the\s+user)(?:\s+(.+))?$", "query_about_me"),
    (r"^(what\s+does|what\s+are)\s+(me|my|raj|the\s+user)\s+(.+)$", "query_about_me"),
    (r"^(remember)\s+(.+)$",                                  "remember_fact"),
    (r"^(forget)\s+(.+)$",                                    "forget_fact"),
    (r"^(show|what)\s+do\s+you\s+know\s+about\s+(me|raj)$",  "query_about_me"),
    (r"^(who\s+am\s+i(?:\s+to\s+you)?)$",                    "query_about_me"),

    # ── Stop / Cancel ────────────────────────────────────────────
    (r"^(stop|cancel|abort|never\s+mind|forget\s+it)$",          "stop_execution"),

    # ── Spotify SDK (Phase 4B) — duplicate anchor (kept for clarity, real patterns above) ──
    # The actual Spotify patterns are hoisted above play_youtube/media_control at the top
    # of the PATTERNS list so they take priority. These entries below are intentionally
    # removed to avoid double-registration — DO NOT add them back here.

    # ── Google Calendar (Phase 4B) ───────────────────────────────
    (r"^(?:what(?:'s| is)|do i have|any|show)\s+(?:on\s+)?(?:my\s+)?(?:calendar|schedule|meetings?|events?)\s+(today)$", "calendar_today"),
    (r"^(?:what(?:'s| is)|do i have|any|show)\s+(?:on\s+)?(?:my\s+)?(?:calendar|schedule|meetings?|events?)\s+(tomorrow)$", "calendar_tomorrow"),
    (r"^(?:what(?:'s| is)|do i have|any|show)\s+(?:on\s+)?(?:my\s+)?(?:calendar|schedule|meetings?|events?)\s+(?:this\s+)?(week)$", "calendar_week"),
    (r"^(?:my\s+)?(?:calendar|schedule)\s+(?:for\s+)?(today|tomorrow|this week)$", "calendar_generic"),
    (r"^(?:create|add|schedule|book)\s+(?:an?\s+)?(?:event|meeting|appointment)\s+(.+)$", "calendar_create"),

    # ── Slack (Phase 4B) ─────────────────────────────────────────
    (r"^(?:send\s+)?(?:a\s+)?(?:slack\s+)?(?:message|msg)\s+(?:to\s+)?#?([\w-]+)\s+(?:saying|:)\s+(.+)$", "slack_send"),
    (r"^(?:post|message|msg)\s+(?:in\s+|to\s+)?#?([\w-]+)\s+(?:on\s+)?slack:\s*(.+)$", "slack_send_alt"),
    (r"^(?:read|check|show)\s+(?:last\s+(\d+)\s+)?(?:messages?|msgs?)\s+(?:in\s+|from\s+)?#?([\w-]+)(?:\s+on\s+slack)?$", "slack_read"),
    (r"^(?:list|show|what(?:'s| are))\s+(?:my\s+)?slack\s+channels?$", "slack_channels"),

    # ── Navigation ──────────────────────────────────────────────
    (r"^(go\s+back|back|previous\s+page)$",                      "browser_back"),
    (r"^(refresh|reload)(?:\s+page|\s+tab)?$",                   "browser_refresh"),

    # ── Vision / Screen Analysis (Phase 2) ──────────────────────
    # NOTE: These must come BEFORE ui_click to avoid 'click' matching vision queries.
    (r"^(?:what(?:'s| is) on (?:my )?screen)$",                                  "vision_query_screen"),
    (r"^(?:describe|look at|analyze|analyse)\s+(?:my\s+)?screen$",               "vision_query_screen"),
    (r"^(read|summarize|explain|describe)\s+(?:the\s+|this\s+)?(?:screen|document|doc|page|error(?:\s+message)?|graph|chart|image|this)$", "vision_query_doc"),
    (r"^(?:what does (?:that|this|it) say)$",                                    "vision_query_screen"),
    (r"^(?:tell me what you see)$",                                               "vision_query_screen"),

    # ── Camera / Webcam Recognition ─────────────────────────────
    (r"^(?:look at me|who am i|scan me|recognize me|what am i doing|who is in front of the camera|who is in the camera|who is that|describe (?:my )?surroundings|describe (?:the )?room|scan (?:the )?environment|can you see me|do you see me|are you looking at me|can you see what i'm doing|see me|webcam scan)$", "camera_recognition"),
    (r"^(?:scan|recognize)\s+(?:another\s+person|someone\s+else|them)$", "camera_recognition"),

    # ── UI Click (Phase 2) ──────────────────────────────────────────────
    # Handles: click X, click on X, click on the X, click where you see X
    (r"^(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(?:where\s+(?:you\s+)?see\s+)?(?:when\s+.+?is\s+written\s+)?(.+?)(?:\s+button|\s+icon|\s+link|\s+tab)?$", "ui_click"),
]

COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), name) for p, name in PATTERNS]

# Fuzzy candidates for near-miss matching
FUZZY_COMMANDS = [
    "open", "close", "play", "pause", "stop", "volume up", "volume down",
    "brightness up", "brightness down", "screenshot", "scroll up", "scroll down",
    "shutdown", "restart", "lock", "search", "mute", "type",
    "describe screen", "click",
    "play on spotify", "pause spotify", "skip spotify",
    "calendar today", "calendar tomorrow",
    "slack message",
]


def get_local_intent(command: str, use_llm_fallback: bool = True) -> Optional[Dict[str, Any]]:
    """
    Hybrid intent matcher — three-layer cascade:

    1. Direct regex match on compiled patterns  (target: < 20ms)
    2. Fuzzy correction + re-match              (near-miss handling)
    3. LLM structured-output classifier         (target: < 800ms)

    Args:
        command: Cleaned user command string.
        use_llm_fallback: Set False to skip LLM (e.g. in confirmation loops).

    Returns:
        Action dict recognized by action_planner.py, or None.
    """
    cmd = command.lower().strip()

    # ── Layer 1: Direct regex match ────────────────────────────────
    for pattern, intent_name in COMPILED_PATTERNS:
        match = pattern.match(cmd)
        if match:
            result = _build_intent(intent_name, match)
            if result:
                logger.debug("Intent matched via regex: %s", intent_name)
                return result

    # ── Layer 2: Fuzzy fallback (typos / speech-recognition errors) ─
    best, score = fuzz_process.extractOne(cmd, FUZZY_COMMANDS)
    if score >= 80:
        corrected = _correct_command(cmd, best)
        if corrected and corrected != cmd:
            for pattern, intent_name in COMPILED_PATTERNS:
                match = pattern.match(corrected)
                if match:
                    result = _build_intent(intent_name, match)
                    if result:
                        logger.debug(
                            "Intent matched via fuzzy (%s→%s): %s",
                            cmd, corrected, intent_name
                        )
                        return result

    # ── Layer 3: LLM classifier (handles paraphrasing / multi-step) ─
    if use_llm_fallback:
        try:
            from backend.engine.llm_intent_classifier import classify_intent_llm
            llm_result = classify_intent_llm(cmd)
            if llm_result:
                logger.debug(
                    "Intent matched via LLM (confidence=%.2f): %s",
                    llm_result.get("confidence", 0),
                    llm_result.get("action", "?")
                )
                return llm_result
        except Exception as exc:
            logger.error("LLM fallback error: %s", exc)

    return None


def _build_intent(intent_name: str, match: re.Match) -> Optional[Dict[str, Any]]:
    """Maps a regex match to a structured action dict."""
    g = match.groups()

    if intent_name == "open_app":
        return {"action": "open_app", "app_name": g[1].strip()}

    elif intent_name == "close_app":
        return {"action": "close_app", "app_name": g[1].strip()}

    elif intent_name == "play_youtube":
        return {"action": "play_youtube", "query": g[1].strip()}

    elif intent_name == "media_control":
        action_word = g[0].lower()
        if len(g) > 1 and g[1]:
            action_word = f"{action_word}_{g[1]}"
        return {"action": "media_control", "type": action_word}

    elif intent_name == "volume_control":
        direction = g[1].lower()
        val = int(g[2]) if len(g) > 2 and g[2] else None
        return {"action": "control_system", "type": f"volume_{direction}", "value": val}

    elif intent_name == "volume_control_alt":
        action_word = g[0].lower()
        direction = "up" if action_word in ("increase", "raise") else "down"
        val = int(g[2]) if len(g) > 2 and g[2] else None
        return {"action": "control_system", "type": f"volume_{direction}", "value": val}

    elif intent_name == "volume_mute":
        mute_type = "volume_mute" if g[0].lower() == "mute" else "volume_unmute"
        return {"action": "control_system", "type": mute_type}

    elif intent_name == "brightness_control":
        direction = g[1].lower()
        if direction in ("low", "min", "down"):
            dir_str = "down"
        else:
            dir_str = "up"
        val = int(g[2]) if len(g) > 2 and g[2] else None
        return {"action": "control_system", "type": f"brightness_{dir_str}", "value": val}

    elif intent_name == "brightness_alt":
        action_word = g[0].lower()
        direction = "up" if action_word in ("increase", "raise") else "down"
        val = int(g[2]) if len(g) > 2 and g[2] else None
        return {"action": "control_system", "type": f"brightness_{direction}", "value": val}

    elif intent_name == "take_screenshot":
        return {"action": "control_system", "type": "take_screenshot"}

    elif intent_name == "take_photo":
        return {"action": "control_system", "type": "take_photo"}

    elif intent_name == "open_camera":
        return {"action": "control_system", "type": "open_camera"}

    elif intent_name == "scroll_screen":
        direction = g[1].lower()
        amount = int(g[2]) if len(g) > 2 and g[2] else 300
        return {"action": "scroll_screen", "direction": direction, "amount": amount}

    elif intent_name == "scroll_edge":
        edge = g[-1].lower() if g else "top"
        direction = "down" if edge == "bottom" else "up"
        return {"action": "scroll_screen", "direction": direction, "amount": 9999}

    elif intent_name == "power_control_lock":
        return {"action": "control_system", "type": "lock"}

    elif intent_name == "power_control_shutdown":
        return {"action": "control_system", "type": "shutdown"}

    elif intent_name == "power_control_restart":
        return {"action": "control_system", "type": "restart"}

    elif intent_name == "get_time":
        return {"action": "get_time"}

    elif intent_name == "get_date":
        return {"action": "get_date"}

    elif intent_name == "get_weather":
        return {"action": "get_weather"}

    elif intent_name == "check_cpu_usage":
        return {"action": "check_cpu_usage"}

    elif intent_name == "check_ram_usage":
        return {"action": "check_ram_usage"}

    elif intent_name == "summarize_day":
        return {"action": "summarize_day"}

    elif intent_name == "open_clipboard_url":
        import pyperclip
        url = pyperclip.paste().strip()
        return {"action": "open_url", "url": url}

    elif intent_name == "search_web":
        return {"action": "search_web", "query": g[1].strip()}

    elif intent_name == "open_url":
        url = g[1].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return {"action": "open_url", "url": url}

    elif intent_name == "type_text":
        return {"action": "type_and_send", "text": g[1].strip(), "press_enter": False}

    elif intent_name == "send_whatsapp":
        return {
            "action": "send_whatsapp",
            "contact_name": g[0].strip(),
            "message": g[1].strip(),
        }


    elif intent_name == "send_sms":
        return {
            "action": "send_sms",
            "phone_number": g[0].strip(),
            "message": g[1].strip(),
        }

    elif intent_name == "send_sms_reverse":
        return {
            "action": "send_sms",
            "phone_number": g[1].strip(),
            "message": g[0].strip(),
        }

    elif intent_name == "send_number_msg":
        return {
            "action": "send_number_msg",
            "phone_number": g[0].strip(),
            "message": g[1].strip(),
        }

    elif intent_name == "send_number_msg_reverse":
        return {
            "action": "send_number_msg",
            "phone_number": g[1].strip(),
            "message": g[0].strip(),
        }

    elif intent_name == "open_whatsapp":
        return {"action": "open_app", "app_name": "whatsapp"}

    elif intent_name == "send_email":
        return {
            "action": "send_email",
            "contact_name": g[2].strip(),
            "content": g[3].strip()
        }

    elif intent_name == "send_email_prompt":
        return {
            "action": "send_email",
            "contact_name": g[2].strip(),
            "prompt_body": True
        }

    elif intent_name == "send_email_nocontact":
        # e.g. "send a mail" — no contact specified, ask for it
        return {
            "action": "send_email",
            "contact_name": None,
            "prompt_body": True
        }

    elif intent_name == "send_email_short":
        # e.g. "email to prabhushankarmund@gmail.com [optional message]"
        return {
            "action": "send_email",
            "contact_name": g[1].strip(),
            "content": g[2].strip() if g[2] else None,
            "prompt_body": not bool(g[2])
        }

    elif intent_name == "open_email":
        return {"action": "open_app", "app_name": "gmail"}

    elif intent_name == "stop_execution":
        return {"action": "stop"}

    # ── Spotify SDK (Phase 4B) ────────────────────────────────────
    elif intent_name == "spotify_play":
        query = g[0].strip() if g else ""
        return {"action": "spotify_play", "query": query}

    elif intent_name == "spotify_pause":
        return {"action": "spotify_pause"}

    elif intent_name == "spotify_resume":
        return {"action": "spotify_resume"}

    elif intent_name == "spotify_skip":
        return {"action": "spotify_skip"}

    elif intent_name == "spotify_previous":
        return {"action": "spotify_previous"}

    elif intent_name == "spotify_volume":
        percent = int(g[0]) if g and g[0] else 50
        return {"action": "spotify_volume", "percent": percent}

    elif intent_name == "spotify_now_playing":
        return {"action": "spotify_now_playing"}

    # ── Google Calendar (Phase 4B) ────────────────────────────────
    elif intent_name == "calendar_today":
        return {"action": "calendar_query", "timeframe": "today"}

    elif intent_name == "calendar_tomorrow":
        return {"action": "calendar_query", "timeframe": "tomorrow"}

    elif intent_name == "calendar_week":
        return {"action": "calendar_query", "timeframe": "this_week"}

    elif intent_name == "calendar_generic":
        timeframe_raw = (g[0] or "").lower().strip()
        timeframe_map = {"today": "today", "tomorrow": "tomorrow", "this week": "this_week", "week": "this_week"}
        timeframe = timeframe_map.get(timeframe_raw, "today")
        return {"action": "calendar_query", "timeframe": timeframe}

    elif intent_name == "calendar_create":
        details = g[0].strip() if g else ""
        return {"action": "calendar_create", "details": details}

    # ── Slack (Phase 4B) ─────────────────────────────────────────
    elif intent_name == "slack_send":
        channel = g[0].strip() if g else "general"
        text = g[1].strip() if len(g) > 1 and g[1] else ""
        return {"action": "slack_send", "channel": channel, "text": text}

    elif intent_name == "slack_send_alt":
        channel = g[0].strip() if g else "general"
        text = g[1].strip() if len(g) > 1 and g[1] else ""
        return {"action": "slack_send", "channel": channel, "text": text}

    elif intent_name == "slack_read":
        # g[0] = optional count, g[1] = channel name
        count = int(g[0]) if g and g[0] else 5
        channel = g[1].strip() if len(g) > 1 and g[1] else "general"
        return {"action": "slack_read", "channel": channel, "count": count}

    elif intent_name == "slack_channels":
        return {"action": "slack_channels"}

    elif intent_name == "browser_back":
        return {"action": "browser_nav", "type": "back"}

    elif intent_name == "browser_refresh":
        return {"action": "browser_nav", "type": "refresh"}

    elif intent_name == "browser_new_tab":
        return {"action": "browser_nav", "type": "new_tab"}

    elif intent_name == "browser_close_tab":
        return {"action": "browser_nav", "type": "close_tab"}

    elif intent_name == "query_about_me":
        return {"action": "query_about_me", "query": match.group(0)}

    elif intent_name == "remember_fact":
        return {"action": "remember_fact", "fact": g[1].strip()}

    elif intent_name == "forget_fact":
        return {"action": "forget_fact", "fact": g[1].strip()}

    elif intent_name in ("vision_query_screen", "vision_query_doc"):
        return {"action": "vision_query", "query": match.group(0)}

    elif intent_name == "camera_recognition":
        return {"action": "camera_recognition", "query": match.group(0)}

    elif intent_name == "close_named_tab":
        # "close Gemini API Free Key tab" — use Vision to click the X on that tab
        tab_name = g[0].strip() if g else ""
        enriched = f'the small X close button on the browser tab labeled "{tab_name}" in the browser tab bar at the top of the screen'
        return {"action": "ui_click", "target": enriched, "_tab_name": tab_name}

    # NOTE: "close_tab" and "new_tab" dead-code branches removed — the correct
    # browser_close_tab / browser_new_tab handlers above always fire first.

    elif intent_name == "ui_click":
        # Clean filler phrases from the target: "on the", "where you see", etc.
        raw_target = g[0].strip() if g else match.group(0)
        target = _clean_click_target(raw_target)
        return {"action": "ui_click", "target": target}

    return None


def _clean_click_target(raw: str) -> str:
    """Strip natural language filler from a click target phrase."""
    import re
    # Remove leading filler phrases
    filler_patterns = [
        r"^on\s+the\s+",
        r"^on\s+",
        r"^where\s+you\s+see\s+",
        r"^where\s+it\s+says?\s+",
        r"^when\s+.+?\s+is\s+written\s+",
        r"^the\s+",
    ]
    for pat in filler_patterns:
        raw = re.sub(pat, "", raw, flags=re.IGNORECASE).strip()
    return raw


def _correct_command(original: str, best_match: str) -> str:
    """
    Simple prefix correction: if the original starts with a fuzzy-matched verb,
    return a corrected version.
    """
    words = original.split()
    if words:
        corrected_words = best_match.split() + words[1:]
        return " ".join(corrected_words)
    return best_match
