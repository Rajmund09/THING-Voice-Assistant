"""
desktop_pet.py — THING AI Desktop Companion
Fully thread-safe PyQt6 desktop pet.
Socket.IO events -> Qt signals -> UI updates on main thread.
"""

import sys
import os
import random
import threading
import socketio

from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

# ── Thread-safe bridge: emits Qt signals from any thread ─────────────────────
class SignalBridge(QObject):
    state_changed = pyqtSignal(str)


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.bridge = SignalBridge()
        self.bridge.state_changed.connect(self._on_state_changed)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("THING Pet")

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_state = ""
        self.movie = None

        # Walking state
        self.target_x = None
        self.walk_speed = 4
        self.facing_right = True   # True = facing right
        self.drag_pos = None

        # Screen bounds
        screen = QApplication.primaryScreen().availableGeometry()
        self.screen_rect = screen

        # ── Timers (all on main thread) ───────────────────────────────────
        # Gravity + walk tick
        self.walk_timer = QTimer(self)
        self.walk_timer.timeout.connect(self._tick)
        self.walk_timer.start(40)   # ~25fps

        # Idle → roam
        self.roam_timer = QTimer(self)
        self.roam_timer.timeout.connect(self._trigger_roam)
        self.roam_timer.start(8000)

        # Temporary-state → idle
        self.revert_timer = QTimer(self)
        self.revert_timer.setSingleShot(True)
        self.revert_timer.timeout.connect(lambda: self._set_state("idle"))

        # ── Initial position: bottom-centre ──────────────────────────────
        pet_w, pet_h = 220, 220
        self.resize(pet_w, pet_h)
        self.label.resize(pet_w, pet_h)
        start_x = screen.width() // 2 - pet_w // 2
        start_y = screen.height() - pet_h - 2
        self.move(start_x, start_y)

        # ── Socket.IO (runs in background thread) ─────────────────────────
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.sio.on('status', self._socket_on_status)
        self._connect_socket()

        self._set_state("idle")
        self.show()

    # ── Socket ────────────────────────────────────────────────────────────────
    def _connect_socket(self):
        def _try():
            try:
                self.sio.connect('http://localhost:5000', wait_timeout=5)
            except Exception as e:
                print(f"[DesktopPet] Socket not connected: {e}")
        threading.Thread(target=_try, daemon=True).start()

    def _socket_on_status(self, data):
        """Called from socket thread — use signal to reach main thread."""
        state = data.get('state', 'idle')
        if state == 'processing':
            state = 'thinking'
        # Emit signal (thread-safe crossing)
        self.bridge.state_changed.emit(state)

    # ── Qt slot — runs on main thread ─────────────────────────────────────────
    def _on_state_changed(self, state: str):
        # Don't interrupt walking with minor state blips
        if state in ('idle',) and self.current_state in ('walking', 'walking_left'):
            return
        self._set_state(state)

    # ── State management ─────────────────────────────────────────────────────
    def _set_state(self, state: str):
        if state == self.current_state:
            return
        print(f"[DesktopPet] → {state}")
        self.current_state = state

        # Stop roam timer when actively doing something
        if state not in ('idle', 'walking', 'walking_left'):
            self.target_x = None
            self.roam_timer.stop()
            self.roam_timer.start(12000)  # reset roam countdown
        else:
            if not self.roam_timer.isActive():
                self.roam_timer.start(8000)

        # Revert after a fixed period for transient states
        self.revert_timer.stop()
        if state in ('listening', 'thinking', 'speaking'):
            self.revert_timer.start(6000)

        self._load_gif(state)

    def _load_gif(self, state: str):
        """Load and play the correct GIF for the given state."""
        # Determine asset file — genuine left/right GIFs, no mirroring needed
        if state == 'walking_left':
            path = os.path.join(ASSETS_DIR, 'walking_left.gif')
            if not os.path.exists(path):
                path = os.path.join(ASSETS_DIR, 'walking.gif')
        elif state == 'walking':
            path = os.path.join(ASSETS_DIR, 'walking.gif')
        elif state == 'idle':
            path = os.path.join(ASSETS_DIR, 'thinking.gif')
        else:
            path = os.path.join(ASSETS_DIR, f'{state}.gif')

        if not os.path.exists(path):
            path = os.path.join(ASSETS_DIR, 'thinking.gif')

        # Stop previous movie
        if self.movie:
            self.movie.stop()
            self.movie = None

        movie = QMovie(path)
        if not movie.isValid():
            print(f"[DesktopPet] Invalid movie: {path}")
            return

        # Scale by height only, preserve natural aspect ratio
        movie.jumpToFrame(0)
        native = movie.currentPixmap().size()
        if native.isValid() and native.height() > 0:
            ratio = native.width() / native.height()
            scaled_h = 220
            scaled_w = int(scaled_h * ratio)
        else:
            scaled_w, scaled_h = 220, 220
        target = QSize(scaled_w, scaled_h)
        movie.setScaledSize(target)

        # Always use setMovie directly — no mirroring needed since we have walking_left.gif
        try:
            movie.frameChanged.disconnect()
        except Exception:
            pass
        self.label.setMovie(movie)
        movie.start()
        self.movie = movie
        self.label.resize(target)
        self.resize(target)

    # ── Walk / physics tick ───────────────────────────────────────────────────
    def _tick(self):
        """Called ~25fps on main thread. Moves pet toward target_x."""
        if self.current_state not in ('walking', 'walking_left'):
            return
        if self.target_x is None:
            return

        x = self.x()
        y = self.y()
        floor_y = self.screen_rect.height() - self.height() - 2

        # Snap to floor
        if y != floor_y:
            self.move(x, floor_y)
            y = floor_y

        dist = self.target_x - x
        if abs(dist) <= self.walk_speed:
            self.move(self.target_x, y)
            self.target_x = None
            self._set_state("idle")
        else:
            step = self.walk_speed if dist > 0 else -self.walk_speed
            self.move(x + step, y)

    def _trigger_roam(self):
        if self.current_state not in ('idle', 'walking', 'walking_left'):
            return
        # 40% chance to pause and think, 60% to walk
        if random.random() < 0.35:
            self._set_state('thinking')
            self.revert_timer.start(3000)
            return

        max_x = self.screen_rect.width() - self.width()
        self.target_x = random.randint(0, max_x)
        dx = self.target_x - self.x()
        # CORRECT direction: moving right → face right (walking), moving left → face left (walking_left)
        if dx >= 0:
            self._set_state('walking')
        else:
            self._set_state('walking_left')

    # ── Drag to move ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            new_pos = event.globalPosition().toPoint() - self.drag_pos
            floor_y = self.screen_rect.height() - self.height() - 2
            # Allow dragging but clamp Y to floor
            clamped_y = min(new_pos.y(), floor_y)
            clamped_x = max(0, min(new_pos.x(), self.screen_rect.width() - self.width()))
            self.move(clamped_x, clamped_y)
            self.target_x = None  # cancel walk

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def closeEvent(self, event):
        try:
            self.sio.disconnect()
        except:
            pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet()
    sys.exit(app.exec())
