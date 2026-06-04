"""
safety_guard.py — THING v4.0
Guards sensitive actions that require explicit confirmation before execution.
"""

from typing import Dict, Any

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


def get_confirmation_prompt(action: str, context: Dict[str, Any] = {}) -> str:
    """Returns a human-readable confirmation prompt."""
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

    # send_whatsapp
    if act == "send_whatsapp":
        return {
            "needs_confirm": True,
            "prompt": get_confirmation_prompt("send_whatsapp", action_dict),
        }

    # power control
    if act == "control_system" and act_type in ("shutdown", "restart", "lock"):
        return {
            "needs_confirm": True,
            "prompt": get_confirmation_prompt(act_type),
        }

    return {"needs_confirm": False, "prompt": ""}
