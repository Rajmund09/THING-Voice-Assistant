"""
oauth_manager.py — THING Phase 4A
Manages OAuth 2.0 flows for Google, Spotify, Slack, Microsoft, and Notion.

Responsibilities:
  - Generate authorization URLs and start a loopback callback server
  - Exchange authorization codes for access + refresh tokens
  - Store tokens encrypted (Fernet) in backend/data/oauth_tokens.json
  - Auto-refresh expired tokens before API calls
  - Provide get_token(service) interface for all service modules
"""

import os
import json
import time
import base64
import logging
import threading
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Token file path ────────────────────────────────────────────────
TOKEN_FILE = Path(__file__).parent.parent / "data" / "oauth_tokens.json"

# ─── Service configurations ─────────────────────────────────────────
SERVICE_CONFIGS = {
    "google": {
        "auth_url":    "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url":   "https://oauth2.googleapis.com/token",
        "scope":       "https://www.googleapis.com/auth/calendar.readonly "
                       "https://www.googleapis.com/auth/calendar.events",
        "client_id_env":     "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
    },
    "spotify": {
        "auth_url":    "https://accounts.spotify.com/authorize",
        "token_url":   "https://accounts.spotify.com/api/token",
        "scope":       "user-read-playback-state user-modify-playback-state "
                       "user-read-currently-playing playlist-read-private",
        "client_id_env":     "SPOTIFY_CLIENT_ID",
        "client_secret_env": "SPOTIFY_CLIENT_SECRET",
    },
    "slack": {
        "auth_url":    "https://slack.com/oauth/v2/authorize",
        "token_url":   "https://slack.com/api/oauth.v2.access",
        "scope":       "channels:read,channels:history,chat:write",
        "client_id_env":     "SLACK_CLIENT_ID",
        "client_secret_env": "SLACK_CLIENT_SECRET",
    },
    "microsoft": {
        "auth_url":    "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token_url":   "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "scope":       "Calendars.Read Mail.Read offline_access",
        "client_id_env":     "MICROSOFT_CLIENT_ID",
        "client_secret_env": None,  # MSAL uses client_id only for public clients
    },
    "notion": {
        "auth_url":    "https://api.notion.com/v1/oauth/authorize",
        "token_url":   "https://api.notion.com/v1/oauth/token",
        "scope":       "",
        "client_id_env":     "NOTION_CLIENT_ID",
        "client_secret_env": "NOTION_CLIENT_SECRET",
    },
}

REDIRECT_URI = "http://localhost:5000/oauth/callback"

def get_redirect_uri(service: str) -> str:
    """Return the service-specific redirect URI.
    Spotify requires http://127.0.0.1 while Microsoft and Notion require http://localhost.
    """
    if service == "spotify":
        return "http://127.0.0.1:5000/oauth/callback"
    return REDIRECT_URI

_pending_service: Optional[str] = None  # service currently awaiting callback


# ─── Encryption helpers ─────────────────────────────────────────────

_fernet_instance = None  # cached so encrypt/decrypt use same key in one process

def _get_fernet():
    """Return a Fernet instance using the key from env (auto-generates if missing).
    The instance is cached per-process so encrypt→decrypt roundtrips always work,
    even when OAUTH_ENCRYPTION_KEY is not yet set in .env.
    """
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None  # graceful degradation — store plaintext if lib missing

    key_str = os.getenv("OAUTH_ENCRYPTION_KEY", "")
    if not key_str:
        # Auto-generate and print once — user should save this to .env
        key = Fernet.generate_key()
        key_str = key.decode()
        logger.warning(
            "[OAuth] No OAUTH_ENCRYPTION_KEY set. Generated a temporary key. "
            "Add this to your .env to persist tokens across restarts: %s", key_str
        )
    else:
        key = key_str.encode()

    try:
        _fernet_instance = Fernet(key)
        return _fernet_instance
    except Exception:
        return None


def _encrypt(data: str) -> str:
    f = _get_fernet()
    if f is None:
        return data  # fallback: plaintext
    return f.encrypt(data.encode()).decode()


def _decrypt(data: str) -> str:
    f = _get_fernet()
    if f is None:
        return data  # fallback: plaintext
    try:
        return f.decrypt(data.encode()).decode()
    except Exception:
        return data  # already plaintext (legacy)


# ─── Token storage ──────────────────────────────────────────────────

def _load_tokens() -> Dict[str, Any]:
    if not TOKEN_FILE.exists():
        return {}
    try:
        raw = TOKEN_FILE.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def _save_tokens(tokens: Dict[str, Any]) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _get_service_tokens(service: str) -> Optional[Dict[str, Any]]:
    all_tokens = _load_tokens()
    entry = all_tokens.get(service)
    if not entry:
        return None
    try:
        decrypted = _decrypt(entry["data"])
        return json.loads(decrypted)
    except Exception:
        return None


def _store_service_tokens(service: str, token_data: Dict[str, Any]) -> None:
    all_tokens = _load_tokens()
    payload = json.dumps(token_data)
    all_tokens[service] = {"data": _encrypt(payload), "updated_at": time.time()}
    _save_tokens(all_tokens)
    logger.info("[OAuth] Stored tokens for %s", service)


def _delete_service_tokens(service: str) -> None:
    all_tokens = _load_tokens()
    all_tokens.pop(service, None)
    _save_tokens(all_tokens)
    logger.info("[OAuth] Removed tokens for %s", service)


# ─── Token refresh ──────────────────────────────────────────────────

