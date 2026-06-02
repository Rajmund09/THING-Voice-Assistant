"""
context_observer.py — THING v5.0
Background thread that monitors system state and emits proactive suggestions.
"""

import time
import threading
import psutil
import pyperclip
import os
from datetime import datetime
from typing import Dict, Optional

from backend.core.suggestion_engine import evaluate_clipboard, evaluate_system_load, evaluate_idle, evaluate_time
from backend.engine.state_manager import state_manager
from backend.core.scheduler import Scheduler

class ContextObserver:
    def __init__(self, socketio):
        self.socketio = socketio
        self._thread = None
        self._stop_event = threading.Event()
        
        self.last_clipboard = ""
        self.cooldowns: Dict[str, float] = {}
        self.COOLDOWN_SECONDS = 600 # 10 minutes from plan
        
        # Config
        self.enabled = os.getenv("PROACTIVE_ENABLED", "true").lower() == "true"
        self.clipboard_enabled = os.getenv("PROACTIVE_CLIPBOARD", "true").lower() == "true"
        self.idle_enabled = os.getenv("PROACTIVE_IDLE", "true").lower() == "true"
        self.load_enabled = os.getenv("PROACTIVE_LOAD", "false").lower() == "true" # Default off per Q1
        self.app_monitoring_enabled = os.getenv("PROACTIVE_APP_MONITORING", "true").lower() == "true"
        self.last_running_apps = set()
        
        self.scheduler = Scheduler(self._handle_scheduled_event)

    def start(self):
        if not self.enabled:
            print("[ContextObserver] Disabled via config.")
            return
            
        print("[ContextObserver] Starting proactive monitoring...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.scheduler.start()

    def stop(self):
        self._stop_event.set()
        self.scheduler.stop()

    def _handle_scheduled_event(self, event_type):
        if event_type == "scheduled_time_check":
            hour = datetime.now().hour
            suggestion = evaluate_time(hour, self.scheduler.eod_hour)
            if suggestion:
                self._emit_suggestion(suggestion)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                # 1. Check Clipboard
                if self.clipboard_enabled:
                    self._check_clipboard()
                
                # 2. Check System Load
                if self.load_enabled:
                    self._check_system_load()
                
                # 3. Check Idle
                if self.idle_enabled:
                    self._check_idle()
                
                # 4. Check Active Apps
                if self.app_monitoring_enabled:
                    self._check_active_apps()
                
            except Exception as e:
                print(f"[ContextObserver] Loop error: {e}")
                
            time.sleep(30) # 30s interval from plan

    def _check_clipboard(self):
        try:
            current = pyperclip.paste().strip()
            if current and current != self.last_clipboard:
                suggestion = evaluate_clipboard(current)
                if suggestion:
                    self._emit_suggestion(suggestion)
                self.last_clipboard = current
        except Exception:
            pass # clipboard might be locked by another app

    def _get_top_cpu_process(self) -> Optional[str]:
        try:
            procs = []
            for proc in psutil.process_iter(['name', 'cpu_percent']):
                try:
                    pct = proc.info.get('cpu_percent')
                    name = proc.info.get('name')
                    if pct is not None and name:
                        procs.append((name, pct))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            if procs:
                procs.sort(key=lambda x: x[1], reverse=True)
                return procs[0][0]
        except Exception:
            pass
        return None

    def _get_top_ram_process(self) -> Optional[str]:
        try:
            procs = []
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    mem_info = proc.info.get('memory_info')
                    name = proc.info.get('name')
                    if mem_info and name:
                        procs.append((name, mem_info.rss))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            if procs:
                procs.sort(key=lambda x: x[1], reverse=True)
                return procs[0][0]
        except Exception:
            pass
        return None

    def _check_system_load(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        top_cpu = self._get_top_cpu_process() if cpu > 90 else None
        top_ram = self._get_top_ram_process() if ram > 90 else None
        suggestion = evaluate_system_load(cpu, ram, top_cpu, top_ram)
        if suggestion:
            self._emit_suggestion(suggestion)

    def _check_active_apps(self):
        try:
            current_apps = set()
            meeting_apps = {"zoom.exe", "teams.exe", "msteams.exe", "discord.exe"}
            
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info.get('name')
                    if name:
                        name_lower = name.lower()
                        if name_lower in meeting_apps:
                            current_apps.add(name_lower)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Detect new meeting apps starting
            new_apps = current_apps - self.last_running_apps
            if new_apps:
                app_name = list(new_apps)[0].replace(".exe", "").capitalize()
                if app_name == "Msteams":
                    app_name = "Teams"
                
                suggestion = {
                    "id": "meeting_app_detected",
                    "message": f"I notice you started {app_name}. Would you like me to enable focus settings or mute notifications?",
                    "action": "mute_notifications",
                    "icon": "volume-x",
                    "dismissible": True
                }
                self._emit_suggestion(suggestion)
                
            self.last_running_apps = current_apps
        except Exception as e:
            print(f"[ContextObserver] Active app check error: {e}")

    def _check_idle(self):
        idle_min = state_manager.get_idle_minutes()
        suggestion = evaluate_idle(idle_min)
        if suggestion:
            self._emit_suggestion(suggestion)

    def _emit_suggestion(self, suggestion: dict):
        sid = suggestion["id"]
        now = time.time()
        
        # Check cooldown
        if sid in self.cooldowns and (now - self.cooldowns[sid]) < self.COOLDOWN_SECONDS:
            return
            
        self.cooldowns[sid] = now
        print(f"[ContextObserver] Emitting proactive suggestion: {sid}")
        self.socketio.emit("proactive_suggestion", suggestion)
