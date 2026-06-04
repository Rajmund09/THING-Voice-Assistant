import pytest
from backend.engine.intent_router import get_local_intent


@pytest.mark.parametrize("command,expected_intent", [
    ("open chrome", "open_app"),
    ("close notepad", "close_app"),
    ("play lofi on youtube", "play_youtube"),
    ("pause the music", "media_control"),
    ("volume up 10", "control_system"),
    ("mute the sound", "control_system"),
    ("brightness down", "control_system"),
    ("take a screenshot", "control_system"),
    ("scroll down 500", "scroll_screen"),
    ("go to top", "scroll_screen"),
    ("lock my pc", "control_system"),
    ("what time is it", "get_time"),
    ("what is the date", "get_date"),
    ("how is the weather", "get_weather"),
    ("search for python tutorials", "search_web"),
    ("open github.com", "open_url"),
    ("type hello world", "type_and_send"),
    ("send mom a message hi", "send_whatsapp"),
    ("message 9876543210 hello", "send_number_msg"),
    ("go back", "browser_nav"),
    ("refresh page", "browser_nav"),
    ("new tab", "browser_nav"),
    ("close tab", "browser_nav"),
    ("stop", "stop"),
    # Phase 2 — Vision
    ("what's on my screen", "vision_query"),
    ("describe my screen", "vision_query"),
    ("read the error message", "vision_query"),
    ("summarize this document", "vision_query"),
    # Phase 2 — UI Click
    ("click the login button", "ui_click"),
    ("click submit", "ui_click"),
    ("press the close icon", "ui_click"),
])
def test_regex_intents(command, expected_intent):
    """Verifies that common commands are correctly matched by the regex layer."""
    # We set use_llm_fallback=False to isolate the regex layer
    result = get_local_intent(command, use_llm_fallback=False)
    assert result is not None
    assert result["action"] == expected_intent


def test_fuzzy_correction():
    """Verifies that minor typos are corrected by the fuzzy layer."""
    # "openn chrome" should be corrected to "open chrome"
    result = get_local_intent("openn chrome", use_llm_fallback=False)
    assert result is not None
    assert result["action"] == "open_app"
    assert result["app_name"] == "chrome"


def test_volume_numeric_extraction():
    """Verifies that volume amounts are correctly extracted."""
    result = get_local_intent("volume up 25", use_llm_fallback=False)
    assert result["action"] == "control_system"
    assert result["type"] == "volume_up"
    assert result["value"] == 25


# ── Bug A Regression Tests ────────────────────────────────────────────────────
# Ensures browser_nav always returns `type` key, never `sub_action`.

@pytest.mark.parametrize("command,expected_type", [
    ("close tab",  "close_tab"),
    ("new tab",    "new_tab"),
    ("go back",    "back"),
    ("refresh",    "refresh"),
])
def test_browser_nav_uses_type_key(command, expected_type):
    """
    Regression test for Bug A: browser_nav intents must use the `type` key,
    never `sub_action`. The dead code branches have been removed.
    """
    result = get_local_intent(command, use_llm_fallback=False)
    assert result is not None
    assert result["action"] == "browser_nav"
    assert "type" in result, f"Expected 'type' key but got: {result}"
    assert "sub_action" not in result, f"Dead-code 'sub_action' key still present: {result}"
    assert result["type"] == expected_type


def test_whatsapp_entity_extraction():
    """Verifies correct contact_name and message extraction for WhatsApp."""
    result = get_local_intent("send raj hello there", use_llm_fallback=False)
    assert result is not None
    assert result["action"] == "send_whatsapp"
    assert "contact_name" in result
    assert "message" in result
    assert result["contact_name"].lower() == "raj"
    assert "hello there" in result["message"].lower()


def test_scroll_amount_extraction():
    """Verifies scroll direction and pixel amount extraction."""
    result = get_local_intent("scroll down 800", use_llm_fallback=False)
    assert result is not None
    assert result["action"] == "scroll_screen"
    assert result["direction"] == "down"
    assert result["amount"] == 800


def test_unknown_command_returns_none_without_llm():
    """Unrecognized command returns None when LLM fallback is disabled."""
    result = get_local_intent(
        "flibbertigibbet the zorgon", use_llm_fallback=False
    )
    assert result is None
