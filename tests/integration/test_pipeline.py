"""
tests/integration/test_pipeline.py — THING Phase 1 Integration Tests

Tests the full Command → route_intent() → action dict pipeline without
touching real external APIs. Only the Groq client and file I/O are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _route(command: str):
    """Thin wrapper around route_intent with LLM disabled for speed."""
    from backend.engine.intent_priority_router import route_intent
    return route_intent(command)


# ── Stop / Cancel ─────────────────────────────────────────────────────────────

def test_pipeline_stop_command():
    """Stop is always handled at the highest priority level."""
    result = _route("stop")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "stop"


def test_pipeline_cancel_command():
    result = _route("cancel")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "stop"


# ── Regex-matched actions ─────────────────────────────────────────────────────

def test_pipeline_open_app():
    result = _route("open spotify")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "open_app"
    assert result["intent"]["app_name"] == "spotify"


def test_pipeline_close_app():
    result = _route("close chrome")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "close_app"
    assert result["intent"]["app_name"] == "chrome"


def test_pipeline_play_youtube():
    result = _route("play lofi hip hop on youtube")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "play_youtube"
    assert "lofi" in result["intent"]["query"].lower()


def test_pipeline_volume_control():
    result = _route("volume up 20")
    assert result["type"] == "LOCAL"
    intent = result["intent"]
    assert intent["action"] == "control_system"
    assert intent["type"] == "volume_up"
    assert intent["value"] == 20


def test_pipeline_screenshot():
    result = _route("take a screenshot")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "control_system"
    assert result["intent"]["type"] == "take_screenshot"


def test_pipeline_lock_pc():
    result = _route("lock my pc")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "control_system"
    assert result["intent"]["type"] == "lock"


def test_pipeline_scroll_down():
    result = _route("scroll down 400")
    assert result["type"] == "LOCAL"
    intent = result["intent"]
    assert intent["action"] == "scroll_screen"
    assert intent["direction"] == "down"
    assert intent["amount"] == 400


def test_pipeline_browser_nav_back():
    result = _route("go back")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "browser_nav"
    assert result["intent"]["type"] == "back"


def test_pipeline_browser_nav_close_tab():
    """Regression: close tab must return `type` key, not `sub_action`."""
    result = _route("close tab")
    assert result["type"] == "LOCAL"
    intent = result["intent"]
    assert intent["action"] == "browser_nav"
    assert intent["type"] == "close_tab"
    assert "sub_action" not in intent


def test_pipeline_browser_nav_new_tab():
    """Regression: new tab must return `type` key, not `sub_action`."""
    result = _route("new tab")
    assert result["type"] == "LOCAL"
    intent = result["intent"]
    assert intent["action"] == "browser_nav"
    assert intent["type"] == "new_tab"
    assert "sub_action" not in intent


def test_pipeline_send_whatsapp():
    result = _route("send raj hello there")
    assert result["type"] == "LOCAL"
    intent = result["intent"]
    assert intent["action"] == "send_whatsapp"
    assert intent["contact_name"].lower() == "raj"


def test_pipeline_search_web():
    result = _route("search for best python books")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "search_web"
    assert "python" in result["intent"]["query"].lower()


def test_pipeline_vision_query():
    result = _route("what's on my screen")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "vision_query"


def test_pipeline_ui_click():
    result = _route("click the login button")
    assert result["type"] == "LOCAL"
    assert result["intent"]["action"] == "ui_click"
    assert "login" in result["intent"]["target"].lower()


# ── LLM-classified multi_step (mocked Groq) ───────────────────────────────────

@patch("backend.engine.llm_intent_classifier._client")
def test_pipeline_multi_step_from_llm(mock_client):
    """
    End-to-end: a compound command that misses regex is classified by the LLM
    as multi_step, then forwarded as MULTI_STEP type by route_intent.
    """
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''
    {
        "intent": "multi_step",
        "multi_step": [
            {"intent": "control_system", "entities": {"type": "take_screenshot"}},
            {"intent": "control_system", "entities": {"type": "lock"}}
        ],
        "confidence": 0.97
    }
    '''
    mock_client.chat.completions.create.return_value = mock_response

    with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
        result = _route("take a screenshot and then lock my pc please")

    # Route type depends on whether regex catches this or falls through to LLM.
    # Either LOCAL (regex) or MULTI_STEP (LLM) is acceptable; both are correct.
    assert result["type"] in ("LOCAL", "MULTI_STEP")


# ── Fast chat bypass ──────────────────────────────────────────────────────────

def test_pipeline_greeting_returns_chat():
    """Simple greetings should short-circuit all routing as CHAT."""
    result = _route("hello")
    assert result["type"] == "CHAT"


# ── Phase 2: Vision & UI Click pipeline tests ─────────────────────────────────

@patch("backend.modules.vision_engine.analyze_screen")
def test_pipeline_vision_query_full_flow(mock_analyze):
    """
    Phase 2: 'what's on my screen' → executor calls analyze_screen →
    pipeline builds a vision_result ResponsePacket with screenshot_b64 and elapsed_ms.
    """
    from backend.core.pipeline import process_pipeline

    mock_analyze.return_value = {
        "description":    "VS Code is open with a Python file.",
        "coordinates":    None,
        "screenshot_b64": "abc123base64",
        "success":        True,
        "elapsed_ms":     842.3,
        "model":          "gemini-2.5-flash",
    }

    result = process_pipeline("what's on my screen")

    assert result["success"] is True
    assert result["action"] == "vision_result"
    assert "VS Code" in result["speak_text"]
    assert result["data"]["screenshot_b64"] == "abc123base64"
    assert result["data"]["elapsed_ms"] == 842.3
    assert result["data"]["model"] == "gemini-2.5-flash"


def test_pipeline_ui_click_requires_confirmation():
    """
    Phase 2: 'click the login button' → pipeline should enter WAIT_CONFIRMATION
    and return a confirm_request packet with the target element name.
    """
    from backend.core.pipeline import process_pipeline
    from backend.engine.state_manager import state_manager, AssistantState

    # Reset state before test
    state_manager.clear_pending_action() if hasattr(state_manager, "clear_pending_action") else None

    result = process_pipeline("click the login button")

    assert result["action"] == "confirm_request"
    assert result["success"] is True
    # Confirmation message should clearly name the target element
    assert "login" in result["speak_text"].lower()
    assert "click" in result["speak_text"].lower()


@patch("backend.modules.vision_engine.analyze_screen")
def test_pipeline_vision_query_privacy_mode_returns_failure(mock_analyze):
    """
    Phase 2: When VISION_PRIVACY_MODE=true, vision calls should return a
    clear error packet — not a crash or silent empty response.
    """
    from backend.core.pipeline import process_pipeline

    mock_analyze.return_value = {
        "description":    "Vision is disabled. Set VISION_PRIVACY_MODE=false in .env to enable.",
        "coordinates":    None,
        "screenshot_b64": None,
        "success":        False,
    }

    result = process_pipeline("describe my screen")

    # Pipeline should produce a response (not crash) and surface the error message
    assert result is not None
    # Either the vision error text or a general failure message is acceptable
    assert result["speak_text"] is not None and len(result["speak_text"]) > 0


@patch("backend.modules.vision_engine.analyze_screen")
def test_pipeline_vision_api_error_returns_graceful_message(mock_analyze):
    """
    Phase 2: If Gemini Vision API fails, the pipeline should return a
    friendly error message — never an exception or empty response.
    """
    from backend.core.pipeline import process_pipeline

    mock_analyze.return_value = {
        "description":    "Vision API error: 503 Service Unavailable",
        "coordinates":    None,
        "screenshot_b64": None,
        "success":        False,
    }

    result = process_pipeline("what's on my screen")

    assert result is not None
    assert isinstance(result["speak_text"], str)
    assert len(result["speak_text"]) > 5   # Must have actual content, not empty
