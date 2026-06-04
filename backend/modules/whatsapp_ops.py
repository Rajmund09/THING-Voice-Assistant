"""
whatsapp_ops.py — THING v4.1
Full Playwright-based WhatsApp Web automation.

Connection strategy (priority order):
1. Try to attach to an existing Chrome/Chromium already running with
   --remote-debugging-port=9222 (the ideal setup).
2. Try to launch Chromium using the user's REAL default Chrome profile
   so WhatsApp Web login is preserved across runs.
3. Fall back to launching a fresh headless-false Chromium (guest, no login —
   user will need to scan QR code once).

To get the best experience (WhatsApp already logged in), start Chrome once with:
   chrome.exe --remote-debugging-port=9222 --profile-directory=Default
"""

import os
import time
from backend.engine.entity_resolver import resolve_contact


# Path to Chrome's real user data dir (auto-detected or overrideable via .env)
_CHROME_USER_DATA = os.getenv(
    "CHROME_USER_DATA_DIR",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
)
_CHROME_PROFILE = os.getenv("CHROME_PROFILE_DIR", "Default")


def send_whatsapp(contact_name: str, message: str) -> str:
    """
    Sends a WhatsApp message via WhatsApp Web using Playwright.

    Connection tries (in order):
    1. Existing Chrome on port 9222 (already running)
    2. Launch Chrome with real user profile (login preserved)
    3. Launch Chromium fresh (will need QR scan)
    """
    if not contact_name:
        return "No contact specified."
    if not message:
        return "No message specified."

    try:
        import sys
        import asyncio
        from playwright.sync_api import sync_playwright

        if sys.platform == "win32":
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

        with sync_playwright() as p:
            browser = None
            context = None
            page = None
            launched_new = False

            # ── Strategy 1: Attach to existing Chrome on CDP port ─────────
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]

                # Find existing WhatsApp tab
                for pg in context.pages:
                    if "web.whatsapp.com" in pg.url:
                        page = pg
                        break

                if not page:
                    # Open WhatsApp in a new tab in the EXISTING window
                    page = context.new_page()
                    page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=30000)
                    time.sleep(3)

            except Exception:
                browser = None

            # ── Strategy 2: Launch Chrome with real user profile ───────────
            if browser is None:
                try:
                    # Find Chrome executable
                    chrome_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    ]
                    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

                    if chrome_exe and os.path.isdir(_CHROME_USER_DATA):
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=_CHROME_USER_DATA,
                            executable_path=chrome_exe,
                            channel="chrome",
                            headless=False,
                            args=[
                                f"--profile-directory={_CHROME_PROFILE}",
                                "--no-first-run",
                                "--disable-blink-features=AutomationControlled",
                            ],
                        )
                        # launch_persistent_context returns a BrowserContext directly
                        context = browser

                        # Find or open WhatsApp tab
                        for pg in context.pages:
                            if "web.whatsapp.com" in pg.url:
                                page = pg
                                break

                        if not page:
                            page = context.new_page()
                            page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=30000)
                            time.sleep(3)

                        launched_new = True
                    else:
                        raise RuntimeError("Chrome exe or user data not found")

                except Exception:
                    browser = None
                    context = None

            # ── Strategy 3: Fresh Chromium (fallback, no login) ───────────
            if browser is None:
                raw_browser = p.chromium.launch(headless=False)
                context = raw_browser.new_context()
                page = context.new_page()
                page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=30000)
                time.sleep(4)
                launched_new = True

            # ── Send the message ───────────────────────────────────────────
            page.bring_to_front()

            # Search for the contact
            search_box = page.wait_for_selector(
                'div[contenteditable="true"][data-tab="3"]',
                timeout=15000,
            )
            search_box.click()
            search_box.fill("")
            search_box.type(contact_name, delay=50)
            time.sleep(1.5)

            # Click matching contact
            try:
                contact_el = page.wait_for_selector(
                    f'span[title="{contact_name}"]',
                    timeout=6000,
                )
                contact_el.click()
            except Exception:
                first_result = page.query_selector('div[role="listitem"]')
                if first_result:
                    first_result.click()
                else:
                    return f"Couldn't find '{contact_name}' on WhatsApp Web. Make sure you are logged in."

            time.sleep(0.8)

            # Type and send
            msg_box = page.wait_for_selector(
                'div[contenteditable="true"][data-tab="10"]',
                timeout=5000,
            )
            msg_box.click()
            msg_box.type(message, delay=30)
            time.sleep(0.3)
            msg_box.press("Enter")
            time.sleep(0.5)

            return f"Message sent to {contact_name}."

    except ImportError:
        return "Playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        print(f"[WhatsApp] Error: {repr(e)}")
        return (
            f"Couldn't send message to {contact_name}. "
            "Make sure WhatsApp Web is open and you are logged in. "
            "Tip: Start Chrome with --remote-debugging-port=9222 for best results."
        )
