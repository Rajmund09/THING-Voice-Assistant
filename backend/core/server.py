"""
server.py — THING v4.0
Flask + SocketIO server.
"""

import time
import uuid
import json
import threading
import webbrowser
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.core.audio import audio
from backend.core.pipeline import process_pipeline
from backend.core.context_observer import ContextObserver

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

ASSISTANT_RUNNING = True
_tts_rate = 1

# Deduplication state
_last_command_text = ""
_last_command_time = 0
DEDUP_THRESHOLD = 0.8


def process_command(command: str, bypass_confirm: bool = False):
    global _last_command_text, _last_command_time
    if not command: return

    now = time.time()
    if command.strip().lower() == _last_command_text and (now - _last_command_time) < DEDUP_THRESHOLD:
        return
    
    _last_command_text = command.strip().lower()
    _last_command_time = now

    # Emit user message to UI for sync
    socketio.emit("user_message", {"id": str(uuid.uuid4()), "text": command, "speaker": "user"})

    from backend.engine.state_manager import state_manager
    if state_manager.is_busy:
        print("[Server] Assistant is currently busy. Command ignored.")
        return

    command = command.strip().lower()

    if any(w in command for w in ["stop listening", "exit assistant", "bye thing", "shutdown assistant"]):
        audio.speak("Goodbye.")
        socketio.emit("response", {"action": "shutdown", "final_response": "Goodbye.", "success": True})
        global ASSISTANT_RUNNING
        ASSISTANT_RUNNING = False
        return

    state_manager.acquire_lock()
    socketio.emit("status", {"state": "processing", "text": "Thinking..."})

    try:
        packet = process_pipeline(command, bypass_confirm=bypass_confirm)
        speak_text = packet.get("speak_text") or packet.get("final_response", "Done.")
        audio.speak(speak_text, rate=_tts_rate)
        socketio.emit("response", packet)
    except Exception as e:
        print(f"[Server] Error: {e}")
    finally:
        state_manager.release_lock()
        socketio.emit("status", {"state": "idle", "text": "Active"})


def assistant_loop():
    audio.speak("System initialized.")
    while ASSISTANT_RUNNING:
        command = audio.listen_for_command()
        if command:
            process_command(command)
        time.sleep(0.1)
    import os; os._exit(0)


@socketio.on("connect")
def handle_connect():
    emit("status", {"state": "idle", "text": "Connected"})

@socketio.on("text_command")
def handle_text_command(data):
    command = data.get("command", "").strip()
    if not command: return
    threading.Thread(target=process_command, args=(command,), daemon=True).start()

@socketio.on("stop_speaking")
def handle_stop():
    audio.stop_speaking()
    emit("status", {"state": "idle", "text": "Stopped"})

@socketio.on("update_voice_settings")
def handle_voice_settings(data):
    from backend.modules.voice_manager import voice_manager
    voice_manager.update_settings(data)
    
    if data.get("preview"):
        gender = data.get("gender", "male")
        test_msg = f"Systems calibrated. I am THING, your premium {gender} assistant. Neural voice link is active."
        audio.speak(test_msg)
        
    emit("status", {"state": "idle", "text": "Voice settings updated"})


@socketio.on("get_profile")
def handle_get_profile():
    from backend.modules.profile_manager import profile_manager
    emit("profile_data", profile_manager.profile)

@socketio.on("send_edited_email")
def handle_send_edited_email(data):
    from backend.engine.state_manager import state_manager
    email_ctx = state_manager.context.get("email")
    if email_ctx:
        email_ctx["recipient"] = data.get("recipient", email_ctx["recipient"])
        email_ctx["subject"] = data.get("subject", email_ctx["subject"])
        email_ctx["body"] = data.get("body", email_ctx["body"])
        # Trigger the "yes" command to complete the flow
        threading.Thread(target=process_command, args=("yes",), daemon=True).start()

