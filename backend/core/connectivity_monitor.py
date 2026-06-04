import threading
import time
import urllib.request
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ConnectivityMonitor(threading.Thread):
    def __init__(self, socketio=None, check_interval=15):
        super().__init__(daemon=True)
        self.socketio = socketio
        self.check_interval = check_interval
        self._is_online = True  # Assume online initially
        self._lock = threading.Lock()
        self._last_status: Optional[bool] = None

    def is_online(self) -> bool:
        with self._lock:
            return self._is_online

    def set_socketio(self, socketio):
        self.socketio = socketio
        # Immediately emit current status when socketio is set
        with self._lock:
            current = self._is_online
        self.socketio.emit("connectivity_status", {"online": current})

    def run(self):
        logger.info("[ConnectivityMonitor] Started.")
        while True:
            current_status = self._check_connection()
            
            with self._lock:
                status_changed = (self._last_status is None) or (self._last_status != current_status)
                self._is_online = current_status
                self._last_status = current_status

            if status_changed:
                logger.info("[ConnectivityMonitor] Status changed: %s", "Online" if current_status else "Offline")
                if self.socketio:
                    self.socketio.emit("connectivity_status", {"online": current_status})

            time.sleep(self.check_interval)

    def _check_connection(self) -> bool:
        try:
            urllib.request.urlopen('http://1.1.1.1', timeout=1)
            return True
        except Exception:
            try:
                urllib.request.urlopen('http://8.8.8.8', timeout=1)
                return True
            except Exception:
                return False

# Global instance
monitor = ConnectivityMonitor()
