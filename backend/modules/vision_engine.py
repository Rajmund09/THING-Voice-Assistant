"""
vision_engine.py — THING v4.7 (Phase 2)
Multimodal Vision Engine.

Captures the current screen and sends it to Gemini Vision (gemini-1.5-flash)
for analysis. Uses the new google-genai SDK (not the deprecated google-generativeai).

Supports two modes:
  1. Description mode — natural language description of screen content.
  2. Click mode     — returns pixel (x, y) coordinates of a UI element.

Returns a structured dict:
  {
    "description":   str,           # Natural language analysis
    "coordinates":   {"x": int, "y": int} | None,  # For ui_click mode
    "screenshot_b64": str | None,   # JPEG base64 for frontend preview
    "success":       bool
  }
"""

import os
import io
import time
import base64
import logging
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────────────

GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
PRIVACY_MODE     = os.getenv("VISION_PRIVACY_MODE", "false").lower() == "true"
SCREENSHOT_QUALITY = int(os.getenv("VISION_SCREENSHOT_QUALITY", "85"))
MAX_WIDTH        = 1280   # Resize to this width for API efficiency
CACHE_TTL_SEC    = 1.0    # Reuse screenshot captured within this window

# Model: gemini-2.5-flash — fastest & latest, configurable via .env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ─────────────────────────────────────────────────────────────────
#  Gemini client singleton (avoids per-call TLS overhead)
# ─────────────────────────────────────────────────────────────────

_client = None

if GEMINI_API_KEY:
    try:
        from google import genai as _genai_module
        _client = _genai_module.Client(api_key=GEMINI_API_KEY)
        logger.debug("[Vision] Gemini client initialised (model: %s)", GEMINI_MODEL)
    except Exception as _e:
        logger.warning("[Vision] Could not initialise Gemini client: %s", _e)

# ─────────────────────────────────────────────────────────────────
#  Screenshot cache (avoids double-captures in compound commands)
# ─────────────────────────────────────────────────────────────────

_last_capture_time: float = 0.0
_last_screenshot_bytes: Optional[bytes] = None
_last_screenshot_size: Optional[tuple] = None   # (width, height) actual screen


# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────

def analyze_screen(query: str = "Describe what is on the screen.") -> Dict[str, Any]:
    """
    Main entry point.
    Captures the screen and sends it + query to Gemini Vision.

    Args:
        query: Natural language instruction for Gemini.

    Returns:
        dict with keys: description, coordinates, screenshot_b64, success, elapsed_ms
    """
    t_start = time.monotonic()

    if PRIVACY_MODE:
        return _error_result("Vision is disabled. Set VISION_PRIVACY_MODE=false in .env to enable.")

    if not GEMINI_API_KEY:
        return _error_result(
            "GEMINI_API_KEY is not set. Add it to your .env file to use vision features."
        )

    # 1. Capture screen
    try:
        img_bytes, screen_w, screen_h = _capture_screen()
    except Exception as e:
        logger.error("[Vision] Screenshot failed: %s", e)
        return _error_result("Failed to capture screen. Make sure the display is accessible.")

    # 2. Encode for frontend preview
    b64_str = base64.b64encode(img_bytes).decode("utf-8")

    # 3. Call Gemini Vision
    try:
        gemini_response = _call_gemini_vision(img_bytes, query, screen_w, screen_h)
    except Exception as e:
        logger.error("[Vision] Gemini API error: %s", e)
        return _error_result(f"Vision API error: {str(e)[:160]}")

    elapsed_ms = round((time.monotonic() - t_start) * 1000, 1)
    logger.info("[Vision] analyze_screen completed in %.1fms", elapsed_ms)

    return {
        "description":    gemini_response.get("description", "Could not analyze screen."),
        "coordinates":    gemini_response.get("coordinates"),
        "screenshot_b64": b64_str,
        "success":        True,
        "elapsed_ms":     elapsed_ms,
        "model":          GEMINI_MODEL,
    }


def capture_screen_only() -> Optional[bytes]:
    """Convenience: just take a screenshot and return raw JPEG bytes."""
    try:
        img_bytes, _, _ = _capture_screen()
        return img_bytes
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
#  Screen capture
# ─────────────────────────────────────────────────────────────────

def _capture_screen() -> tuple:
    """
    Captures full primary screen using mss (fastest cross-platform library).
    Returns (jpeg_bytes, screen_width, screen_height).
    Uses a 1-second cache to avoid double-captures.
    """
    global _last_capture_time, _last_screenshot_bytes, _last_screenshot_size

    now = time.monotonic()
    if _last_screenshot_bytes and (now - _last_capture_time) < CACHE_TTL_SEC:
        w, h = _last_screenshot_size
        return _last_screenshot_bytes, w, h

    import mss
    from PIL import Image

    with mss.MSS() as sct:
        monitor = sct.monitors[1]   # Primary monitor
        raw = sct.grab(monitor)
        screen_w = raw.width
        screen_h = raw.height

        # Convert to PIL
        img = Image.frombytes("RGB", (screen_w, screen_h), raw.rgb)

    # Resize for API efficiency
    if screen_w > MAX_WIDTH:
        ratio = MAX_WIDTH / screen_w
        new_h = int(screen_h * ratio)
        img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)

    # Encode to JPEG bytes
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=SCREENSHOT_QUALITY, optimize=True)
    jpeg_bytes = buf.getvalue()

    # Cache
    _last_capture_time    = now
    _last_screenshot_bytes = jpeg_bytes
    _last_screenshot_size  = (screen_w, screen_h)

    logger.debug("[Vision] Screenshot: %dx%d → %d bytes", screen_w, screen_h, len(jpeg_bytes))
    return jpeg_bytes, screen_w, screen_h


