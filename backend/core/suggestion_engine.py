"""
suggestion_engine.py — THING v5.0
Stateless pure functions for evaluating proactive triggers.
"""

import re
from typing import Dict, Any, Optional, TypedDict

class SuggestionDict(TypedDict):
    id: str
    message: str
    action: str
    icon: str
    dismissible: bool

def evaluate_clipboard(text: str) -> Optional[SuggestionDict]:
    """Checks clipboard text for meeting links."""
    if not text:
        return None
    
    # regex for common meeting links
    meeting_patterns = [
        r"zoom\.us/j/\d+",
        r"meet\.google\.com/[a-z-]+",
        r"teams\.microsoft\.com/l/meetup-join/",
    ]
    
    for pattern in meeting_patterns:
        if re.search(pattern, text):
            return {
                "id": "meeting_link_detected",
                "message": "I see a meeting link in your clipboard. Should I open it?",
                "action": "open_meeting_and_notify", # Action handled by pipeline
                "icon": "calendar",
                "dismissible": True
            }
    
    return None

def evaluate_system_load(
    cpu: float,
    ram: float,
    top_cpu_process: Optional[str] = None,
    top_ram_process: Optional[str] = None,
) -> Optional[SuggestionDict]:
    """Checks CPU and RAM usage."""
    if cpu > 90:
        msg = f"Your CPU is at {cpu:.0f}%"
        if top_cpu_process:
            msg += f" ({top_cpu_process} is consuming the most)"
        msg += ". Want me to help close some background apps?"
        return {
            "id": "high_cpu_usage",
            "message": msg,
            "action": "list_heavy_processes",
            "icon": "cpu",
            "dismissible": True
        }
    
    if ram > 90:
        msg = f"System RAM is nearly full ({ram:.0f}%)"
        if top_ram_process:
            msg += f" ({top_ram_process} is using the most)"
        msg += ". Want me to clear some space?"
        return {
            "id": "high_ram_usage",
            "message": msg,
            "action": "check_ram_usage",
            "icon": "ram",
            "dismissible": True
        }
    
    return None

def evaluate_idle(idle_minutes: float) -> Optional[SuggestionDict]:
    """Checks if the user has been idle for a long time."""
    if idle_minutes >= 20: # Threshold from plan
        return {
            "id": "system_idle_detected",
            "message": "You've been idle for a while. Should I lock your PC?",
            "action": "control_system_lock",
            "icon": "clock",
            "dismissible": True
        }
    return None

def evaluate_time(current_hour: int, eod_hour: int = 17) -> Optional[SuggestionDict]:
    """Checks for end-of-day trigger."""
    if current_hour == eod_hour:
        return {
            "id": "end_of_day_suggestion",
            "message": "It's the end of your day! Want me to save and close your work?",
            "action": "summarize_day",
            "icon": "moon",
            "dismissible": True
        }
    return None
