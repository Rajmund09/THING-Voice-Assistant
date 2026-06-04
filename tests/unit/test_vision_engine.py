"""
tests/unit/test_vision_engine.py — THING Phase 2
Unit tests for vision_engine.py using mocked dependencies.

All tests run without a real screen, camera, or Gemini API key.
Key technique: patch `backend.modules.vision_engine._client` (the singleton)
directly — do NOT patch `google.genai.Client` at the module level since the
singleton is already created at import time.
"""

import io
import json
import time
import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────

def _make_fake_screenshot_bytes() -> bytes:
    """Return minimal valid JPEG bytes via Pillow."""
    from PIL import Image
    img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def _mock_client_response(text: str) -> MagicMock:
    """
    Build a mock singleton client whose models.generate_content() returns
    a response with .text = text.
    """
    mock_response = MagicMock()
    mock_response.text = text

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ─────────────────────────────────────────────────────────────────
#  Privacy mode and API key guard
# ─────────────────────────────────────────────────────────────────

def test_privacy_mode_blocks_capture():
    """Privacy mode should return a refusal without capturing the screen.

    Uses patch.object directly on the module-level PRIVACY_MODE flag rather than
    importlib.reload + os.environ patching, because load_dotenv(override=True) in
    vision_engine re-reads the .env file on every reload, defeating env patches.
    """
    import backend.modules.vision_engine as ve
    with patch.object(ve, "PRIVACY_MODE", True):
        with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
            result = ve.analyze_screen("what's on my screen")
    assert result["success"] is False
    assert "disabled" in result["description"].lower()


def test_missing_api_key_returns_error():
    """
    Missing GEMINI_API_KEY should return a helpful error, not crash.
    We patch the module-level GEMINI_API_KEY and _client directly after
    module import because dotenv.load_dotenv(override=True) in vision_engine
    re-reads .env on every import, making os.environ patching unreliable.
    """
    import backend.modules.vision_engine as ve
    with patch.object(ve, "GEMINI_API_KEY", ""):
        with patch.object(ve, "_client", None):
            with patch.object(ve, "PRIVACY_MODE", False):
                result = ve.analyze_screen("describe my screen")
    assert result["success"] is False
    assert "GEMINI_API_KEY" in result["description"]


# ─────────────────────────────────────────────────────────────────
#  Description mode — patch the singleton _client directly
# ─────────────────────────────────────────────────────────────────

@patch("backend.modules.vision_engine._capture_screen")
def test_description_mode_plain_text(mock_capture):
    """
    analyze_screen in description mode should return plain text description.
    Patches the singleton _client directly (created at module import time).
    """
    import backend.modules.vision_engine as ve

    fake_jpg = _make_fake_screenshot_bytes()
    mock_capture.return_value = (fake_jpg, 1920, 1080)

    mock_client = _mock_client_response(
        "VS Code is open with a Python file on the left and terminal on the right."
    )

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key", "VISION_PRIVACY_MODE": "false"}):
        with patch.object(ve, "_client", mock_client):
            with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
                with patch.object(ve, "PRIVACY_MODE", False):
                    result = ve.analyze_screen("describe my screen")

    assert result["success"] is True
    assert "VS Code" in result["description"]
    assert result["coordinates"] is None
    assert result["screenshot_b64"] is not None
    assert "elapsed_ms" in result
    assert result["elapsed_ms"] >= 0


@patch("backend.modules.vision_engine._capture_screen")
def test_description_mode_accidental_json_recovery(mock_capture):
    """
    If Gemini wraps its description in JSON despite being told not to,
    the parser should extract the 'description' key gracefully.
    """
    import backend.modules.vision_engine as ve

    fake_jpg = _make_fake_screenshot_bytes()
    mock_capture.return_value = (fake_jpg, 1920, 1080)

    # Gemini returns JSON despite plain-text instruction
    mock_client = _mock_client_response(
        '{"description": "I see a browser window with Google open.", "extra": "ignored"}'
    )

    with patch.object(ve, "_client", mock_client):
        with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
            with patch.object(ve, "PRIVACY_MODE", False):
                result = ve.analyze_screen("what do you see")

    assert result["success"] is True
    assert "browser" in result["description"].lower()


# ─────────────────────────────────────────────────────────────────
#  Click mode — patch the singleton _client directly
# ─────────────────────────────────────────────────────────────────