@socketio.on("suggestion_response")
def handle_suggestion_response(data):
    """Handles user response to a proactive suggestion."""
    if not data.get("accepted"):
        return
    
    action = data.get("action")
    if not action:
        return
    
    # Map internal actions to user-like commands for the pipeline
    mapping = {
        "open_meeting_and_notify": "open the meeting link from my clipboard",
        "control_system_lock": "lock my pc",
        "list_heavy_processes": "check cpu usage",
        "check_ram_usage": "check ram usage",
        "summarize_day": "summarize my day",
        "mute_notifications": "mute my system"
    }
    
    cmd = mapping.get(action, action)
    threading.Thread(target=process_command, args=(cmd, True), daemon=True).start()

def start_server():
    audio.on_status_change = lambda state, text: socketio.emit("status", {"state": state, "text": text})

    # Start Proactive Observer
    observer = ContextObserver(socketio)
    observer.start()

    # Start Connectivity Monitor (Phase 5)
    from backend.core.connectivity_monitor import monitor as connectivity_monitor
    connectivity_monitor.set_socketio(socketio)
    connectivity_monitor.start()

    threading.Thread(target=assistant_loop, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)


# ─────────────────────────────────────────────────────────────────────
#  Phase 4A — OAuth REST Endpoints
# ─────────────────────────────────────────────────────────────────────

@app.route("/oauth/start/<service>", methods=["GET"])
def oauth_start(service: str):
    """
    Generates the OAuth authorization URL for the requested service
    and opens it in the user's default browser.

    Returns JSON: {"status": "ok", "url": "..."}  or  {"error": "..."}
    """
    from backend.core.oauth_manager import get_auth_url

    url = get_auth_url(service)
    if not url:
        return jsonify({
            "error": f"Service '{service}' is not configured or unsupported. "
                     f"Check your .env for {service.upper()}_CLIENT_ID."
        }), 400

    # Open the URL in the user's default browser for convenience
    webbrowser.open(url)
    return jsonify({"status": "ok", "url": url, "service": service})


@app.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    """
    Receives the OAuth authorization code from the browser redirect.
    Exchanges it for tokens and stores them encrypted.

    Returns a simple HTML page the user sees after authorizing.
    """
    from backend.core.oauth_manager import handle_callback, get_pending_service

    code  = request.args.get("code", "")
    state = request.args.get("state", "")
    error = request.args.get("error", "")

    if error:
        return (
            f"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            f"<h2 style='color:#e74c3c'>❌ Authorization Failed</h2>"
            f"<p>{error}</p>"
            f"<p>You can close this window.</p></body></html>"
        ), 400

    if not code:
        return (
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2 style='color:#e74c3c'>❌ No authorization code received.</h2>"
            "<p>You can close this window.</p></body></html>"
        ), 400

    service = get_pending_service()
    success = handle_callback(code, service)

    # Notify frontend via WebSocket so the dashboard updates immediately
    if success:
        socketio.emit("oauth_connected", {"service": service})
        return (
            f"<html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#0a0a0a;color:#fff'>"
            f"<h2 style='color:#00e676'>✅ {service.title()} Connected!</h2>"
            f"<p style='color:#aaa'>THING is now authorized to access your {service.title()} account.</p>"
            f"<p style='color:#555;font-size:12px'>You can close this tab and return to THING.</p>"
            f"</body></html>"
        )
    else:
        return (
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px;background:#0a0a0a;color:#fff'>"
            "<h2 style='color:#e74c3c'>❌ Token Exchange Failed</h2>"
            "<p style='color:#aaa'>Check your client credentials in .env and try again.</p>"
            "<p style='color:#555;font-size:12px'>You can close this tab.</p>"
            "</body></html>"
        ), 500


@app.route("/oauth/status", methods=["GET"])
def oauth_status():
    """
    Returns the connection status for all supported OAuth services.

    Returns JSON: {"google": true, "spotify": false, ...}
    """
    from backend.core.oauth_manager import get_all_statuses
    return jsonify(get_all_statuses())


@app.route("/oauth/disconnect/<service>", methods=["DELETE"])
def oauth_disconnect(service: str):
    """
    Revokes and deletes the stored token for a service.

    Returns JSON: {"status": "disconnected", "service": "..."}
    """
    from backend.core.oauth_manager import disconnect_service
    disconnect_service(service)
    socketio.emit("oauth_disconnected", {"service": service})
    return jsonify({"status": "disconnected", "service": service})
