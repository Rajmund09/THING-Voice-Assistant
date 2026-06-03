"""
google_calendar.py — THING Phase 4B
Google Calendar read/write via google-api-python-client.

Provides:
  - get_events_today()        — returns today's events
  - get_events_tomorrow()     — returns tomorrow's events
  - get_events_this_week()    — returns events for the next 7 days
  - create_event(...)         — creates a new calendar event
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _get_calendar_service():
    """
    Builds and returns an authenticated Google Calendar API service object.
    Uses the stored OAuth token from oauth_manager.
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        raise RuntimeError(
            "google-api-python-client is not installed. "
            "Run: pip install google-api-python-client google-auth"
        )

    from backend.core.oauth_manager import get_token, is_connected
    if not is_connected("google"):
        raise RuntimeError(
            "Google is not connected. Open THING's Integrations panel and click 'Connect Google'."
        )

    token = get_token("google")
    creds = Credentials(token=token)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service


def _format_event_for_voice(event: Dict[str, Any]) -> str:
    """Converts a raw API event dict into a natural voice-readable string."""
    summary = event.get("summary", "Untitled Event")
    start = event.get("start", {})

    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"])
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        return f"{summary} at {time_str}"
    elif "date" in start:
        return f"{summary} (all day)"
    return summary


def _get_events_in_range(
    time_min: datetime,
    time_max: datetime,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Fetches calendar events in the given UTC time range."""
    service = _get_calendar_service()

    time_min_str = time_min.astimezone(timezone.utc).isoformat()
    time_max_str = time_max.astimezone(timezone.utc).isoformat()

    result = service.events().list(
        calendarId="primary",
        timeMin=time_min_str,
        timeMax=time_max_str,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return result.get("items", [])


def get_events_today() -> str:
    """
    Fetches and formats today's calendar events as a voice-readable string.

    Returns:
        A string like "You have 2 events today: Team standup at 10:00 AM, and Lunch with Sarah at 1:00 PM."
    """
    try:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        events = _get_events_in_range(start_of_day, end_of_day)
        if not events:
            return "You have no events scheduled for today."

        formatted = [_format_event_for_voice(e) for e in events]
        count = len(formatted)
        if count == 1:
            return f"You have 1 event today: {formatted[0]}."
        return f"You have {count} events today: {', '.join(formatted[:-1])}, and {formatted[-1]}."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Calendar] get_events_today error: %s", exc)
        return "Failed to retrieve today's calendar events."


def get_events_tomorrow() -> str:
    """
    Fetches and formats tomorrow's calendar events.

    Returns:
        A voice-readable events summary for tomorrow.
    """
    try:
        now = datetime.now(timezone.utc)
        start_of_tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_tomorrow = start_of_tomorrow + timedelta(days=1)

        events = _get_events_in_range(start_of_tomorrow, end_of_tomorrow)
        if not events:
            return "You have no events scheduled for tomorrow."

        formatted = [_format_event_for_voice(e) for e in events]
        count = len(formatted)
        if count == 1:
            return f"You have 1 event tomorrow: {formatted[0]}."
        return f"You have {count} events tomorrow: {', '.join(formatted[:-1])}, and {formatted[-1]}."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Calendar] get_events_tomorrow error: %s", exc)
        return "Failed to retrieve tomorrow's calendar events."


def get_events_this_week() -> str:
    """
    Fetches events for the next 7 days.

    Returns:
        A voice-readable summary of this week's events.
    """
    try:
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=7)

        events = _get_events_in_range(now, end, max_results=20)
        if not events:
            return "You have no events in the next 7 days."

        formatted = [_format_event_for_voice(e) for e in events]
        count = len(formatted)
        return f"You have {count} event{'s' if count != 1 else ''} this week: {', '.join(formatted)}."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Calendar] get_events_this_week error: %s", exc)
        return "Failed to retrieve this week's events."


def create_event(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: str = "",
    location: str = ""
) -> str:
    """
    Creates a new Google Calendar event.

    Args:
        title:       Event title/summary.
        start_time:  ISO 8601 datetime string, e.g. "2026-05-24T14:00:00".
        end_time:    ISO 8601 datetime string. Defaults to 1 hour after start.
        description: Optional event description.
        location:    Optional event location.

    Returns:
        Confirmation string for voice output.
    """
    try:
        service = _get_calendar_service()

        # Parse start time
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError:
            return f"Invalid start time format: '{start_time}'. Please use ISO format."

        # Default end = start + 1 hour
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)

        # Ensure timezone info
        if start_dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            start_dt = start_dt.replace(tzinfo=local_tz)
            end_dt = end_dt.replace(tzinfo=local_tz)

        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start_dt.isoformat()},
            "end":   {"dateTime": end_dt.isoformat()},
        }

        created = service.events().insert(calendarId="primary", body=event_body).execute()
        time_str = start_dt.strftime("%I:%M %p on %B %d").lstrip("0")
        return f"Created event '{title}' at {time_str} on your Google Calendar."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Calendar] create_event error: %s", exc)
        return f"Failed to create calendar event: {exc}"
