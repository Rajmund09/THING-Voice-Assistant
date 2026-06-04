"""
camera_recognition.py — THING v4.8
Webcam facial, action, and environment recognition engine using Gemini Vision.

Captures real-time webcam frames, identifies registered users (e.g. Raj), detects new
people, recognizes their activities/environment, and facilitates dynamic live registration.
"""

import os
import io
import time
import json
import base64
import logging
from typing import Optional, Dict, Any, List

import cv2
from dotenv import load_dotenv

from backend.engine.state_manager import state_manager, AssistantState
from backend.modules.vision_engine import GEMINI_MODEL, GEMINI_API_KEY, PRIVACY_MODE

load_dotenv(override=True)
logger = logging.getLogger(__name__)

client = None

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACES_DIR = os.path.join(BASE_DIR, "backend", "data", "faces")
PEOPLE_JSON_PATH = os.path.join(BASE_DIR, "backend", "data", "registered_people.json")

# Ensure face registry directory exists
os.makedirs(FACES_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
#  Prompts
# ─────────────────────────────────────────────────────────────────

_CAMERA_PROMPT = """
You are a precise real-time vision observer for the AI assistant THING.
You will be provided with:
1. Reference face images of registered users (if any). Each reference image has a label "This is a reference image of [Name]".
2. The current webcam frame image.

Analyze the webcam frame and identify who is present, what they are doing, and the surrounding environment.

### TARGET OUTPUT SCHEMA
Your final response MUST be a JSON object inside a markdown code block with the following keys:
{
  "people": [
    {
      "name": "Raj" or "New Person" or another matched registered name,
      "box_2d": [ymin, xmin, ymax, xmax],  // Normalized 0-1000 bounding box of their FACE only
      "activity": "typing on laptop" // Precise natural description of what they are doing
    }
  ],
  "environment": "home office, clean desk, books in background",
  "description": "Natural summary description for verbal reply."
}

### CRITICAL RULES:
1. Bounding Box: The "box_2d" field should define the bounding box of their FACE, not their whole body. Use [ymin, xmin, ymax, xmax] coordinates normalized from 0 to 1000 (integers).
2. Reference matching: Compare the webcam frame face(s) with the reference images. The primary user is "Raj" (the creator/developer). If a face matches Raj's reference image, label them as "Raj". If they match another registered face, use their registered name. If they do not match any references, label them as "New Person".
3. Return ONLY a valid JSON object. No other text.
"""


# ─────────────────────────────────────────────────────────────────
#  Helper: Webcam Frame Capture
# ─────────────────────────────────────────────────────────────────

def capture_webcam_frame() -> Optional[bytes]:
    """
    Programmatically capture a single high-quality frame from camera 0.
    Includes warm-up frames to ensure auto-exposure/focus stabilizes.
    If the captured frame is completely black/dark (possibly due to camera lock),
    it retries for a few times to allow the browser to release the hardware lock.
    """
    import numpy as np
    
    max_attempts = 6
    attempt = 0
    frame = None
    ret = False
    
    while attempt < max_attempts:
        logger.info("[Camera] Capturing frame from webcam index 0 (attempt %d/%d)...", attempt + 1, max_attempts)
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
            if not cap.isOpened():
                # Try default fallback
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    logger.warning("[Camera] Could not open camera source 0 on attempt %d.", attempt + 1)
                    attempt += 1
                    time.sleep(0.2)
                    continue
            
            # Set resolution to a reasonable high quality
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Allow camera auto-exposure/focus to stabilize (warm up)
            for _ in range(5):
                cap.read()
                time.sleep(0.05)
                
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                mean_val = float(np.mean(frame))
                logger.info("[Camera] Capture attempt %d: success, mean intensity: %.2f", attempt + 1, mean_val)
                # A completely black/dark frame (lock or uninitialized sensor) has mean near 0.
                # Threshold of 2.0 is safe to distinguish locked camera from actual dark room.
                if mean_val > 2.0:
                    break
                else:
                    logger.warning("[Camera] Captured frame is completely dark/black. Retrying...")
            else:
                logger.warning("[Camera] Failed to read frame from opened camera on attempt %d.", attempt + 1)
        except Exception as e:
            logger.error("[Camera] Exception during attempt %d: %s", attempt + 1, e)
            
        attempt += 1
        time.sleep(0.2) # Sleep to give browser time to release webcam lock
        
    if not ret or frame is None:
        logger.error("[Camera] Failed to retrieve a valid frame after all attempts.")
        return None
        
    try:
        # Encode as JPEG
        success, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not success:
            logger.error("[Camera] Image encoding failed.")
            return None
            
        logger.info("[Camera] Successfully captured webcam frame.")
        return encoded_img.tobytes()
        
    except Exception as e:
        logger.error("[Camera] Exception during JPEG encoding: %s", e, exc_info=True)
        return None


# ─────────────────────────────────────────────────────────────────
#  Helper: Gemini Client Factory
# ─────────────────────────────────────────────────────────────────

def get_gemini_client():
    global client
    # If the client has been mocked by tests, return it directly
    if client is not None:
        from unittest.mock import Mock, MagicMock
        if isinstance(client, (Mock, MagicMock)):
            return client
    # For production thread-safety, return a brand new Client
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai as _genai_module
        return _genai_module.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error("[Camera] Failed to initialize Gemini client: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────
#  Main API: Describe Camera Context (Person/Action/Environment)
# ─────────────────────────────────────────────────────────────────

def recognize_camera_context(user_query: str = "") -> Dict[str, Any]:
    """
    Captures a frame from the webcam, matches against registered faces,
    determines what people are doing, analyzes the environment using Gemini,
    and returns a structured response.
    """
    t0 = time.perf_counter()

    if PRIVACY_MODE:
        return {
            "success": False,
            "description": "Camera/Vision features are disabled due to Privacy Mode being active.",
            "screenshot_b64": None
        }

    # 1. Capture webcam frame
    img_bytes = capture_webcam_frame()
    if not img_bytes:
        return {
            "success": False,
            "description": "I'm sorry, I couldn't access your camera. Make sure no other application is using it and your webcam is connected.",
            "screenshot_b64": None
        }

    # Base64 encode captured frame for frontend preview
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')

    # 2. Build Gemini contents with registered faces
    from google.genai import types

    gemini_client = get_gemini_client()
    if gemini_client is None:
        return {
            "success": False,
            "description": "Gemini API Client is not configured. Please supply a valid GEMINI_API_KEY.",
            "screenshot_b64": img_b64
        }

    parts = []

    # Load registered faces as references
    registered_count = 0
    if os.path.exists(FACES_DIR):
        for filename in os.listdir(FACES_DIR):
            if filename.endswith(('.jpg', '.jpeg', '.png')) and not filename.startswith('temp_'):
                name = os.path.splitext(filename)[0].capitalize()
                filepath = os.path.join(FACES_DIR, filename)
                try:
                    with open(filepath, 'rb') as f:
                        ref_bytes = f.read()
                    # Add reference image and its name
                    parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=ref_bytes)))
                    parts.append(types.Part(text=f"This is a reference image of {name}."))
                    registered_count += 1
                except Exception as e:
                    logger.error("[Camera] Failed to load reference image %s: %s", filepath, e)

    logger.info("[Camera] Loaded %d registered reference faces.", registered_count)

    # Add the current captured webcam frame
    parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes)))
    
    # Custom query enrichment
    custom_query_part = f"\nUser specifically asked: {user_query}" if user_query else ""
    parts.append(types.Part(text=_CAMERA_PROMPT + custom_query_part))

    # 3. Call Gemini Vision
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1000
            )
        )
        raw_text = response.text.strip()
        logger.debug("[Camera] Gemini Response: %s", raw_text)
    except Exception as e:
        logger.error("[Camera] Gemini Vision call failed: %s", e, exc_info=True)
        return {
            "success": False,
            "description": f"Failed to analyze camera frame: {e}",
            "screenshot_b64": img_b64
        }

    # 4. Parse Gemini Response JSON
    parsed_data = {
        "people": [],
        "environment": "Unknown environment",
        "description": "I see you in front of the camera."
    }

    # Strip MD fences and load JSON
    clean_json = raw_text
    if "```json" in clean_json:
        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
    elif "```" in clean_json:
        clean_json = clean_json.split("```")[1].split("```")[0].strip()

    try:
        parsed_data = json.loads(clean_json)
    except Exception as e:
        logger.warning("[Camera] Failed to parse JSON, falling back to regex extraction. Error: %s", e)
        # Fallback parsing in case JSON is slightly malformed
        import re
        desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', clean_json)
        if desc_match:
            parsed_data["description"] = desc_match.group(1)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    # Check for unrecognized people
    has_new_person = False
    for p in parsed_data.get("people", []):
        if p.get("name", "").lower() in ("new person", "unknown", "visitor"):
            has_new_person = True
            p["name"] = "New Person"

    speech_desc = parsed_data.get("description", "Camera analysis complete.")

    # 5. Handle Stateful Registration Loop
    if has_new_person:
        # Temporarily save the frame to faces folder
        temp_path = os.path.join(FACES_DIR, "temp_unrecognized.jpg")
        try:
            with open(temp_path, 'wb') as f:
                f.write(img_bytes)
            logger.info("[Camera] Saved temp frame for face registration: %s", temp_path)
            
            # Transition to stateful registration
            state_manager.set_state(AssistantState.REGISTERING_FACE)
            speech_desc += "\n\nI noticed someone new in the camera! What is their name? Let me know so I can register them."
        except Exception as e:
            logger.error("[Camera] Failed to save temp registration frame: %s", e)

    return {
        "success": True,
        "description": speech_desc,
        "screenshot_b64": img_b64,
        "elapsed_ms": elapsed_ms,
        "model": GEMINI_MODEL,
        "people": parsed_data.get("people", []),
        "environment": parsed_data.get("environment", ""),
        "is_new_person": has_new_person,
        "_vision": True  # triggers visual preview renderer
    }


