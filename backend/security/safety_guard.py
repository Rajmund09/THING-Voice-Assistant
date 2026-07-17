"""
safety_guard.py — THING Jarvis Upgrade
Guards sensitive actions that require explicit confirmation before execution, enhanced with an LLM mind.
"""

import os
import json
import logging
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
LLM_MODEL = "llama-3.1-8b-instant"

# Actions that require verbal confirmation before executing
DANGEROUS_ACTIONS = {
    "shutdown":   "Shut down the PC",
    "restart":    "Restart the PC",
    "lock":       "Lock the screen",
    "send_whatsapp": "Send a WhatsApp message",
    "delete":     "Delete files",
}

def requires_confirmation(action: str) -> bool:
    """Returns True if the action requires user confirmation."""
    return action in DANGEROUS_ACTIONS

def get_confirmation_prompt(action: str, context: Dict[str, Any] = None) -> str:
    """Returns a human-readable confirmation prompt."""
    if context is None:
        context = {}
        
    label = DANGEROUS_ACTIONS.get(action, action.replace("_", " "))

    if action == "send_whatsapp":
        contact = context.get("contact_name", "someone")
        message = context.get("message", "")
        return f"Ready to send '{message}' to {contact}. Say yes to send."

    if action in ("shutdown", "restart"):
        return f"Ready to {label.lower()}. Say yes to confirm."

    return f"Ready to {label.lower()}. Say yes to proceed."


def validate_action(action_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks if an action dict needs confirmation.
    Returns: {needs_confirm: bool, prompt: str}
    """
    act = action_dict.get("action", "")
    act_type = action_dict.get("type", "")

    # Static checks
    if act == "send_whatsapp":
        return {
            "needs_confirm": True,
            "prompt": get_confirmation_prompt("send_whatsapp", action_dict),
        }

    if act == "control_system" and act_type in ("shutdown", "restart", "lock"):
        return {
            "needs_confirm": True,
            "prompt": get_confirmation_prompt(act_type),
        }

    # Dynamic LLM check for other potentially dangerous actions
    try:
        from backend.core.connectivity_monitor import monitor as connectivity_monitor
        if not connectivity_monitor.is_online():
            return {"needs_confirm": False, "prompt": ""}
            
        SYSTEM_PROMPT = f"""You are a safety evaluator for an AI voice assistant.
Your job is to determine if an action requested by the system requires explicit user confirmation before executing.
Actions that delete data, make purchases, send messages/emails, or shut down systems should require confirmation.
Harmless actions like getting the weather, opening apps, checking system stats, or playing music do NOT require confirmation.

Action Context: {json.dumps(action_dict)}

Output format: Return ONLY a JSON object with:
"needs_confirm": boolean (true if dangerous/irreversible, false otherwise)
"prompt": a short friendly string asking the user for confirmation (e.g., "Ready to send the email. Say yes to proceed.") if needs_confirm is true. Otherwise empty string.
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
        
        if result.get("needs_confirm"):
            logger.info("LLM safety guard flagged action for confirmation: %s", act)
            return {
                "needs_confirm": True,
                "prompt": result.get("prompt", f"Ready to perform {act}. Say yes to proceed.")
            }
            
    except Exception as e:
        logger.error("Safety guard LLM error: %s", e)

    return {"needs_confirm": False, "prompt": ""}
