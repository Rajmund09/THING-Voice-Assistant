import subprocess
from playwright.sync_api import sync_playwright

class BrowserController:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def _ensure_browser(self):
        if sys.platform == 'win32':
            import asyncio
            import sys
            # Force Proactor event loop for subprocess support on Windows
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

        try:
            if not self.playwright:
                self.playwright = sync_playwright().start()
            if not self.browser:
                # Using chromium in non-headless mode for assistant visibility
                self.browser = self.playwright.chromium.launch(headless=False)
                self.context = self.browser.new_context()
            if not self.page or self.page.is_closed():
                self.page = self.context.new_page()
        except Exception as e:
            err_msg = repr(e)
            print(f"[Browser] Error: {err_msg}")
            if "Executable doesn't exist" in err_msg:
                print("[Browser] CRITICAL: Chromium not found. Run: playwright install chromium")
            raise e

    def open_url(self, url: str) -> str:
        self._ensure_browser()
        if not url.startswith("http"):
            url = f"https://{url}"
        self.page.goto(url)
        return f"Opened {url}"

    def scroll(self, direction: str, amount: int = 500) -> str:
        self._ensure_browser()
        if direction == "down":
            self.page.mouse.wheel(0, amount)
        elif direction == "up":
            self.page.mouse.wheel(0, -amount)
        return f"Scrolled {direction}"
        
    def click_element(self, text: str) -> str:
        self._ensure_browser()
        try:
            self.page.get_by_text(text).first.click()
            return f"Clicked {text}"
        except:
            return f"Could not find {text} to click."
            
    def type_text(self, selector: str, text: str, press_enter: bool = True) -> str:
        self._ensure_browser()
        try:
            self.page.fill(selector, text)
            if press_enter:
                self.page.press(selector, "Enter")
            return f"Typed in {selector}"
        except:
            return "Failed to type."

    def close(self):
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        return "Browser closed."

browser_controller = BrowserController()
