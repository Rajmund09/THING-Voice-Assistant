"""
ui_interactor.py — THING v4.7 (Phase 2)
UI Interaction Module.

Executes mouse actions (click, hover, double-click) at pixel coordinates
returned by vision_engine.py.

Safety guarantees:
  - Bounds check before every action — refuses out-of-screen coordinates.
  - pyautogui FAILSAFE always enabled — move mouse to top-left corner to abort.
  - Smooth movement (duration=0.3s) to avoid jarring jumps.
  - Never simulates keyboard input (reserved for type_and_send in browser_ops.py).
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
#  PyAutoGUI initialisation (import lazily to avoid startup cost)
# ─────────────────────────────────────────────────────────────────

def _get_pyautogui():
    """Lazy import + safety config."""
    import pyautogui
    pyautogui.FAILSAFE    = True   # Top-left corner aborts any action
    pyautogui.PAUSE       = 0.05  # 50ms between actions (reduces flakiness)
    return pyautogui


def _screen_size() -> Tuple[int, int]:
    """Returns actual screen (width, height)."""
    pyautogui = _get_pyautogui()
    return pyautogui.size()


def _bounds_check(x: int, y: int) -> bool:
    """Returns True if (x, y) is within the screen bounds."""
    w, h = _screen_size()
    return 0 <= x < w and 0 <= y < h


# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────

def click_at(x: int, y: int, button: str = "left") -> str:
    """
    Smoothly moves the mouse to (x, y) and performs a single click.

    Args:
        x, y:   Screen pixel coordinates.
        button: 'left' (default), 'right', or 'middle'.

    Returns:
        Result string (success message or error).
    """
    if not _bounds_check(x, y):
        w, h = _screen_size()
        logger.warning("[UIInteractor] Coordinates (%d, %d) out of bounds (%dx%d)", x, y, w, h)
        return f"Could not click: coordinates ({x}, {y}) are outside the screen."

    try:
        pyautogui = _get_pyautogui()
        # Smooth movement over 0.3s then click
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.click(x, y, button=button)
        logger.info("[UIInteractor] Clicked (%s) at (%d, %d)", button, x, y)
        return f"Clicked at ({x}, {y}) successfully."
    except Exception as e:
        logger.error("[UIInteractor] Click failed: %s", e)
        return f"Failed to click: {str(e)}"


def double_click_at(x: int, y: int) -> str:
    """
    Double-clicks at (x, y) — for opening files, icons, etc.
    """
    if not _bounds_check(x, y):
        return f"Could not double-click: coordinates ({x}, {y}) are outside the screen."

    try:
        pyautogui = _get_pyautogui()
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.doubleClick(x, y)
        logger.info("[UIInteractor] Double-clicked at (%d, %d)", x, y)
        return f"Double-clicked at ({x}, {y}) successfully."
    except Exception as e:
        logger.error("[UIInteractor] Double-click failed: %s", e)
        return f"Failed to double-click: {str(e)}"


def right_click_at(x: int, y: int) -> str:
    """Right-clicks at (x, y) — for context menus."""
    return click_at(x, y, button="right")


def hover_at(x: int, y: int) -> str:
    """
    Moves mouse to (x, y) without clicking — useful for revealing tooltips.
    """
    if not _bounds_check(x, y):
        return f"Could not hover: coordinates ({x}, {y}) are outside the screen."

    try:
        pyautogui = _get_pyautogui()
        pyautogui.moveTo(x, y, duration=0.4)
        logger.info("[UIInteractor] Hovered at (%d, %d)", x, y)
        return f"Mouse moved to ({x}, {y})."
    except Exception as e:
        logger.error("[UIInteractor] Hover failed: %s", e)
        return f"Failed to hover: {str(e)}"
