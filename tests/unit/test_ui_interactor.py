"""
test_ui_interactor.py — THING Phase 2 Tests
Unit tests for ui_interactor.py using mocked pyautogui.
All tests run without a real mouse or screen.
"""

import pytest
from unittest.mock import patch, MagicMock, call


# ─────────────────────────────────────────────────────────────────
#  click_at
# ─────────────────────────────────────────────────────────────────

@patch("backend.modules.ui_interactor._get_pyautogui")
@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_click_at_calls_moveto_and_click(mock_size, mock_pyag_getter):
    """click_at should call moveTo then click with correct coordinates."""
    mock_pyag = MagicMock()
    mock_pyag_getter.return_value = mock_pyag

    from backend.modules.ui_interactor import click_at
    result = click_at(500, 400)

    mock_pyag.moveTo.assert_called_once_with(500, 400, duration=0.3)
    mock_pyag.click.assert_called_once_with(500, 400, button="left")
    assert "500" in result and "400" in result
    assert "successfully" in result.lower()


@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_click_at_out_of_bounds_refused(mock_size):
    """click_at should refuse coordinates outside screen bounds."""
    from backend.modules.ui_interactor import click_at
    result = click_at(9999, 9999)
    assert "outside the screen" in result.lower()


@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_click_at_negative_coords_refused(mock_size):
    """Negative coordinates should be refused."""
    from backend.modules.ui_interactor import click_at
    result = click_at(-100, -50)
    assert "outside the screen" in result.lower()


@patch("backend.modules.ui_interactor._get_pyautogui")
@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_right_click_uses_correct_button(mock_size, mock_pyag_getter):
    """right_click_at should pass button='right' to pyautogui."""
    mock_pyag = MagicMock()
    mock_pyag_getter.return_value = mock_pyag

    from backend.modules.ui_interactor import right_click_at
    right_click_at(300, 200)
    mock_pyag.click.assert_called_once_with(300, 200, button="right")


# ─────────────────────────────────────────────────────────────────
#  double_click_at
# ─────────────────────────────────────────────────────────────────

@patch("backend.modules.ui_interactor._get_pyautogui")
@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_double_click_at_calls_doubleclick(mock_size, mock_pyag_getter):
    """double_click_at should call pyautogui.doubleClick."""
    mock_pyag = MagicMock()
    mock_pyag_getter.return_value = mock_pyag

    from backend.modules.ui_interactor import double_click_at
    result = double_click_at(600, 300)
    mock_pyag.doubleClick.assert_called_once_with(600, 300)
    assert "successfully" in result.lower()


# ─────────────────────────────────────────────────────────────────
#  hover_at
# ─────────────────────────────────────────────────────────────────

@patch("backend.modules.ui_interactor._get_pyautogui")
@patch("backend.modules.ui_interactor._screen_size", return_value=(1920, 1080))
def test_hover_at_calls_moveto(mock_size, mock_pyag_getter):
    """hover_at should call moveTo without clicking."""
    mock_pyag = MagicMock()
    mock_pyag_getter.return_value = mock_pyag

    from backend.modules.ui_interactor import hover_at
    result = hover_at(100, 200)
    mock_pyag.moveTo.assert_called_once_with(100, 200, duration=0.4)
    mock_pyag.click.assert_not_called()
    assert "200" in result
