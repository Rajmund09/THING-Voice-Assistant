"""
pipeline.py — THING v4.0
Master processing pipeline.
Returns a ResponsePacket dict (never a bare string).
Guarantees: voice text == display text via single ResponsePacket.
"""

import uuid
from backend.engine.entity_resolver import resolve_entities
from backend.engine.intent_priority_router import route_intent
from backend.engine.action_planner import plan_actions
from backend.engine.chat_engine import process_chat
from backend.engine.knowledge_engine import fetch_knowledge
from backend.modules.action_executor import execute_actions
from backend.utils.response_manager import (
    build_response_packet,
    error_packet,
    success_packet,
    format_premium_response,
)
from backend.engine.state_manager import state_manager, AssistantState


def process_pipeline(raw_command: str, bypass_confirm: bool = False) -> dict:
    """
    Master pipeline for THING voice assistant.
    ALWAYS returns a ResponsePacket dict — never a bare string.
    The server uses packet['speak_text'] for TTS and emits packet to frontend.
    """
    state_manager.record_activity()
    if not raw_command or not raw_command.strip():
        return error_packet("none", "No command received.")

    clean_command = resolve_entities(raw_command.strip())

    # --- NSFW / Profanity Filter ---
    import re
    prohibited_words = ["porn", "pornography", "xxx", "sex", "nude", "nsfw", "porno"]
    clean_lower = clean_command.lower()
    if any(re.search(r'\b' + re.escape(w) + r'\b', clean_lower) for w in prohibited_words):
        return build_response_packet(
            "restricted", 
            "I cannot process requests containing restricted or inappropriate content.", 
            success=False
        )

    # 0. State-aware routing (Highest priority)
    if state_manager.current_state == AssistantState.EMAIL_COMPOSING:
        from backend.modules.email_agent import email_agent
        res = email_agent.handle_input(clean_command)
        if isinstance(res, dict):
            # Pass through the structured data (e.g. email_review)
            return build_response_packet(
                "email_flow",
                res.get("message", "Review your email."),
                success=res.get("success", True),
                data=res,
            )
        # res is a plain string (e.g. asking for subject/body)
        return build_response_packet("email_flow", str(res), success=True)

    if state_manager.current_state == AssistantState.REGISTERING_FACE:
        from backend.modules.camera_recognition import register_pending_face
        res = register_pending_face(clean_command)
        return build_response_packet("camera_registration", res, success=True)

    try:
        routed = route_intent(clean_command)
    except Exception as e:
        print(f"[Pipeline] Router error: {e}")
        return error_packet("route_error", "I had trouble understanding that.")

    # ── Offline Capability Filter ────────────────────────────────
    from backend.core.connectivity_monitor import monitor as connectivity_monitor
    from backend.core.offline_capability_filter import can_execute, get_offline_error_message
    
    if not connectivity_monitor.is_online():
        if routed["type"] == "LIVE_DATA":
            return build_response_packet("knowledge_live", get_offline_error_message("search_web"), success=False)
        elif routed["type"] == "LOCAL" and routed.get("intent"):
            action_name = routed["intent"].get("action")
            if action_name and not can_execute(action_name):
                return build_response_packet(action_name, get_offline_error_message(action_name), success=False)
        elif routed["type"] in ["EXECUTE_PENDING", "MULTI_STEP"]:
            steps = routed.get("steps") or (routed.get("action", {}).get("plan") if isinstance(routed.get("action"), dict) else None)
            if steps:
                for step in steps:
                    action_name = step.get("action")
                    if action_name and not can_execute(action_name):
                        return build_response_packet(action_name, get_offline_error_message(action_name), success=False)
            elif routed["type"] == "EXECUTE_PENDING" and isinstance(routed.get("action"), dict):
                action_name = routed["action"].get("action")
                if action_name and not can_execute(action_name):
                    return build_response_packet(action_name, get_offline_error_message(action_name), success=False)

    # ── Route: Execute pending confirmation ──────────────────────
    if routed["type"] == "EXECUTE_PENDING":
        action = routed["action"]
        try:
            if action.get("action") == "multi_step":
                result = execute_actions(action["plan"])
            else:
                result = execute_actions([action])
            return _build_from_result(result, action.get("action", "execute"), clean_command)
        except Exception as e:
            return error_packet("execute_pending", f"Execution failed: {str(e)}")

    # ── Route: Cancelled by user ─────────────────────────────────
    elif routed["type"] == "CANCEL_PENDING":
        return build_response_packet("cancel", routed["response"], success=True)

    # ── Route: Local intent ──────────────────────────────────────
    elif routed["type"] == "LOCAL":
        intent = routed.get("intent")

        if not intent:
            # Multi-step: use LLM planner
            plan = plan_actions(clean_command)
            if not plan:
                return error_packet(
                    "plan_failed",
                    "I couldn't figure out how to do that.",
                )

            has_destructive = _plan_has_destructive(plan) if not bypass_confirm else False
            if has_destructive:
                state_manager.set_pending_action({"action": "multi_step", "plan": plan})
                return build_response_packet(
                    "confirm_request",
                    "This sequence contains sensitive actions. Say yes to proceed or no to cancel.",
                    success=True,
                )
            else:
                result = execute_actions(plan)
                return _build_from_result(result, "multi_step", clean_command)
        else:
            # Single intent
            needs_confirm = _intent_needs_confirm(intent) if not bypass_confirm else False

            if needs_confirm:
                state_manager.set_pending_action(intent)
                # Build a human-readable confirmation message specific to action type
                action_type = intent.get("action", "")
                if action_type == "ui_click":
                    target = intent.get("target", "that element")
                    msg = f"I'll click '{target}'. Say yes to confirm or no to cancel."
                elif action_type == "send_whatsapp":
                    target = intent.get("contact_name", "that contact")
                    msg = f"Ready to send WhatsApp to {target}. Say yes to confirm."
                elif action_type == "send_email":
                    target = intent.get("contact_name", "that person")
                    msg = f"Ready to send email to {target}. Say yes to confirm."
                elif action_type == "control_system":
                    sys_type = intent.get("type", "that")
                    msg = f"Ready to {sys_type.replace('_', ' ')} your system. Say yes to confirm."
                else:
                    msg = f"Ready to {_humanize_action(action_type)}. Say yes to confirm."
                return build_response_packet("confirm_request", msg, success=True)
            else:
                try:
                    result = execute_actions([intent])
                    # Update context
                    if intent["action"] == "open_app":
                        state_manager.set_active_app(intent.get("app_name", ""))
                    elif intent["action"] == "close_app":
                        state_manager.clear_active_app()
                    return _build_from_result(result, intent["action"], clean_command)
                except Exception as e:
                    return error_packet(intent["action"], f"Failed: {str(e)}")

    # ── Route: Multi-step from LLM Classifier ───────────────────
    elif routed["type"] == "MULTI_STEP":
        steps = routed.get("steps", [])
        if not steps:
            return error_packet("multi_step", "No steps identified.")

        has_destructive = _plan_has_destructive(steps)
        if has_destructive:
            state_manager.set_pending_action({"action": "multi_step", "plan": steps})
            return build_response_packet(
                "confirm_request",
                "This sequence contains sensitive actions. Say yes to proceed or no to cancel.",
                success=True,
            )
        else:
            result = execute_actions(steps)
            return _build_from_result(result, "multi_step", clean_command)

    # ── Route: Live data (web search) ────────────────────────────
    elif routed["type"] == "LIVE_DATA":
        try:
            text = fetch_knowledge(clean_command, realtime=True)
            return build_response_packet("knowledge_live", text, success=bool(text))
        except Exception as e:
            return error_packet("knowledge_live", "I couldn't fetch live data right now.")

    # ── Route: Factual knowledge ─────────────────────────────────
    elif routed["type"] == "KNOWLEDGE":
        try:
            text = fetch_knowledge(clean_command, realtime=False)
            return build_response_packet("knowledge", text, success=bool(text))
        except Exception as e:
            return error_packet("knowledge", "My knowledge engine is offline.")

    # ── Route: Conversational chat ───────────────────────────────
    elif routed["type"] == "CHAT":
        if "response" in routed:
            return build_response_packet("chat", routed["response"], success=True)
        try:
            text = process_chat(clean_command)
            return build_response_packet("chat", text, success=True)
        except Exception as e:
            return error_packet("chat", "I'm having trouble responding right now.")

    # ── Final fallback: forward to chat engine for natural response ──
    try:
        text = process_chat(clean_command)
        return build_response_packet("chat_fallback", text, success=True)
    except Exception:
        return error_packet("unknown", "I'm not sure how to do that. Try rephrasing your command.")


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

