"""
action_executor.py — THING v4.0
Executes action lists and returns honest result strings.
Anti-hallucination contract: never returns success message if action failed.
"""

from typing import List, Dict, Any
from backend.modules.system_ops import control_system, open_app, close_app, get_time, get_date, search_web, get_weather
from backend.modules.youtube_ops import play_youtube, control_media
from backend.modules.whatsapp_ops import send_whatsapp
from backend.modules.sms_ops import send_sms
from backend.modules.number_msg_ops import send_number_msg
from backend.modules.browser_ops import scroll_screen, type_and_send, browser_nav, open_url
from backend.engine.memory_engine import memory
from backend.engine.state_manager import state_manager


def execute_actions(actions: List[Dict[str, Any]]) -> str:
    """
    Executes a list of actions sequentially.
    Returns a concatenated honest result string.
    """
    if not actions:
        return "No actions to execute."

    results = []

    for action in actions:
        act_type = action.get("action")
        result = _execute_single(action, act_type)
        results.append(result)

        # Log to memory
        memory.add_command(str(action), str(result))

        # Update state context
        if act_type == "open_app":
            state_manager.set_active_app(action.get("app_name", ""))
        elif act_type == "close_app":
            state_manager.clear_active_app()

        # Track last action
        state_manager.set_last_action(action)

        # Stop signal
        if act_type == "stop":
            break

        # Structured packet (e.g. email review dict) — bubble up immediately
        if isinstance(result, dict):
            return result

    return " ".join(str(r) for r in results if r and not isinstance(r, dict))