# ─────────────────────────────────────────────────────────────────
#  Stateful Registration handler
# ─────────────────────────────────────────────────────────────────

def register_pending_face(name: str) -> str:
    """
    Registers the temporarily captured unrecognized face with the provided name,
    moving the image file to the library and updating registered_people.json.
    """
    clean_name = name.strip().replace("'", "").replace('"', "")
    
    # Check if the user input contains trigger phrases like "my name is...", "he is..."
    # We clean these up to get just the actual name
    import re
    prefixes = [
        r"^(?:this is|my name is|he is|she is|call them|call him|call her|they are|it's|its)\s+",
        r"^(?:friend\s+)?(?:named\s+)?",
    ]
    for p in prefixes:
        clean_name = re.sub(p, "", clean_name, flags=re.IGNORECASE).strip()

    # Title case the name
    clean_name = clean_name.title()

    temp_path = os.path.join(FACES_DIR, "temp_unrecognized.jpg")
    if not os.path.exists(temp_path):
        state_manager.set_state(AssistantState.IDLE)
        return "I couldn't find a pending face capture. Please ask me to recognize you or look at the camera again."

    # Move temp image to final file
    safe_filename = clean_name.lower().replace(" ", "_") + ".jpg"
    final_path = os.path.join(FACES_DIR, safe_filename)

    try:
        os.rename(temp_path, final_path)
        logger.info("[Camera] Moved temp face to registered library: %s", final_path)
    except Exception as e:
        logger.error("[Camera] Failed to move registered face file: %s", e)
        state_manager.set_state(AssistantState.IDLE)
        return f"I had an issue saving the registration photo. Please try again."

    # Update database
    registry = {"registered": []}
    if os.path.exists(PEOPLE_JSON_PATH):
        try:
            with open(PEOPLE_JSON_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        except Exception:
            pass

    # Ensure no duplicates
    registry["registered"] = [p for p in registry.get("registered", []) if p.get("name", "").lower() != clean_name.lower()]

    # Add new person
    relative_path = f"backend/data/faces/{safe_filename}"
    registry["registered"].append({
        "name": clean_name,
        "nickname": clean_name,
        "description": f"Registered user named {clean_name}",
        "image_path": relative_path
    })

    try:
        with open(PEOPLE_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)
        logger.info("[Camera] Updated registered_people.json database with %s", clean_name)
    except Exception as e:
        logger.error("[Camera] Failed to update registered_people.json: %s", e)

    # Release lock & reset state
    state_manager.set_state(AssistantState.IDLE)

    return f"Excellent! I've registered {clean_name}. I've saved their picture to my facial database and will recognize them instantly in the future!"
