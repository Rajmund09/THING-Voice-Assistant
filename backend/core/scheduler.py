"""
scheduler.py — THING v5.0
Wrapper for the schedule library to handle time-based proactive events.
"""

import schedule
import time
import threading
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Scheduler:
    def __init__(self, callback):
        self.callback = callback
        self._stop_event = threading.Event()
        self._thread = None
        
        # User configurable settings
        self.eod_hour = int(os.getenv("PROACTIVE_EOD_HOUR", "17"))
        self.enabled = os.getenv("PROACTIVE_ENABLED", "true").lower() == "true"

    def start(self):
        if not self.enabled:
            return
            
        # Schedule daily end-of-day check
        self._job = schedule.every().day.at(f"{self.eod_hour:02d}:00").do(self._run_callback)
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if hasattr(self, '_job') and self._job:
            schedule.cancel_job(self._job)
            self._job = None

    def _run_callback(self):
        # Notify the callback (ContextObserver) that a scheduled event occurred
        self.callback("scheduled_time_check")

    def _run_loop(self):
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(60) # Check every minute
