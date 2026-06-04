"""
test_suggestion_engine.py — THING v5.0
Unit tests for proactive suggestion logic.
"""

import pytest
from backend.core.suggestion_engine import evaluate_clipboard, evaluate_system_load, evaluate_idle, evaluate_time

def test_zoom_link_triggers_suggestion():
    text = "Join Zoom Meeting: https://zoom.us/j/123456789"
    res = evaluate_clipboard(text)
    assert res is not None
    assert res["id"] == "meeting_link_detected"
    assert "meeting" in res["message"].lower()

def test_meet_link_triggers_suggestion():
    text = "Join Meet: https://meet.google.com/abc-defg-hij"
    res = evaluate_clipboard(text)
    assert res is not None
    assert res["id"] == "meeting_link_detected"

def test_teams_link_triggers_suggestion():
    text = "Teams: https://teams.microsoft.com/l/meetup-join/19%3ameeting_xyz"
    res = evaluate_clipboard(text)
    assert res is not None
    assert res["id"] == "meeting_link_detected"

def test_non_meeting_link_ignored():
    text = "Check this out: https://google.com"
    res = evaluate_clipboard(text)
    assert res is None

def test_high_cpu_triggers_suggestion():
    res = evaluate_system_load(95.0, 50.0)
    assert res is not None
    assert res["id"] == "high_cpu_usage"
    assert "95%" in res["message"]

def test_high_ram_triggers_suggestion():
    res = evaluate_system_load(50.0, 92.0)
    assert res is not None
    assert res["id"] == "high_ram_usage"

def test_normal_load_ignored():
    res = evaluate_system_load(40.0, 60.0)
    assert res is None

def test_idle_20_min_triggers_lock_suggestion():
    res = evaluate_idle(20.5)
    assert res is not None
    assert res["id"] == "system_idle_detected"
    assert "lock" in res["message"].lower()

def test_idle_5_min_ignored():
    res = evaluate_idle(5.0)
    assert res is None

def test_eod_hour_triggers_suggestion():
    res = evaluate_time(17, 17)
    assert res is not None
    assert res["id"] == "end_of_day_suggestion"

def test_non_eod_hour_ignored():
    res = evaluate_time(10, 17)
    assert res is None


def test_high_cpu_triggers_suggestion_personalized():
    res = evaluate_system_load(95.0, 50.0, top_cpu_process="chrome.exe")
    assert res is not None
    assert res["id"] == "high_cpu_usage"
    assert "chrome.exe" in res["message"]


def test_high_ram_triggers_suggestion_personalized():
    res = evaluate_system_load(50.0, 92.0, top_ram_process="pycharm.exe")
    assert res is not None
    assert res["id"] == "high_ram_usage"
    assert "pycharm.exe" in res["message"]
