import sys
import asyncio

# CRITICAL: This must be at the absolute top for Windows Playwright support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.core.server import start_server

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[System] Shutting down THING...")