def _execute_single(action: Dict[str, Any], act_type: str) -> str:
    """Dispatches a single action and returns an honest result string."""
    try:
        if act_type == "open_app":
            return open_app(action.get("app_name", ""))

        elif act_type == "close_app":
            return close_app(action.get("app_name", ""))

        elif act_type == "control_system":
            return control_system(action.get("type"), action.get("value"))

        elif act_type == "play_youtube":
            return play_youtube(action.get("query", ""))

        elif act_type == "media_control":
            return control_media(action.get("type", ""))

        elif act_type == "send_whatsapp":
            return send_whatsapp(
                action.get("contact_name", ""),
                action.get("message", ""),
            )

        elif act_type == "send_sms":
            return send_sms(
                action.get("phone_number", "") or action.get("contact_name", ""),
                action.get("message", ""),
            )

        elif act_type == "send_number_msg":
            return send_number_msg(
                action.get("phone_number", ""),
                action.get("message", ""),
            )

        elif act_type == "send_email":
            from backend.modules.email_agent import email_agent
            res = email_agent.start_flow(
                recipient=action.get("contact_name"),
                topic=action.get("content"),
                subject=action.get("subject"),
            )
            if isinstance(res, dict):
                # Return early as structured packet — execute_actions caller handles this
                return {"success": True, "message": res.get("message", "Review your email."), "data": res}
            # Plain string (asking for subject/body/recipient)
            return str(res) if res else "Something went wrong with the email flow."

        elif act_type == "scroll_screen":
            return scroll_screen(action.get("direction", "down"), action.get("amount", 300))

        elif act_type == "type_and_send":
            return type_and_send(action.get("text", ""), action.get("press_enter", False))

        elif act_type == "search_web":
            return search_web(action.get("query", ""))

        elif act_type == "get_time":
            return get_time()

        elif act_type == "get_date":
            return get_date()

        elif act_type == "get_weather":
            return get_weather()

        elif act_type == "check_cpu_usage":
            from backend.modules.system_ops import get_cpu_usage
            return get_cpu_usage()

        elif act_type == "check_ram_usage":
            from backend.modules.system_ops import get_ram_usage
            return get_ram_usage()

        elif act_type == "summarize_day":
            from backend.modules.system_ops import summarize_day
            return summarize_day()

        elif act_type == "open_url":
            return open_url(action.get("url", ""))

        elif act_type == "browser_nav":
            return browser_nav(action.get("type", "back"))

        elif act_type == "query_about_me":
            from backend.engine.about_me_engine import get_about_me_response
            return get_about_me_response(action.get("query", ""))

        elif act_type == "remember_fact":
            from backend.modules.profile_manager import profile_manager
            fact = action.get("fact", "")
            # Simple heuristic for auto-learning
            if "birthday" in fact.lower():
                profile_manager.update_info("birthday", fact)
            elif "study" in fact.lower() or "bca" in fact.lower():
                profile_manager.update_info("education", fact)
            else:
                profile_manager.update_info("skills", fact)
            return f"Understood. I'll remember that: {fact}"

        elif act_type == "forget_fact":
            from backend.modules.profile_manager import profile_manager
            field = action.get("field", "") or action.get("fact", "")
            if not field:
                return "Please specify what you want me to forget."
            # Attempt to clear the field by key name
            try:
                profile_manager.update_info(field.lower().strip(), "")
                return f"Understood. I've cleared '{field}' from my memory."
            except Exception:
                return f"I couldn't find '{field}' in my memory to forget."

        elif act_type == "stop":
            return "Stopped."

        elif act_type == "vision_query":
            from backend.modules.vision_engine import analyze_screen
            query = action.get("query", "Describe what is on the screen.")
            result = analyze_screen(query)
            if not result.get("success", True):
                return result.get("description", "Vision failed.")
            # Return structured dict so pipeline can attach screenshot_b64 + timing
            return {
                "_vision":        True,
                "description":    result["description"],
                "screenshot_b64": result.get("screenshot_b64"),
                "elapsed_ms":     result.get("elapsed_ms"),
                "model":          result.get("model"),
                "coordinates":    result.get("coordinates"),
            }

        elif act_type == "camera_recognition":
            from backend.modules.camera_recognition import recognize_camera_context
            query = action.get("query", "")
            result = recognize_camera_context(query)
            if not result.get("success", True):
                return result.get("description", "Camera recognition failed.")
            return result

        elif act_type == "ui_click":
            from backend.modules.vision_engine import analyze_screen
            from backend.modules.ui_interactor import click_at
            from backend.security.hallucination_guard import validate_click_coordinates
            import pyautogui

            target = action.get("target", "")

            # Build a rich, descriptive query so Gemini has enough context
            # If the target is already a long enriched description (from close_named_tab), use it directly.
            # Otherwise build context around the bare word.
            if len(target) > 40:
                # Already enriched (e.g. from close_named_tab)
                gemini_query = target
            else:
                gemini_query = _build_vision_query(target)

            vision_result = analyze_screen(gemini_query)
            coords = vision_result.get("coordinates")
            screen_w, screen_h = pyautogui.size()

            if not coords or not validate_click_coordinates(coords, screen_w, screen_h):
                # Give a helpful, specific suggestion
                suggestion = _click_suggestion(target)
                return f"Could not locate '{target}' on screen. {suggestion}"

            x, y = coords["x"], coords["y"]
            return click_at(x, y)

        # ── Spotify SDK (Phase 4B) ──────────────────────────────────
        elif act_type == "spotify_play":
            from backend.modules.spotify_sdk import play_track
            return play_track(action.get("query", ""))

        elif act_type == "spotify_pause":
            from backend.modules.spotify_sdk import pause
            return pause()

        elif act_type == "spotify_resume":
            from backend.modules.spotify_sdk import resume
            return resume()

        elif act_type == "spotify_skip":
            from backend.modules.spotify_sdk import skip
            return skip()

        elif act_type == "spotify_previous":
            from backend.modules.spotify_sdk import previous
            return previous()

        elif act_type == "spotify_volume":
            from backend.modules.spotify_sdk import set_volume
            return set_volume(action.get("percent", 50))

        elif act_type == "spotify_now_playing":
            from backend.modules.spotify_sdk import get_current_track
            info = get_current_track()
            if "error" in info:
                return info["error"]
            status = "Playing" if info.get("is_playing") else "Paused"
            return f"{status}: '{info['track_name']}' by {info['artist']} from '{info['album']}'."

        # ── Google Calendar (Phase 4B) ──────────────────────────────
        elif act_type == "calendar_query":
            timeframe = action.get("timeframe", "today")
            if timeframe == "today":
                from backend.modules.google_calendar import get_events_today
                return get_events_today()
            elif timeframe == "tomorrow":
                from backend.modules.google_calendar import get_events_tomorrow
                return get_events_tomorrow()
            else:
                from backend.modules.google_calendar import get_events_this_week
                return get_events_this_week()

        elif act_type == "calendar_create":
            from backend.modules.google_calendar import create_event
            # For regex-matched commands, the LLM will have extracted entities.
            # For direct regex, details is a raw string passed to the LLM for parsing.
            title = action.get("title", "")
            start_time = action.get("start_time", "")
            if not title or not start_time:
                # Details was extracted raw — return a prompt to the LLM
                details = action.get("details", "")
                return (
                    f"I need the exact date and time for that. Please say something like "
                    f"'create meeting Team Sync on May 25 at 2pm'."
                )
            return create_event(
                title=title,
                start_time=start_time,
                end_time=action.get("end_time"),
                description=action.get("description", ""),
                location=action.get("location", ""),
            )

        # ── Slack (Phase 4B) ────────────────────────────────────────
        elif act_type == "slack_send":
            from backend.modules.slack_sdk_module import send_message
            return send_message(
                channel=action.get("channel", "general"),
                text=action.get("text", ""),
            )

        elif act_type == "slack_read":
            from backend.modules.slack_sdk_module import get_recent_messages
            return get_recent_messages(
                channel=action.get("channel", "general"),
                n=action.get("count", 5),
            )

        elif act_type == "slack_channels":
            from backend.modules.slack_sdk_module import list_channels
            return list_channels()

        else:
            return f"Unknown action: {act_type}."

    except Exception as e:
        print(f"[Executor] Error in '{act_type}': {e}")
        # Anti-hallucination: honest failure message
        return f"Failed to execute {act_type.replace('_', ' ')}."


