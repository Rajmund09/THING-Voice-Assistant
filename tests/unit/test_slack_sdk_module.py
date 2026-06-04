"""
test_slack_sdk_module.py — Phase 4B Tests
Unit tests for slack_sdk_module.py — mocks slack_sdk WebClient and oauth_manager.
"""

import pytest
from unittest.mock import patch, MagicMock, call


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_slack_connected(monkeypatch):
    """Patch oauth_manager so Slack appears connected."""
    monkeypatch.setattr("backend.core.oauth_manager.is_connected", lambda s: s == "slack")
    monkeypatch.setattr("backend.core.oauth_manager.get_token", lambda s: "fake_slack_token" if s == "slack" else None)


@pytest.fixture
def mock_slack_client():
    """Inject a mock Slack WebClient."""
    mock_client = MagicMock()
    with patch("backend.modules.slack_sdk_module._get_slack_client", return_value=mock_client):
        # Reset channel cache between tests
        import backend.modules.slack_sdk_module as slack_mod
        slack_mod._channel_cache.clear()
        yield mock_client


# ─── send_message ────────────────────────────────────────────────────

class TestSendMessage:
    def test_sends_to_channel_by_name(self, mock_slack_client):
        from backend.modules.slack_sdk_module import send_message

        # Mock channel resolution
        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C12345"}]
        }
        mock_slack_client.chat_postMessage.return_value = {"ok": True}

        result = send_message("general", "Hello everyone!")
        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel="C12345",
            text="Hello everyone!",
        )
        assert "#general" in result
        assert "Hello everyone!" in result

    def test_sends_to_channel_by_id_directly(self, mock_slack_client):
        from backend.modules.slack_sdk_module import send_message

        mock_slack_client.chat_postMessage.return_value = {"ok": True}
        result = send_message("C99ABCDEF", "Direct by ID")

        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel="C99ABCDEF",
            text="Direct by ID",
        )
        assert "Direct by ID" in result

    def test_returns_error_when_channel_not_found(self, mock_slack_client):
        from backend.modules.slack_sdk_module import send_message

        mock_slack_client.conversations_list.return_value = {"channels": []}
        result = send_message("nonexistent-channel", "hello")
        assert "Could not find" in result or "not found" in result.lower()

    def test_returns_error_on_slack_api_failure(self, mock_slack_client):
        from backend.modules.slack_sdk_module import send_message

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "dev", "id": "C111"}]
        }
        mock_slack_client.chat_postMessage.return_value = {
            "ok": False,
            "error": "not_in_channel",
        }
        result = send_message("dev", "test message")
        assert "failed" in result.lower() or "not_in_channel" in result

    def test_strips_leading_hash(self, mock_slack_client):
        from backend.modules.slack_sdk_module import send_message

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C12345"}]
        }
        mock_slack_client.chat_postMessage.return_value = {"ok": True}
        send_message("#general", "hi")

        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel="C12345",
            text="hi",
        )

    def test_error_when_not_connected(self, monkeypatch):
        monkeypatch.setattr("backend.core.oauth_manager.is_connected", lambda s: False)
        from backend.modules.slack_sdk_module import send_message
        result = send_message("general", "hi")
        # Result is "not connected" (oauth check) or "not installed" (import check)
        assert any(phrase in result.lower() for phrase in ["not connected", "connect", "not installed"])


# ─── list_channels ───────────────────────────────────────────────────

class TestListChannels:
    def test_lists_channels(self, mock_slack_client):
        from backend.modules.slack_sdk_module import list_channels

        mock_slack_client.conversations_list.return_value = {
            "channels": [
                {"name": "general", "id": "C1"},
                {"name": "dev-team", "id": "C2"},
                {"name": "random", "id": "C3"},
            ]
        }
        result = list_channels()
        assert "#general" in result
        assert "#dev-team" in result
        assert "#random" in result

    def test_returns_no_channels_message(self, mock_slack_client):
        from backend.modules.slack_sdk_module import list_channels

        mock_slack_client.conversations_list.return_value = {"channels": []}
        result = list_channels()
        assert "No" in result or "no" in result.lower()

    def test_shows_total_count_when_many(self, mock_slack_client):
        from backend.modules.slack_sdk_module import list_channels

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": f"ch{i}", "id": f"C{i}"} for i in range(15)]
        }
        result = list_channels()
        assert "15" in result


# ─── get_recent_messages ─────────────────────────────────────────────

class TestGetRecentMessages:
    def _make_message(self, user: str, text: str) -> dict:
        return {"user": user, "text": text, "ts": "1234567890.000001"}

    def test_reads_recent_messages(self, mock_slack_client):
        from backend.modules.slack_sdk_module import get_recent_messages

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C12345"}]
        }
        mock_slack_client.conversations_history.return_value = {
            "messages": [
                self._make_message("U001", "Hello team!"),
                self._make_message("U002", "Ready for standup?"),
            ]
        }
        mock_slack_client.users_info.return_value = {
            "user": {"profile": {"display_name": "Alice"}, "real_name": "Alice Smith"}
        }

        result = get_recent_messages("general", n=2)
        assert "Alice" in result
        assert "Hello team!" in result

    def test_returns_no_messages_when_channel_empty(self, mock_slack_client):
        from backend.modules.slack_sdk_module import get_recent_messages

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "quiet", "id": "C999"}]
        }
        mock_slack_client.conversations_history.return_value = {"messages": []}
        result = get_recent_messages("quiet")
        assert "No recent messages" in result or "no" in result.lower()

    def test_clamps_n_to_10(self, mock_slack_client):
        from backend.modules.slack_sdk_module import get_recent_messages

        mock_slack_client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C12345"}]
        }
        mock_slack_client.conversations_history.return_value = {"messages": []}
        get_recent_messages("general", n=100)
        call_kwargs = mock_slack_client.conversations_history.call_args
        assert call_kwargs[1]["limit"] <= 10

    def test_returns_error_when_channel_not_found(self, mock_slack_client):
        from backend.modules.slack_sdk_module import get_recent_messages

        mock_slack_client.conversations_list.return_value = {"channels": []}
        result = get_recent_messages("no-such-channel")
        assert "Could not find" in result or "not found" in result.lower()
