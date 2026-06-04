"""
state_manager.py — THING v4.0
Single source of truth for all assistant state and context.
Replaces dual-state bug where memory_engine.context and state_manager diverged.
"""

import time
from enum import Enum
from typing import Dict, Any, Optional


class AssistantState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    WAIT_CONFIRMATION = "WAIT_CONFIRMATION"
    APP_CONTEXT_ACTIVE = "APP_CONTEXT_ACTIVE"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    EMAIL_COMPOSING = "EMAIL_COMPOSING"
    REGISTERING_FACE = "REGISTERING_FACE"


class StateManager:
    def __init__(self):
        self.current_state: AssistantState = AssistantState.IDLE
        self.pending_action: Optional[Dict[str, Any]] = None
        self.active_app: Optional[str] = None
        self.active_browser_tab: Optional[str] = None
        self.is_busy: bool = False # Lock flag for long-running automations

        # Context tracking — single source of truth
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_command: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.last_activity_time: float = time.monotonic()

    # ─── State Control ───────────────────────────────────────────

    def set_state(self, state: AssistantState):
        self.current_state = state

    def acquire_lock(self):
        """Sets busy flag to True to block other commands."""
        self.is_busy = True
        self.set_state(AssistantState.EXECUTING)

    def release_lock(self):
        """Clears busy flag."""
        self.is_busy = False
        if self.active_app:
            self.set_state(AssistantState.APP_CONTEXT_ACTIVE)
        else:
            self.set_state(AssistantState.IDLE)

    def is_waiting_confirmation(self) -> bool:
        return self.current_state == AssistantState.WAIT_CONFIRMATION

    # ─── Pending Actions (confirmation flow) ─────────────────────

    def set_pending_action(self, action: Dict[str, Any]):
        self.pending_action = action
        self.set_state(AssistantState.WAIT_CONFIRMATION)

    def clear_pending_action(self):
        self.pending_action = None
        if self.active_app:
            self.set_state(AssistantState.APP_CONTEXT_ACTIVE)
        else:
            self.set_state(AssistantState.IDLE)

    # ─── App Context ──────────────────────────────────────────────

    def set_active_app(self, app_name: str):
        if app_name:
            self.active_app = app_name.lower().strip()
            self.context["active_app"] = self.active_app
            self.set_state(AssistantState.APP_CONTEXT_ACTIVE)

    def clear_active_app(self):
        self.active_app = None
        self.active_browser_tab = None
        self.context.pop("active_app", None)
        if self.current_state == AssistantState.APP_CONTEXT_ACTIVE:
            self.set_state(AssistantState.IDLE)

    def set_active_browser_tab(self, url: str):
        self.active_browser_tab = url
        self.context["active_browser_tab"] = url

    # ─── Last Action Tracking (for "next/repeat" context) ────────

    def set_last_action(self, action: Dict[str, Any], command: str = ""):
        self.last_action = action
        self.last_command = command

    def get_last_action(self) -> Optional[Dict[str, Any]]:
        return self.last_action

    # ─── Generic Context ─────────────────────────────────────────

    def update_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self) -> Dict[str, Any]:
        return self.context

    def clear_context(self):
        self.context = {}
        self.active_app = None
        self.active_browser_tab = None
        self.set_state(AssistantState.IDLE)

    def record_activity(self):
        """Called by pipeline on every processed command."""
        self.last_activity_time = time.monotonic()

    def get_idle_minutes(self) -> float:
        """Returns minutes since last recorded activity."""
        return (time.monotonic() - self.last_activity_time) / 60

    def reset(self):
        """Full reset — used on assistant restart."""
        self.__init__()


# Global singleton
state_manager = StateManager()
