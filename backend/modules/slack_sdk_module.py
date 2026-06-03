"""
slack_sdk_module.py — THING Phase 4B
Slack API integration via slack_sdk.

Provides:
  - send_message(channel, text)     — send a message to a channel
  - list_channels()                  — list accessible channels
  - get_recent_messages(channel, n)  — read last N messages from a channel
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _get_slack_client():
    """
    Returns an authenticated Slack WebClient using the stored OAuth token.
    """
    try:
        from slack_sdk import WebClient
    except ImportError:
        raise RuntimeError(
            "slack_sdk is not installed. Run: pip install slack-sdk>=3.27.0"
        )

    from backend.core.oauth_manager import get_token, is_connected
    if not is_connected("slack"):
        raise RuntimeError(
            "Slack is not connected. Open THING's Integrations panel and click 'Connect Slack'."
        )

    token = get_token("slack")
    return WebClient(token=token)


# ─── Channel name → ID resolution cache ─────────────────────────────
_channel_cache: Dict[str, str] = {}  # name → id


def _resolve_channel_id(client, channel_name: str) -> Optional[str]:
    """
    Resolves a channel name like '#general' or 'general' to its Slack channel ID.
    Uses a local cache to avoid repeated API calls.
    """
    # Strip leading # if present
    name = channel_name.lstrip("#").lower().strip()

    if name in _channel_cache:
        return _channel_cache[name]

    try:
        response = client.conversations_list(types="public_channel,private_channel", limit=200)
        channels = response.get("channels", [])
        for ch in channels:
            ch_name = ch.get("name", "").lower()
            _channel_cache[ch_name] = ch["id"]

        return _channel_cache.get(name)
    except Exception as exc:
        logger.error("[Slack] Could not resolve channel '%s': %s", channel_name, exc)
        return None


def send_message(channel: str, text: str) -> str:
    """
    Sends a message to a Slack channel.

    Args:
        channel: Channel name (e.g. '#general' or 'general') or channel ID.
        text:    Message text to send.

    Returns:
        Confirmation string for voice output.
    """
    try:
        client = _get_slack_client()

        # Determine if channel is an ID or a name
        if channel.startswith("C") and len(channel) >= 9:
            channel_id = channel  # already an ID
        else:
            channel_id = _resolve_channel_id(client, channel)
            if not channel_id:
                return (
                    f"Could not find Slack channel '{channel}'. "
                    "Make sure the channel exists and THING has been invited to it."
                )

        response = client.chat_postMessage(channel=channel_id, text=text)
        if response.get("ok"):
            clean_name = channel.lstrip("#")
            return f"Message sent to #{clean_name} on Slack: '{text}'"
        else:
            return f"Slack message failed: {response.get('error', 'Unknown error')}"

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Slack] send_message error: %s", exc)
        return f"Failed to send Slack message: {exc}"


def list_channels() -> str:
    """
    Lists accessible Slack channels.

    Returns:
        A voice-readable list of channel names.
    """
    try:
        client = _get_slack_client()
        response = client.conversations_list(types="public_channel", limit=50)
        channels = response.get("channels", [])

        if not channels:
            return "No public Slack channels found."

        names = [f"#{ch['name']}" for ch in channels[:10]]
        total = len(channels)
        shown = len(names)

        if total > shown:
            return (
                f"You have {total} channels. Here are the first {shown}: "
                f"{', '.join(names)}."
            )
        return f"Your Slack channels: {', '.join(names)}."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Slack] list_channels error: %s", exc)
        return "Failed to list Slack channels."


def get_recent_messages(channel: str, n: int = 5) -> str:
    """
    Reads the last N messages from a Slack channel.

    Args:
        channel: Channel name or ID.
        n:       Number of recent messages to retrieve (max 10).

    Returns:
        A voice-readable summary of recent messages.
    """
    try:
        client = _get_slack_client()
        n = max(1, min(10, n))

        if channel.startswith("C") and len(channel) >= 9:
            channel_id = channel
        else:
            channel_id = _resolve_channel_id(client, channel)
            if not channel_id:
                return f"Could not find Slack channel '{channel}'."

        response = client.conversations_history(channel=channel_id, limit=n)
        messages = response.get("messages", [])

        if not messages:
            return f"No recent messages in #{channel.lstrip('#')}."

        # Resolve user IDs to display names
        formatted = []
        for msg in messages:
            user_id = msg.get("user", "")
            text = msg.get("text", "").strip()
            if not text:
                continue
            try:
                user_info = client.users_info(user=user_id)
                display_name = (
                    user_info.get("user", {})
                    .get("profile", {})
                    .get("display_name") or
                    user_info.get("user", {}).get("real_name", "Someone")
                )
            except Exception:
                display_name = "Someone"
            formatted.append(f"{display_name} said: {text}")

        if not formatted:
            return f"No readable messages in #{channel.lstrip('#')}."

        clean_name = channel.lstrip("#")
        return f"Recent messages in #{clean_name}: " + ". ".join(formatted) + "."

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("[Slack] get_recent_messages error: %s", exc)
        return "Failed to retrieve Slack messages."