@patch("backend.modules.vision_engine._capture_screen")
def test_click_mode_found_scales_coords(mock_capture):
    """
    analyze_screen in click mode should scale normalized coords to pixels.
    1920x1080 screen, element at x=0.5, y=0.3 → pixel (960, 324).
    """
    import backend.modules.vision_engine as ve

    fake_jpg = _make_fake_screenshot_bytes()
    mock_capture.return_value = (fake_jpg, 1920, 1080)

    # New compact format: {found, x, y, what}
    mock_client = _mock_client_response(
        '{"found": true, "x": 0.5, "y": 0.3, "what": "Submit button"}'
    )

    with patch.object(ve, "_client", mock_client):
        with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
            with patch.object(ve, "PRIVACY_MODE", False):
                result = ve.analyze_screen("click the submit button")

    assert result["success"] is True
    assert result["coordinates"] is not None
    assert result["coordinates"]["x"] == 960   # int(0.5 * 1920)
    assert result["coordinates"]["y"] == 324   # int(0.3 * 1080)


@patch("backend.modules.vision_engine._capture_screen")
def test_click_mode_not_found_returns_none(mock_capture):
    """
    When Gemini says {found: false}, coordinates should be None.
    """
    import backend.modules.vision_engine as ve

    fake_jpg = _make_fake_screenshot_bytes()
    mock_capture.return_value = (fake_jpg, 1920, 1080)

    mock_client = _mock_client_response(
        '{"found": false, "what": "submit button not visible"}'
    )

    with patch.object(ve, "_client", mock_client):
        with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
            with patch.object(ve, "PRIVACY_MODE", False):
                result = ve.analyze_screen("click the submit button")

    assert result["success"] is True   # API call succeeded; element just wasn't found
    assert result["coordinates"] is None
    assert "not" in result["description"].lower() or "could not" in result["description"].lower()


@patch("backend.modules.vision_engine._capture_screen")
def test_coordinate_boundary_clamping(mock_capture):
    """
    Normalized coords of 0.999 on a 1920x1080 screen should be clamped
    to (1919, 1079) — never equal to or beyond screen dimensions.
    """
    import backend.modules.vision_engine as ve

    fake_jpg = _make_fake_screenshot_bytes()
    mock_capture.return_value = (fake_jpg, 1920, 1080)

    mock_client = _mock_client_response(
        '{"found": true, "x": 0.999, "y": 0.999, "what": "bottom-right element"}'
    )

    with patch.object(ve, "_client", mock_client):
        with patch.object(ve, "GEMINI_API_KEY", "fake-key"):
            with patch.object(ve, "PRIVACY_MODE", False):
                result = ve.analyze_screen("click the bottom right element")

    assert result["coordinates"] is not None
    assert result["coordinates"]["x"] < 1920
    assert result["coordinates"]["y"] < 1080
    assert result["coordinates"]["x"] >= 0
    assert result["coordinates"]["y"] >= 0


def test_screenshot_cache_reuse():
    """
    Calling _capture_screen twice within CACHE_TTL_SEC should reuse the cache
    (mss.MSS is called only once).
    """
    import importlib
    import backend.modules.vision_engine as ve

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key", "VISION_PRIVACY_MODE": "false"}):
        importlib.reload(ve)

        fake_jpg = _make_fake_screenshot_bytes()

        with patch("mss.MSS") as mock_mss_cls:
            mock_mss = MagicMock()
            mock_mss_cls.return_value.__enter__ = MagicMock(return_value=mock_mss)
            mock_mss_cls.return_value.__exit__ = MagicMock(return_value=False)

            fake_grab = MagicMock()
            fake_grab.width = 1920
            fake_grab.height = 1080
            fake_grab.rgb = b'\x1e\x1e\x1e' * (1920 * 1080)
            mock_mss.grab.return_value = fake_grab
            mock_mss.monitors = [None, {"left": 0, "top": 0, "width": 1920, "height": 1080}]

            with patch("PIL.Image.frombytes") as mock_frombytes:
                mock_img = MagicMock()
                buf = io.BytesIO()
                from PIL import Image
                Image.new("RGB", (100, 50)).save(buf, format="JPEG")
                mock_img.resize.return_value = mock_img
                mock_img.save = lambda b, **kw: b.write(buf.getvalue())
                mock_frombytes.return_value = mock_img

                # Force cache reset
                ve._last_capture_time = 0.0
                ve._last_screenshot_bytes = None

                # First call — hits mss
                bytes1, w1, h1 = ve._capture_screen()
                # Second call within TTL — uses cache
                bytes2, w2, h2 = ve._capture_screen()

            # mss.MSS should only be entered once
            assert mock_mss_cls.return_value.__enter__.call_count == 1

    importlib.reload(ve)