def _refresh_token(service: str, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Attempt to refresh an expired access token using the refresh token."""
    import httpx

    cfg = SERVICE_CONFIGS.get(service)
    if not cfg:
        return None

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None

    client_id = os.getenv(cfg["client_id_env"], "")
    client_secret_env = cfg.get("client_secret_env")
    client_secret = os.getenv(client_secret_env, "") if client_secret_env else ""

    token_url = cfg["token_url"]
    if "{tenant}" in token_url:
        tenant = os.getenv("MICROSOFT_TENANT_ID", "common")
        token_url = token_url.format(tenant=tenant)

    payload = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    # Slack uses form + basic auth
    headers = {}
    if service == "slack" and client_id and client_secret:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    try:
        resp = httpx.post(token_url, data=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        new_data = resp.json()
        # Merge — keep existing refresh_token if new one not provided
        if "refresh_token" not in new_data and refresh_token:
            new_data["refresh_token"] = refresh_token
        new_data["expires_at"] = time.time() + new_data.get("expires_in", 3600)
        _store_service_tokens(service, new_data)
        logger.info("[OAuth] Refreshed token for %s", service)
        return new_data
    except Exception as exc:
        logger.error("[OAuth] Failed to refresh token for %s: %s", service, exc)
        return None


# ─── Public API ─────────────────────────────────────────────────────

def get_token(service: str) -> Optional[str]:
    """
    Returns a valid access token for the given service.
    Auto-refreshes if expired. Returns None if not connected.

    Args:
        service: One of 'google', 'spotify', 'slack', 'microsoft', 'notion'

    Returns:
        Access token string or None.
    """
    token_data = _get_service_tokens(service)
    if not token_data:
        return None

    # Check expiry (with 60s buffer)
    expires_at = token_data.get("expires_at", 0)
    if time.time() >= expires_at - 60:
        token_data = _refresh_token(service, token_data)
        if not token_data:
            return None

    return token_data.get("access_token")


def is_connected(service: str) -> bool:
    """Returns True if valid tokens exist for the service."""
    return get_token(service) is not None


def get_all_statuses() -> Dict[str, bool]:
    """Returns connection status for all supported services."""
    return {service: is_connected(service) for service in SERVICE_CONFIGS}


def disconnect_service(service: str) -> None:
    """Revokes local tokens for a service. (Full API revocation is service-specific.)"""
    _delete_service_tokens(service)


def get_auth_url(service: str) -> Optional[str]:
    """
    Generates the OAuth authorization URL for the given service.
    Also sets the pending service so the callback knows which service to complete.

    Returns:
        The full authorization URL to open in a browser, or None on error.
    """
    global _pending_service

    cfg = SERVICE_CONFIGS.get(service)
    if not cfg:
        logger.error("[OAuth] Unknown service: %s", service)
        return None

    client_id = os.getenv(cfg["client_id_env"], "")
    if not client_id:
        logger.warning("[OAuth] %s not configured (missing %s)", service, cfg["client_id_env"])
        return None

    auth_url = cfg["auth_url"]
    if "{tenant}" in auth_url:
        tenant = os.getenv("MICROSOFT_TENANT_ID", "common")
        auth_url = auth_url.format(tenant=tenant)

    params = {
        "client_id":     client_id,
        "redirect_uri":  get_redirect_uri(service),
        "response_type": "code",
        "scope":         cfg["scope"],
        "access_type":   "offline",  # Google needs this for refresh_token
        "prompt":        "consent",
    }

    # Slack uses "user_scope" instead of "scope" for user tokens
    if service == "slack":
        params["user_scope"] = params.pop("scope")
        params.pop("access_type", None)
        params.pop("prompt", None)

    # Notion doesn't use scope in the same way
    if service == "notion":
        params.pop("scope", None)
        params["owner"] = "user"

    _pending_service = service
    full_url = auth_url + "?" + urllib.parse.urlencode(params)
    logger.info("[OAuth] Auth URL generated for %s", service)
    return full_url


def handle_callback(code: str, service: Optional[str] = None) -> bool:
    """
    Exchanges an authorization code for tokens and stores them.

    Args:
        code: The authorization code from the OAuth callback.
        service: Override the pending service (optional).

    Returns:
        True on success, False on failure.
    """
    global _pending_service
    import httpx

    target_service = service or _pending_service
    if not target_service:
        logger.error("[OAuth] Callback received but no pending service known.")
        return False

    cfg = SERVICE_CONFIGS.get(target_service)
    if not cfg:
        return False

    client_id = os.getenv(cfg["client_id_env"], "")
    client_secret_env = cfg.get("client_secret_env")
    client_secret = os.getenv(client_secret_env, "") if client_secret_env else ""

    token_url = cfg["token_url"]
    if "{tenant}" in token_url:
        tenant = os.getenv("MICROSOFT_TENANT_ID", "common")
        token_url = token_url.format(tenant=tenant)

    payload = {
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": get_redirect_uri(target_service),
        "client_id":    client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Notion uses HTTP Basic auth for token exchange
    if target_service == "notion" and client_id and client_secret:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    try:
        resp = httpx.post(token_url, data=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        _store_service_tokens(target_service, token_data)
        _pending_service = None
        logger.info("[OAuth] Successfully connected %s", target_service)
        return True
    except Exception as exc:
        logger.error("[OAuth] Token exchange failed for %s: %s", target_service, exc)
        return False


def get_pending_service() -> Optional[str]:
    """Returns the service currently awaiting an OAuth callback."""
    return _pending_service