from backend.security.hallucination_guard import validate_response

def _build_from_result(result, action_name: str, raw_command: str = "") -> dict:
    """
    Converts executor result (str or dict) to a ResponsePacket.
    Anti-hallucination: never claims success if result signals failure.
    Special case: vision_query results carry screenshot_b64 for the frontend.
    """
    # ── Camera result: structured dict with people/environment details ────
    if isinstance(result, dict) and result.get("_vision") and ("people" in result or "environment" in result):
        description = result.get("description", "I see you in front of the camera.")
        return build_response_packet(
            "camera_result",
            description,
            success=True,
            data={
                "type":           "camera_result",
                "screenshot_b64": result.get("screenshot_b64"),
                "elapsed_ms":     result.get("elapsed_ms"),
                "model":          result.get("model"),
                "people":         result.get("people", []),
                "environment":    result.get("environment", ""),
            },
        )

    # ── Vision result: structured dict with screenshot ──────────────
    if isinstance(result, dict) and result.get("_vision"):
        description = result.get("description", "Here is what I see on your screen.")
        return build_response_packet(
            "vision_result",
            description,
            success=True,
            data={
                "type":           "vision_result",
                "screenshot_b64": result.get("screenshot_b64"),
                "elapsed_ms":     result.get("elapsed_ms"),
                "model":          result.get("model"),
                "coordinates":    result.get("coordinates"),
            },
        )

    if isinstance(result, dict):
        success = result.get("success", True)
        msg = result.get("message", "Done.")
    elif isinstance(result, str):
        # Infer success from message content
        fail_signals = ["error", "failed", "couldn't", "unable", "not found", "no active"]
        success = not any(s in result.lower() for s in fail_signals)
        msg = result
    else:
        return error_packet(action_name, "Unexpected response from executor.")

    # Guard against empty success messages
    if success and (not msg or msg.strip().lower() in ["", "task completed.", "no output"]):
        msg = "Done."

    # Final validation layer
    msg = validate_response(msg, raw_command)

    return build_response_packet(action_name, msg, success=success, data=result.get("data") if isinstance(result, dict) else None)


def _plan_has_destructive(plan: list) -> bool:
    for a in plan:
        if a.get("action") == "send_whatsapp":
            return True
        if a.get("action") == "control_system" and a.get("type") in ["shutdown", "restart"]:
            return True
    return False


def _intent_needs_confirm(intent: dict) -> bool:
    if intent.get("action") == "send_whatsapp":
        return True
    if intent.get("action") == "send_email":
        return True
    if intent.get("action") == "ui_click":
        return True  # Phase 2: confirm before clicking any UI element
    if intent.get("action") == "control_system" and intent.get("type") in [
        "shutdown", "restart", "lock"
    ]:
        return True
    return False


def _humanize_action(action: str) -> str:
    return action.replace("_", " ")
