"""
offline_capability_filter.py — THING v5.5
Determines if an action can be executed based on the current network state.
"""

def can_execute(action_name: str) -> bool:
    """
    Returns True if the action can execute offline, 
    False if it strictly requires the internet (Tier 3).
    """
    tier_3_actions = {
        "search_web",
        "play_youtube",
        "vision_query",
        "camera_recognition",
        # Spotify SDK needs internet
        "spotify_play",
        "spotify_pause", 
        "spotify_resume",
        "spotify_skip",
        "spotify_previous",
        "spotify_volume",
        "spotify_now_playing",
        # Google Calendar API needs internet
        "calendar_query",
        "calendar_create",
        # Slack API needs internet
        "slack_send",
        "slack_read",
        "slack_channels",
    }
    
    return action_name not in tier_3_actions

def get_offline_error_message(action_name: str) -> str:
    """Returns a graceful user-friendly message when a Tier 3 action is blocked."""
    if action_name.startswith("spotify_"):
        return "I cannot control Spotify without an internet connection."
    if action_name.startswith("calendar_"):
        return "I need an internet connection to access your Google Calendar."
    if action_name.startswith("slack_"):
        return "I need an internet connection to use Slack."
    if action_name == "search_web":
        return "I cannot search the web while offline."
    if action_name == "play_youtube":
        return "I cannot play YouTube videos without an internet connection."
    if action_name in ("vision_query", "camera_recognition"):
        return "My vision capabilities require an internet connection."
    
    return "I cannot perform this action while offline."
