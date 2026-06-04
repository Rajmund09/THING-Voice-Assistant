"""
test_oauth_manager.py — Phase 4A Tests
Unit tests for oauth_manager.py: encryption, token storage, and OAuth flow logic.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate_token_file(tmp_path, monkeypatch):
    """Redirect TOKEN_FILE to a temp path so tests don't write to real storage."""
    import backend.core.oauth_manager as om
    monkeypatch.setattr(om, "TOKEN_FILE", tmp_path / "oauth_tokens.json")
    yield


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch):
    """Use a fixed Fernet key so encryption is deterministic in tests."""
    from cryptography.fernet import Fernet
    import backend.core.oauth_manager as om
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", key)
    # Reset the module-level Fernet cache so this new key takes effect
    om._fernet_instance = None
    yield
    # Clean up after test
    om._fernet_instance = None


# ─── Encryption round-trip ────────────────────────────────────────────

class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from backend.core.oauth_manager import _encrypt, _decrypt
        original = '{"access_token": "abc123", "expires_at": 9999999999}'
        encrypted = _encrypt(original)
        assert encrypted != original  # must be transformed
        assert _decrypt(encrypted) == original

    def test_different_ciphertexts_same_plaintext(self):
        """Fernet generates different ciphertexts for same input (IV randomness)."""
        from backend.core.oauth_manager import _encrypt
        p = "hello"
        assert _encrypt(p) != _encrypt(p)  # different nonces

    def test_decrypt_plaintext_fallback(self, monkeypatch):
        """If Fernet fails on the data, it returns the raw string (plaintext legacy)."""
        from backend.core.oauth_manager import _decrypt
        result = _decrypt("not-encrypted-at-all")
        # Should not raise; returns the raw string
        assert isinstance(result, str)


# ─── Token storage ────────────────────────────────────────────────────

class TestTokenStorage:
    def test_store_and_retrieve_token(self):
        from backend.core.oauth_manager import _store_service_tokens, _get_service_tokens
        token_data = {"access_token": "tok_abc", "expires_at": time.time() + 3600}
        _store_service_tokens("spotify", token_data)
        retrieved = _get_service_tokens("spotify")
        assert retrieved is not None
        assert retrieved["access_token"] == "tok_abc"

    def test_retrieve_nonexistent_service(self):
        from backend.core.oauth_manager import _get_service_tokens
        result = _get_service_tokens("notion")
        assert result is None

    def test_delete_service_tokens(self):
        from backend.core.oauth_manager import _store_service_tokens, _delete_service_tokens, _get_service_tokens
        _store_service_tokens("slack", {"access_token": "tok_slack", "expires_at": time.time() + 3600})
        _delete_service_tokens("slack")
        assert _get_service_tokens("slack") is None

    def test_multiple_services_isolated(self):
        from backend.core.oauth_manager import _store_service_tokens, _get_service_tokens
        _store_service_tokens("google", {"access_token": "g_tok", "expires_at": time.time() + 3600})
        _store_service_tokens("spotify", {"access_token": "s_tok", "expires_at": time.time() + 3600})
        assert _get_service_tokens("google")["access_token"] == "g_tok"
        assert _get_service_tokens("spotify")["access_token"] == "s_tok"


# ─── get_token ────────────────────────────────────────────────────────

class TestGetToken:
    def test_returns_valid_token(self):
        from backend.core.oauth_manager import _store_service_tokens, get_token
        _store_service_tokens("google", {
            "access_token": "valid_tok",
            "expires_at": time.time() + 3600,
        })
        assert get_token("google") == "valid_tok"

    def test_returns_none_when_not_connected(self):
        from backend.core.oauth_manager import get_token
        assert get_token("microsoft") is None

    def test_auto_refresh_when_expired(self, monkeypatch):
        from backend.core import oauth_manager as om
        expired_data = {
            "access_token": "old_tok",
            "refresh_token": "refresh_xyz",
            "expires_at": time.time() - 100,  # expired
        }
        om._store_service_tokens("spotify", expired_data)

        refreshed_data = {
            "access_token": "new_tok",
            "refresh_token": "refresh_xyz",
            "expires_at": time.time() + 3600,
        }
        monkeypatch.setattr(om, "_refresh_token", lambda svc, data: refreshed_data)

        token = om.get_token("spotify")
        assert token == "new_tok"

    def test_returns_none_when_refresh_fails(self, monkeypatch):
        from backend.core import oauth_manager as om
        expired_data = {
            "access_token": "old_tok",
            "refresh_token": "bad_refresh",
            "expires_at": time.time() - 100,
        }
        om._store_service_tokens("slack", expired_data)
        monkeypatch.setattr(om, "_refresh_token", lambda svc, data: None)

        assert om.get_token("slack") is None


# ─── is_connected / get_all_statuses ──────────────────────────────────

class TestConnectionStatus:
    def test_is_connected_true_when_valid_token(self, monkeypatch):
        from backend.core import oauth_manager as om
        monkeypatch.setattr(om, "get_token", lambda svc: "tok" if svc == "google" else None)
        assert om.is_connected("google") is True
        assert om.is_connected("spotify") is False

    def test_get_all_statuses_shape(self, monkeypatch):
        from backend.core import oauth_manager as om
        monkeypatch.setattr(om, "get_token", lambda svc: "tok" if svc == "spotify" else None)
        statuses = om.get_all_statuses()
        assert isinstance(statuses, dict)
        assert "google" in statuses
        assert "spotify" in statuses
        assert statuses["spotify"] is True
        assert statuses["google"] is False


# ─── get_auth_url ─────────────────────────────────────────────────────

class TestGetAuthUrl:
    def test_returns_url_when_configured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
        from backend.core.oauth_manager import get_auth_url
        url = get_auth_url("google")
        assert url is not None
        assert "accounts.google.com" in url
        assert "test_client_id" in url
        assert "calendar" in url  # scope

    def test_returns_none_for_missing_client_id(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        from backend.core.oauth_manager import get_auth_url
        url = get_auth_url("google")
        assert url is None

    def test_returns_none_for_unknown_service(self):
        from backend.core.oauth_manager import get_auth_url
        assert get_auth_url("twitter") is None

    def test_sets_pending_service(self, monkeypatch):
        monkeypatch.setenv("SPOTIFY_CLIENT_ID", "sp_client")
        import backend.core.oauth_manager as om
        om._pending_service = None
        om.get_auth_url("spotify")
        assert om._pending_service == "spotify"


# ─── handle_callback ──────────────────────────────────────────────────

class TestHandleCallback:
    def test_successful_token_exchange(self, monkeypatch):
        import backend.core.oauth_manager as om
        om._pending_service = "google"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "google_access_tok",
            "refresh_token": "google_refresh",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response):
            monkeypatch.setenv("GOOGLE_CLIENT_ID", "gid")
            monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gsec")
            result = om.handle_callback("auth_code_xyz")

        assert result is True
        assert om._pending_service is None
        token_data = om._get_service_tokens("google")
        assert token_data["access_token"] == "google_access_tok"

    def test_returns_false_on_http_error(self, monkeypatch):
        import backend.core.oauth_manager as om
        om._pending_service = "spotify"

        with patch("httpx.post", side_effect=Exception("network error")):
            monkeypatch.setenv("SPOTIFY_CLIENT_ID", "sid")
            monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "ssec")
            result = om.handle_callback("bad_code")

        assert result is False

    def test_returns_false_when_no_pending_service(self):
        import backend.core.oauth_manager as om
        om._pending_service = None
        result = om.handle_callback("some_code")
        assert result is False
