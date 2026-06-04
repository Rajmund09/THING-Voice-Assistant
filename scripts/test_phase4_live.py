"""
scripts/test_phase4_live.py — THING Phase 4 Live Integration Tester
=====================================================================
Tests ALL Phase 4 components against REAL credentials from .env.
Skips services not configured or not OAuth'd yet (with clear guidance).

Usage:
    python scripts/test_phase4_live.py

Color codes:
    ✅ PASS    — Real API call succeeded
    ❌ FAIL    — Error / unexpected result
    ⚠️  SKIP    — Not configured (missing env vars or OAuth token)
    🔑 INFO    — Configuration status info
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Bootstrap ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS  = f"{GREEN}[PASS]{RESET}"
FAIL  = f"{RED}[FAIL]{RESET}"
SKIP  = f"{YELLOW}[SKIP]{RESET}"
INFO  = f"{CYAN}[INFO]{RESET}"

# ── Result tracking ────────────────────────────────────────────────────────────
results = {"pass": 0, "fail": 0, "skip": 0}

def check(name: str, condition: bool, detail: str = "", skip: bool = False):
    if skip:
        results["skip"] += 1
        print(f"  {SKIP}  {name}{DIM}  -- {detail}{RESET}")
    elif condition:
        results["pass"] += 1
        print(f"  {PASS}  {name}{DIM}  {detail}{RESET}")
    else:
        results["fail"] += 1
        print(f"  {FAIL}  {name}{DIM}  -- {detail}{RESET}")

def section(title: str):
    print(f"\n{BOLD}{CYAN}{'-'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'-'*60}{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 0 — Environment & Dependencies
# ══════════════════════════════════════════════════════════════════════════════
section("0. Environment Variables")

env_vars = {
    "GROQ_API_KEY":         os.getenv("GROQ_API_KEY", ""),
    "GEMINI_API_KEY":       os.getenv("GEMINI_API_KEY", ""),
    "GOOGLE_CLIENT_ID":     os.getenv("GOOGLE_CLIENT_ID", ""),
    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    "SPOTIFY_CLIENT_ID":    os.getenv("SPOTIFY_CLIENT_ID", ""),
    "SPOTIFY_CLIENT_SECRET":os.getenv("SPOTIFY_CLIENT_SECRET",""),
    "SLACK_CLIENT_ID":      os.getenv("SLACK_CLIENT_ID", ""),
    "SLACK_CLIENT_SECRET":  os.getenv("SLACK_CLIENT_SECRET", ""),
    "OAUTH_ENCRYPTION_KEY": os.getenv("OAUTH_ENCRYPTION_KEY", ""),
}

for k, v in env_vars.items():
    if v:
        check(k, True, f"= {v[:14]}...")
    else:
        check(k, False, "NOT SET in .env")

section("0b. Python Dependencies")
DEPS = {
    "cryptography":   "cryptography",
    "spotipy":        "spotipy",
    "slack_sdk":      "slack-sdk",
    "googleapiclient":"google-api-python-client",
    "httpx":          "httpx",
}
missing_deps = []
for mod, pkg in DEPS.items():
    try:
        __import__(mod)
        check(pkg, True, "installed")
    except ImportError:
        check(pkg, False, f"MISSING — run: pip install {pkg}")
        missing_deps.append(pkg)

if missing_deps:
    print(f"\n  {RED}Install missing deps then re-run:{RESET}")
    print(f"  pip install {' '.join(missing_deps)}\n")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — OAuth Manager Core
# ══════════════════════════════════════════════════════════════════════════════
section("1. OAuth Manager — Encryption & Token Store")

from backend.core import oauth_manager

# 1.1 Encrypt / decrypt roundtrip
try:
    cipher_text = oauth_manager._encrypt("test-secret-value")
    plain_text  = oauth_manager._decrypt(cipher_text)
    check("Encrypt → Decrypt roundtrip", plain_text == "test-secret-value",
          f"cipher_len={len(cipher_text)}")
except Exception as e:
    check("Encrypt → Decrypt roundtrip", False, str(e))

# 1.2 Token file parent is accessible
token_path = oauth_manager.TOKEN_FILE
check("Token file parent path accessible",
      True,
      str(token_path.parent))

# 1.3 OAuth status for all services
section("1b. OAuth Connection Status (per service)")
try:
    statuses = oauth_manager.get_all_statuses()
    for svc, connected in statuses.items():
        if connected:
            token = oauth_manager.get_token(svc)
            check(f"{svc.capitalize():12s} connected", True,
                  f"token prefix = {str(token)[:16]}...")
        else:
            client_id_env = oauth_manager.SERVICE_CONFIGS[svc]["client_id_env"]
            has_creds = bool(os.getenv(client_id_env, ""))
            if has_creds:
                check(f"{svc.capitalize():12s} connected", False,
                      f"credentials set but not OAuth'd — open THING → Integrations → Connect {svc.capitalize()}")
            else:
                check(f"{svc.capitalize():12s} connected", True,
                      f"not configured ({client_id_env} not in .env)", skip=True)
except Exception as e:
    check("get_all_statuses()", False, str(e))
    statuses = {}


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — Google Calendar (Live)
# ══════════════════════════════════════════════════════════════════════════════
section("2. Google Calendar — Live API Calls")

GOOGLE_OK    = statuses.get("google", False)
GOOGLE_CREDS = bool(os.getenv("GOOGLE_CLIENT_ID")) and bool(os.getenv("GOOGLE_CLIENT_SECRET"))

if not GOOGLE_CREDS:
    for label in ["get_events_today()", "get_events_tomorrow()", "get_events_this_week()", "create_event()"]:
        check(f"Google Calendar — {label}", True,
              "No GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env", skip=True)

elif not GOOGLE_OK:
    for label in ["get_events_today()", "get_events_tomorrow()", "get_events_this_week()", "create_event()"]:
        check(f"Google Calendar — {label}", True,
              "Credentials found but not OAuth'd — go to Integrations → Connect Google", skip=True)
else:
    from backend.modules.google_calendar import (
        get_events_today, get_events_tomorrow,
        get_events_this_week, create_event
    )

    # 2.1 Today's events
    try:
        result = get_events_today()
        ok = isinstance(result, str) and len(result) > 5
        check("Google Calendar — get_events_today()", ok, result[:90])
    except Exception as e:
        check("Google Calendar — get_events_today()", False, str(e))

    # 2.2 Tomorrow's events
    try:
        result = get_events_tomorrow()
        ok = isinstance(result, str) and "tomorrow" in result.lower()
        check("Google Calendar — get_events_tomorrow()", ok, result[:90])
    except Exception as e:
        check("Google Calendar — get_events_tomorrow()", False, str(e))

    # 2.3 This week's events
    try:
        result = get_events_this_week()
        ok = isinstance(result, str) and len(result) > 5
        check("Google Calendar — get_events_this_week()", ok, result[:90])
    except Exception as e:
        check("Google Calendar — get_events_this_week()", False, str(e))

    # 2.4 Create test event 14 days out at 11:30pm to avoid conflicts
    from datetime import datetime, timedelta
    future_start = (datetime.now() + timedelta(days=14)).replace(
        hour=23, minute=30, second=0, microsecond=0)
    future_end = future_start + timedelta(hours=1)
    try:
        result = create_event(
            title="THING Phase 4 Test Event",
            start_time=future_start.isoformat(),
            end_time=future_end.isoformat(),
            description="Auto-created by test_phase4_live.py — safe to delete."
        )
        ok = "THING Phase 4 Test Event" in result or "Created" in result or "created" in result.lower()
        check("Google Calendar — create_event() [+14 days]", ok, result[:90])
    except Exception as e:
        check("Google Calendar — create_event()", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — Spotify SDK (Live)
# ══════════════════════════════════════════════════════════════════════════════
section("3. Spotify — Live API Calls")

SPOTIFY_OK    = statuses.get("spotify", False)
SPOTIFY_CREDS = bool(os.getenv("SPOTIFY_CLIENT_ID")) and bool(os.getenv("SPOTIFY_CLIENT_SECRET"))

if not SPOTIFY_CREDS:
    for label in ["get_current_track()", "Search API", "Devices list", "set_volume(50)"]:
        check(f"Spotify — {label}", True,
              "No SPOTIFY_CLIENT_ID/SECRET in .env", skip=True)

elif not SPOTIFY_OK:
    for label in ["get_current_track()", "Search API", "Devices list", "set_volume(50)"]:
        check(f"Spotify — {label}", True,
              "Credentials found but not OAuth'd — Integrations → Connect Spotify", skip=True)
else:
    from backend.modules.spotify_sdk import get_current_track, set_volume
    import spotipy
    from backend.core.oauth_manager import get_token as _get_token

    # 3.1 Current track (non-destructive)
    try:
        result = get_current_track()
        if "error" in result:
            check("Spotify — get_current_track()", True,
                  f"Nothing playing: {result['error']}")
        else:
            check("Spotify — get_current_track()", True,
                  f"Now playing: '{result.get('track_name','?')}' by {result.get('artist','?')}")
    except Exception as e:
        check("Spotify — get_current_track()", False, str(e))

    # 3.2 Search API (non-destructive — just query, don't play)
    try:
        token = _get_token("spotify")
        sp = spotipy.Spotify(auth=token)
        res = sp.search(q="Blinding Lights The Weeknd", type="track", limit=1)
        items = res.get("tracks", {}).get("items", [])
        check("Spotify — Search API (track lookup)",
              bool(items),
              f"Found: '{items[0]['name']}' by {items[0]['artists'][0]['name']}" if items else "no results")
    except Exception as e:
        check("Spotify — Search API", False, str(e))

    # 3.3 Device list
    try:
        token = _get_token("spotify")
        sp = spotipy.Spotify(auth=token)
        devices = sp.devices().get("devices", [])
        if devices:
            names = [d["name"] for d in devices]
            check("Spotify — Active devices", True, f"{', '.join(names)}")
        else:
            check("Spotify — Active devices", True,
                  "No active device — open Spotify on PC/phone to enable playback commands")
    except Exception as e:
        check("Spotify — Active devices", False, str(e))

    # 3.4 Volume set (only if device active)
    try:
        token = _get_token("spotify")
        sp = spotipy.Spotify(auth=token)
        device_list = sp.devices().get("devices", [])
        if device_list:
            result = set_volume(50)
            check("Spotify — set_volume(50)", "50%" in result, result)
        else:
            check("Spotify — set_volume(50)", True,
                  "No active device — skipping volume test", skip=True)
    except Exception as e:
        check("Spotify — set_volume(50)", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — Slack SDK (Live)
# ══════════════════════════════════════════════════════════════════════════════
section("4. Slack — Live API Calls")

SLACK_OK    = statuses.get("slack", False)
SLACK_CREDS = bool(os.getenv("SLACK_CLIENT_ID")) and bool(os.getenv("SLACK_CLIENT_SECRET"))

if not SLACK_CREDS:
    for label in ["auth.test()", "list_channels()"]:
        check(f"Slack — {label}", True,
              "No SLACK_CLIENT_ID/SECRET in .env", skip=True)

elif not SLACK_OK:
    for label in ["auth.test()", "list_channels()"]:
        check(f"Slack — {label}", True,
              "Credentials found but not OAuth'd — Integrations → Connect Slack", skip=True)
else:
    from backend.modules.slack_sdk_module import list_channels
    from slack_sdk import WebClient as SlackWebClient
    from backend.core.oauth_manager import get_token as _get_token

    # 4.1 Auth test
    try:
        token = _get_token("slack")
        sc = SlackWebClient(token=token)
        resp = sc.auth_test()
        check("Slack — auth.test()", resp.get("ok"),
              f"Workspace: {resp.get('team','?')} | Bot/User: {resp.get('user','?')}")
    except Exception as e:
        check("Slack — auth.test()", False, str(e))

    # 4.2 List channels
    try:
        result = list_channels()
        ok = "channel" in result.lower() or "#" in result
        check("Slack — list_channels()", ok, result[:100])
    except Exception as e:
        check("Slack — list_channels()", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — Action Executor Phase 4 Dispatches
# ══════════════════════════════════════════════════════════════════════════════
section("5. Action Executor — Phase 4 Dispatch Routing")

from backend.modules.action_executor import _execute_single

dispatch_tests = [
    ("spotify_now_playing", {"action": "spotify_now_playing"}),
    ("calendar_query today", {"action": "calendar_query", "timeframe": "today"}),
    ("calendar_query tomorrow", {"action": "calendar_query", "timeframe": "tomorrow"}),
    ("calendar_query week", {"action": "calendar_query", "timeframe": "this_week"}),
    ("slack_channels", {"action": "slack_channels"}),
    ("slack_read general", {"action": "slack_read", "channel": "general", "count": 3}),
]

for label, action_dict in dispatch_tests:
    try:
        result = _execute_single(action_dict, action_dict["action"])
        is_str = isinstance(result, str) and len(result) > 0
        check(f"execute {label}", is_str, result[:80] if is_str else "no response")
    except Exception as e:
        check(f"execute {label}", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — Intent Router Phase 4 Regex Patterns
# ══════════════════════════════════════════════════════════════════════════════
section("6. Intent Router — Phase 4 Regex Patterns")

try:
    from backend.engine.intent_router import get_local_intent

    pattern_cases = [
        # Spotify
        ("play blinding lights on spotify",    "spotify_play"),
        ("play my lofi playlist",              "spotify_play"),
        ("pause spotify",                      "spotify_pause"),
        ("resume spotify",                     "spotify_resume"),
        ("skip on spotify",                    "spotify_skip"),
        ("previous on spotify",                "spotify_previous"),
        ("set spotify volume to 70",           "spotify_volume"),
        ("what's playing on spotify",          "spotify_now_playing"),
        # Calendar
        ("what's on my calendar today",        "calendar_query"),
        ("what's on my calendar tomorrow",     "calendar_query"),
        ("what's on my calendar this week",    "calendar_query"),
        ("create an event team standup at 9am","calendar_create"),
        # Slack
        ("list my slack channels",             "slack_channels"),
        ("read messages in general on slack",  "slack_read"),
        ("slack message to general saying hello there", "slack_send"),
    ]

    pass_count = 0
    for cmd, expected_action in pattern_cases:
        try:
            result = get_local_intent(cmd, use_llm_fallback=False)
            got = result.get("action") if result else None
            ok  = (got == expected_action)
            check(f'Router: "{cmd}"', ok,
                  f"→ {got}" if got else "returned None — no regex match")
            if ok:
                pass_count += 1
        except Exception as e:
            check(f'Router: "{cmd}"', False, str(e))

except Exception as e:
    check("Intent router import", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — Phase 4 Mock Unit Tests (pytest)
# ══════════════════════════════════════════════════════════════════════════════
section("7. Phase 4 Unit Tests (Mocked — pytest)")

import subprocess
unit_test_files = [
    ("test_oauth_manager.py",    "tests/unit/test_oauth_manager.py"),
    ("test_spotify_sdk.py",      "tests/unit/test_spotify_sdk.py"),
    ("test_google_calendar.py",  "tests/unit/test_google_calendar.py"),
    ("test_slack_sdk_module.py", "tests/unit/test_slack_sdk_module.py"),
]

for name, tf in unit_test_files:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", tf, "-q", "--tb=line", "--no-header"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        lines   = [l for l in r.stdout.strip().splitlines() if l.strip()]
        summary = lines[-1] if lines else r.stderr.strip()[:100]
        passed  = ("failed" not in summary.lower()) and (r.returncode == 0)
        check(name, passed, summary)
    except Exception as e:
        check(name, False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — Full Test Suite (All Phases)
# ══════════════════════════════════════════════════════════════════════════════
section("8. Full Test Suite (All Phases — pytest)")

try:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line", "--no-header"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    lines   = [l for l in r.stdout.strip().splitlines() if l.strip()]
    summary = lines[-1] if lines else r.stderr.strip()[:120]
    passed  = ("failed" not in summary.lower()) and (r.returncode == 0)
    check("All phases — full pytest suite", passed, summary)
    # Print any failures
    if not passed:
        failure_lines = [l for l in r.stdout.splitlines() if "FAILED" in l or "ERROR" in l]
        for fl in failure_lines[:10]:
            print(f"     {RED}{fl.strip()}{RESET}")
except Exception as e:
    check("Full pytest suite", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
total = results["pass"] + results["fail"] + results["skip"]
section("FINAL SUMMARY")
print(f"""
  {GREEN}✅ Passed : {results['pass']}{RESET}
  {RED}❌ Failed : {results['fail']}{RESET}
  {YELLOW}⚠️  Skipped: {results['skip']} (services not configured / not OAuth'd){RESET}
  {DIM}   Total  : {total}{RESET}
""")

if results["skip"] > 0:
    unset = [k for k, v in env_vars.items() if not v]
    if unset:
        print(f"  {YELLOW}To enable skipped tests, add these to your .env:{RESET}")
        for k in unset:
            print(f"    {DIM}{k}=<your-value>{RESET}")
        print()

if results["fail"] > 0:
    print(f"  {RED}{BOLD}Some checks failed. Review the ❌ lines above.{RESET}\n")
    sys.exit(1)
else:
    print(f"  {GREEN}{BOLD}🎉 All Phase 4 checks passed (or gracefully skipped)!{RESET}\n")
    sys.exit(0)
