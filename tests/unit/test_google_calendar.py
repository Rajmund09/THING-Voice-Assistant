"""
test_google_calendar.py — Phase 4B Tests
Unit tests for google_calendar.py — mocks Google API client and oauth_manager.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_google_connected(monkeypatch):
    """Patch oauth_manager so Google appears connected."""
    monkeypatch.setattr("backend.core.oauth_manager.is_connected", lambda s: s == "google")
    monkeypatch.setattr("backend.core.oauth_manager.get_token", lambda s: "fake_google_token" if s == "google" else None)


@pytest.fixture
def mock_calendar_service():
    """Mock the Google Calendar API service object."""
    mock_svc = MagicMock()
    with patch("backend.modules.google_calendar._get_calendar_service", return_value=mock_svc):
        yield mock_svc


# ─── Sample event factory ─────────────────────────────────────────────

def make_event(summary: str, hour: int, minute: int = 0) -> dict:
    dt = datetime.now(timezone.utc).replace(hour=hour, minute=minute)
    return {
        "summary": summary,
        "start": {"dateTime": dt.isoformat()},
        "end": {"dateTime": (dt + timedelta(hours=1)).isoformat()},
    }


def make_all_day_event(summary: str) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "summary": summary,
        "start": {"date": today},
        "end": {"date": today},
    }


# ─── get_events_today ────────────────────────────────────────────────

class TestGetEventsToday:
    def test_returns_single_event(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_today
        mock_calendar_service.events().list().execute.return_value = {
            "items": [make_event("Team Standup", 10, 0)]
        }
        result = get_events_today()
        assert "1 event" in result
        assert "Team Standup" in result

    def test_returns_multiple_events(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_today
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                make_event("Team Standup", 10),
                make_event("Lunch with Sarah", 13),
            ]
        }
        result = get_events_today()
        assert "2 events" in result
        assert "Team Standup" in result
        assert "Lunch with Sarah" in result

    def test_returns_no_events_message(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_today
        mock_calendar_service.events().list().execute.return_value = {"items": []}
        result = get_events_today()
        assert "no events" in result.lower()

    def test_handles_all_day_event(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_today
        mock_calendar_service.events().list().execute.return_value = {
            "items": [make_all_day_event("Company Holiday")]
        }
        result = get_events_today()
        assert "Company Holiday" in result
        assert "all day" in result


# ─── get_events_tomorrow ─────────────────────────────────────────────

class TestGetEventsTomorrow:
    def test_returns_events_for_tomorrow(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_tomorrow
        mock_calendar_service.events().list().execute.return_value = {
            "items": [make_event("Dentist Appointment", 9)]
        }
        result = get_events_tomorrow()
        assert "tomorrow" in result
        assert "Dentist Appointment" in result

    def test_returns_no_events_for_tomorrow(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_tomorrow
        mock_calendar_service.events().list().execute.return_value = {"items": []}
        result = get_events_tomorrow()
        assert "no events" in result.lower()
        assert "tomorrow" in result


# ─── get_events_this_week ────────────────────────────────────────────

class TestGetEventsThisWeek:
    def test_returns_week_events(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_this_week
        mock_calendar_service.events().list().execute.return_value = {
            "items": [
                make_event("Sprint Planning", 9),
                make_event("Code Review", 14),
                make_event("One-on-One", 16),
            ]
        }
        result = get_events_this_week()
        assert "3 events" in result
        assert "this week" in result.lower() or "week" in result

    def test_returns_no_events_message(self, mock_calendar_service):
        from backend.modules.google_calendar import get_events_this_week
        mock_calendar_service.events().list().execute.return_value = {"items": []}
        result = get_events_this_week()
        assert "no events" in result.lower()


# ─── create_event ────────────────────────────────────────────────────

class TestCreateEvent:
    def test_creates_event_successfully(self, mock_calendar_service):
        from backend.modules.google_calendar import create_event
        mock_calendar_service.events().insert().execute.return_value = {
            "id": "event_123",
            "summary": "Team Sync",
        }
        result = create_event(
            title="Team Sync",
            start_time="2026-05-25T14:00:00",
            end_time="2026-05-25T15:00:00",
        )
        assert "Team Sync" in result
        assert "Google Calendar" in result
        # Verify insert was called with the right calendar ID
        insert_calls = mock_calendar_service.events().insert.call_args_list
        real_calls = [c for c in insert_calls if c.kwargs.get("calendarId") == "primary"]
        assert len(real_calls) == 1


    def test_invalid_start_time_returns_error(self, mock_calendar_service):
        from backend.modules.google_calendar import create_event
        result = create_event(title="Bad Event", start_time="not-a-date")
        assert "Invalid" in result or "invalid" in result.lower()

    def test_default_end_time_is_one_hour_after_start(self, mock_calendar_service):
        from backend.modules.google_calendar import create_event
        mock_calendar_service.events().insert().execute.return_value = {"id": "e1", "summary": "Quick Call"}
        create_event(title="Quick Call", start_time="2026-05-25T10:00:00")

        call_kwargs = mock_calendar_service.events().insert.call_args
        body = call_kwargs[1]["body"] if call_kwargs[1] else call_kwargs[0][1]
        start_dt = datetime.fromisoformat(body["start"]["dateTime"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(body["end"]["dateTime"].replace("Z", "+00:00"))
        delta = end_dt - start_dt
        assert delta == timedelta(hours=1)

    def test_error_when_not_connected(self, monkeypatch):
        monkeypatch.setattr("backend.core.oauth_manager.is_connected", lambda s: False)
        from backend.modules.google_calendar import create_event
        result = create_event(title="Test", start_time="2026-05-25T10:00:00")
        assert "not connected" in result.lower() or "Connect" in result