# ─────────────────────────────────────────────────────────────────
#  Vision click helpers
# ─────────────────────────────────────────────────────────────────

def _build_vision_query(target: str) -> str:
    """
    Converts a bare click target word into a rich, specific Gemini prompt.
    Examples:
      "close"  → "Find the small X or close button (a tab close button, dialog close, or window close)"
      "submit" → "Find the Submit button on the page"
      "search bar" → "Find the search input field / search bar / address bar on the screen"
    """
    t = target.lower().strip()

    # Browser tab close patterns
    if t in ("x", "close", "close button", "close icon", "✕", "×"):
        return (
            "Find the small X close button. Look in: browser tab bar (the small × on a tab), "
            "dialog box close buttons, window title bar close button (top-right corner), "
            "or any visible × / close icon on screen."
        )

    # Address / URL bar
    if any(k in t for k in ("address bar", "url bar", "search bar", "location bar", "localhost")):
        return (
            f"Find the browser address bar / URL bar at the top of the browser window "
            f"that currently shows or should contain: {target}"
        )

    # Login / form buttons
    if any(k in t for k in ("login", "sign in", "submit", "send", "confirm", "ok", "cancel", "accept", "decline")):
        return f"Find the '{target}' button on the page. It may be a colored rectangular button."

    # Menu / hamburger
    if any(k in t for k in ("menu", "hamburger", "nav", "sidebar")):
        return f"Find the '{target}' — a menu icon, hamburger (☰) button, or navigation toggle."

    # Generic enrichment
    return (
        f"Find and locate '{target}' on the screen. "
        "Look carefully at all UI elements: buttons, tabs, icons, links, form fields, and toolbars."
    )


def _click_suggestion(target: str) -> str:
    """Return a helpful next-step suggestion when a click fails."""
    t = target.lower()
    if any(k in t for k in ("x", "close", "×")):
        return "Try: 'click the X button on the tab' or 'close this tab' (uses Ctrl+W instead)."
    if "search" in t or "address" in t or "url" in t:
        return "Try: 'click the browser address bar' or press Ctrl+L to focus it."
    if "submit" in t or "login" in t or "send" in t:
        return "Try pressing Enter, or describe the button color: 'click the blue submit button'."
    return "Try describing it more specifically, e.g. 'click the blue button at the top'."