# ─── DESCRIPTION prompt: plain text only, no JSON (avoids parsing failures) ──
_DESCRIBE_PROMPT = """
You are analyzing a screenshot of a computer screen. Describe what you see in 3-5 complete sentences.
Focus on: what application is open, what content is visible, and any notable UI elements.
IMPORTANT: Always finish your sentences completely. Do NOT cut off mid-sentence.
Do NOT use JSON. Just write plain, natural text.

User request: {query}
"""

# ─── COORDINATE prompt: strict JSON for click targeting ──────────────────────
_COORD_PROMPT = """
You are analyzing a screenshot. Find the UI element the user wants to click.

Rules:
- x_normalized and y_normalized are 0.0 to 1.0 (fraction of image width/height)
- Point to the CENTER of the target element
- The image dimensions represent the full screen

Respond ONLY with this JSON (no markdown, no extra text):
If found:    {{"found": true,  "x": 0.45, "y": 0.32, "what": "brief label"}}
If missing:  {{"found": false, "what": "element not visible"}}

Element to find: {query}
"""


def get_gemini_client():
    global _client
    # If the client has been mocked by tests, return it directly
    if _client is not None:
        from unittest.mock import Mock, MagicMock
        if isinstance(_client, (Mock, MagicMock)):
            return _client
    # For production thread-safety, return a brand new Client
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API Key not configured. Please supply a valid GEMINI_API_KEY in .env.")
    from google import genai as _genai_module
    return _genai_module.Client(api_key=GEMINI_API_KEY)


def _call_gemini_vision(
    img_bytes: bytes,
    user_query: str,
    screen_w: int,
    screen_h: int,
) -> Dict[str, Any]:
    """Sends image + prompt to Gemini Vision using the singleton google-genai client."""
    import json, re
    from google.genai import types

    client = get_gemini_client()

    # Decide mode
    click_keywords = ["click", "press", "tap", "find", "locate", "where is", "coordinates of"]
    wants_click = any(kw in user_query.lower() for kw in click_keywords)

    full_prompt = (_COORD_PROMPT if wants_click else _DESCRIBE_PROMPT).replace("{query}", user_query)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes)),
                    types.Part(text=full_prompt),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
            # Use more tokens for descriptions (800) vs click mode (300 is plenty for JSON)
            max_output_tokens=300 if wants_click else 800,
        ),
    )

    raw_text = response.text.strip()
    logger.debug("[Vision] Raw Gemini response: %s", raw_text[:300])

    # ── Description mode: plain text, return directly ──────────────────────
    if not wants_click:
        # Strip any accidental JSON wrapper if Gemini ignored the instruction
        if raw_text.startswith("{"):
            try:
                data = json.loads(_strip_md_fences(raw_text))
                # Try common field names
                for key in ("description", "text", "answer", "response"):
                    if key in data:
                        return {"description": str(data[key]), "coordinates": None}
            except Exception:
                pass
        return {"description": raw_text, "coordinates": None}

    # ── Click mode: extract JSON coordinates ───────────────────────────────
    clean = _strip_md_fences(raw_text)

    # Strategy 1: direct JSON parse
    try:
        data = json.loads(clean)
        return _parse_coord_json(data, screen_w, screen_h)
    except json.JSONDecodeError:
        pass

    # Strategy 2: regex — find first {...} block
    m = re.search(r"\{[^{}]+\}", clean, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return _parse_coord_json(data, screen_w, screen_h)
        except json.JSONDecodeError:
            pass

    # Strategy 3: regex — extract x/y directly from any number pairs
    nums = re.findall(r"(?:x|x_normalized)[\s:]+([0-9.]+).*?(?:y|y_normalized)[\s:]+([0-9.]+)", clean, re.IGNORECASE | re.DOTALL)
    if nums:
        try:
            x_n, y_n = float(nums[0][0]), float(nums[0][1])
            if 0 <= x_n <= 1 and 0 <= y_n <= 1:
                return {
                    "description": "Found element.",
                    "coordinates": {"x": int(x_n * screen_w), "y": int(y_n * screen_h)},
                }
        except ValueError:
            pass

    logger.warning("[Vision] Could not parse click coordinates from: %s", raw_text[:200])
    return {"description": "Could not locate the element on screen.", "coordinates": None}


def _strip_md_fences(text: str) -> str:
    """Remove ```json ... ``` and similar markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _parse_coord_json(data: dict, screen_w: int, screen_h: int) -> Dict[str, Any]:
    """Parse the new compact JSON format: {found, x, y, what}."""
    if not data.get("found", False):
        label = data.get("what", "element not visible")
        return {"description": f"Could not find: {label}", "coordinates": None}

    # Support both compact (x, y) and verbose (x_normalized, y_normalized) keys
    x_n = data.get("x") or data.get("x_normalized")
    y_n = data.get("y") or data.get("y_normalized")

    if x_n is None or y_n is None:
        return {"description": "Coordinates missing from response.", "coordinates": None}

    x_n, y_n = float(x_n), float(y_n)
    px_x = max(0, min(int(x_n * screen_w), screen_w - 1))
    px_y = max(0, min(int(y_n * screen_h), screen_h - 1))

    label = data.get("what", "element")
    logger.info("[Vision] Found '%s' at (%d, %d) on %dx%d", label, px_x, px_y, screen_w, screen_h)
    return {
        "description": f"Found: {label}",
        "coordinates": {"x": px_x, "y": px_y},
    }


# ─────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────

def _error_result(msg: str) -> Dict[str, Any]:
    return {
        "description":    msg,
        "coordinates":    None,
        "screenshot_b64": None,
        "success":        False,
    }
