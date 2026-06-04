"""
tests/unit/test_camera_recognition.py — THING Phase 2
Unit tests for camera_recognition.py using mock dependencies.

Runs isolated from a real physical camera or real Gemini credentials.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock


def _mock_client_response(text: str) -> MagicMock:
    """Mock Gemini SDK Client response."""
    mock_response = MagicMock()
    mock_response.text = text

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@patch("cv2.VideoCapture")
def test_capture_webcam_frame_success(mock_video_capture):
    """Verifies that frame capture opens capture index, reads frame, and releases successfully."""
    import numpy as np
    from backend.modules.camera_recognition import capture_webcam_frame

    # Use a real numpy array with non-zero values so the darkness check (np.mean > 2.0) passes
    # on the first attempt — preventing the retry loop from firing.
    bright_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 128

    mock_cap = MagicMock()
    mock_video_capture.return_value = mock_cap
    mock_cap.isOpened.return_value = True
    # Warm-up reads (5) + the real read all return the bright frame
    mock_cap.read.return_value = (True, bright_frame)

    with patch("cv2.imencode") as mock_imencode:
        mock_imencode.return_value = (True, MagicMock(tobytes=lambda: b"fake-jpeg-bytes"))
        img_bytes = capture_webcam_frame()

    assert img_bytes == b"fake-jpeg-bytes"
    mock_cap.release.assert_called_once()


@patch("cv2.VideoCapture")
def test_capture_webcam_frame_failure(mock_video_capture):
    """Verifies camera capture handles errors gracefully and returns None."""
    from backend.modules.camera_recognition import capture_webcam_frame

    mock_cap = MagicMock()
    mock_video_capture.return_value = mock_cap
    mock_cap.isOpened.return_value = False

    img_bytes = capture_webcam_frame()
    assert img_bytes is None


@patch("backend.modules.camera_recognition.capture_webcam_frame")
def test_recognize_camera_context_privacy_mode(mock_capture):
    """Verifies that privacy mode active blocks capture."""
    import backend.modules.camera_recognition as cr
    
    with patch.object(cr, "PRIVACY_MODE", True):
        result = cr.recognize_camera_context()

    assert result["success"] is False
    assert "privacy" in result["description"].lower()


@patch("backend.modules.camera_recognition.capture_webcam_frame")
def test_recognize_camera_context_no_api_key(mock_capture):
    """Verifies missing api key triggers warning."""
    import backend.modules.camera_recognition as cr
    mock_capture.return_value = b"fake-bytes"

    with patch.object(cr, "client", None):
        with patch.object(cr, "GEMINI_API_KEY", ""):
            with patch.object(cr, "PRIVACY_MODE", False):
                result = cr.recognize_camera_context()

    assert result["success"] is False
    assert "Gemini API Client" in result["description"]


@patch("backend.modules.camera_recognition.capture_webcam_frame")
def test_recognize_camera_context_known_person(mock_capture):
    """Verifies that recognizing a known person parses fields correctly."""
    import backend.modules.camera_recognition as cr
    mock_capture.return_value = b"fake-bytes"

    mock_json = {
        "people": [
            {
                "name": "Raj",
                "box_2d": [100, 200, 300, 400],
                "activity": "smiling at the camera"
            }
        ],
        "environment": "Home office with high-end PC setup",
        "description": "I see Raj smiling at the camera in a modern home office."
    }

    mock_client = _mock_client_response(json.dumps(mock_json))

    with patch.object(cr, "client", mock_client):
        with patch.object(cr, "GEMINI_API_KEY", "fake-key"):
            with patch.object(cr, "PRIVACY_MODE", False):
                result = cr.recognize_camera_context()

    assert result["success"] is True
    assert "smiling" in result["description"]
    assert len(result["people"]) == 1
    assert result["people"][0]["name"] == "Raj"
    assert result["environment"] == "Home office with high-end PC setup"
    assert result["is_new_person"] is False


@patch("backend.modules.camera_recognition.capture_webcam_frame")
def test_recognize_camera_context_new_person(mock_capture):
    """Verifies unrecognized person triggers face enrollment state transition."""
    import backend.modules.camera_recognition as cr
    from backend.engine.state_manager import state_manager, AssistantState
    mock_capture.return_value = b"fake-bytes"

    mock_json = {
        "people": [
            {
                "name": "New Person",
                "box_2d": [150, 250, 350, 450],
                "activity": "waving hand"
            }
        ],
        "environment": "Living room",
        "description": "I see an unrecognized person waving at the camera."
    }

    mock_client = _mock_client_response(json.dumps(mock_json))

    with patch("builtins.open", MagicMock()):
        with patch.object(cr, "client", mock_client):
            with patch.object(cr, "GEMINI_API_KEY", "fake-key"):
                with patch.object(cr, "PRIVACY_MODE", False):
                    result = cr.recognize_camera_context()

    assert result["success"] is True
    assert "unrecognized" in result["description"].lower() or "someone new" in result["description"].lower()
    assert result["is_new_person"] is True
    assert state_manager.current_state == AssistantState.REGISTERING_FACE
    
    # Cleanup state
    state_manager.set_state(AssistantState.IDLE)


def test_register_pending_face_success():
    """Verifies that submitting a name saves face from temp to registry and updates JSON."""
    from backend.modules.camera_recognition import register_pending_face
    from backend.engine.state_manager import state_manager, AssistantState
    
    state_manager.set_state(AssistantState.REGISTERING_FACE)

    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("os.rename") as mock_rename:
            with patch("builtins.open", MagicMock()):
                with patch("json.load") as mock_load:
                    mock_load.return_value = {"registered": []}
                    with patch("json.dump") as mock_dump:
                        res = register_pending_face("this is John")

    assert "John" in res
    assert state_manager.current_state == AssistantState.IDLE
