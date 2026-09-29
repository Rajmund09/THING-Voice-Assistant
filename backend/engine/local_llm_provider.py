"""
local_llm_provider.py — THING v6.1
Provides a fully local LLM via Ollama.
Acts as PRIMARY brain when Groq API key is invalid/expired or internet is down.
Falls back to Groq if Ollama isn't running.

Ollama setup:
  1. Download from https://ollama.com
  2. Run: ollama pull llama3.2:1b  (fast, 1.3GB — recommended)
       or: ollama pull gemma2:2b
  3. Ollama server starts automatically on http://localhost:11434
"""

import os
import time
import subprocess
import logging
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Fallback model priority list — tries each in order
OLLAMA_FALLBACK_MODELS = ["llama3.2:1b", "llama3.2:3b", "qwen2.5:1.5b", "gemma2:2b", "phi3:mini", "mistral:7b-instruct-q4_0"]

_ollama_status_cache = {"running": False, "model": None, "last_check": 0}


def is_ollama_running() -> bool:
    """Quick check if Ollama server is reachable (cached for 5s)."""
    now = time.time()
    if now - _ollama_status_cache["last_check"] < 5.0 and _ollama_status_cache["last_check"] > 0:
        return _ollama_status_cache["running"]
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.5)
        _ollama_status_cache["running"] = (r.status_code == 200)
        _ollama_status_cache["last_check"] = now
        return _ollama_status_cache["running"]
    except Exception:
        _ollama_status_cache["running"] = False
        _ollama_status_cache["last_check"] = now
        return False


def ensure_ollama_running() -> bool:
    """Auto-start Ollama server if it's not already running."""
    if is_ollama_running():
        return True
    try:
        local_app_data = os.getenv("LOCALAPPDATA", "")
        ollama_path = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
        if os.path.exists(ollama_path):
            logger.info("[LocalLLM] Auto-starting Ollama server: %s serve", ollama_path)
            subprocess.Popen([ollama_path, "serve"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            time.sleep(2)
            _ollama_status_cache["last_check"] = 0
            return is_ollama_running()
    except Exception as e:
        logger.warning("[LocalLLM] Could not auto-start Ollama: %s", e)
    return False


def get_available_ollama_model() -> Optional[str]:
    """Returns the first available model from the priority list, or None."""
    now = time.time()
    if _ollama_status_cache["model"] and now - _ollama_status_cache["last_check"] < 60.0:
        return _ollama_status_cache["model"]
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if r.status_code != 200:
            return None
        installed = {m["name"].split(":")[0]: m["name"] for m in r.json().get("models", [])}
        
        # Check configured model first
        configured_base = OLLAMA_MODEL.split(":")[0]
        if configured_base in installed:
            model = installed[configured_base]
            _ollama_status_cache["model"] = model
            return model
            
        # Try fallbacks in priority order
        for m_name in OLLAMA_FALLBACK_MODELS:
            base = m_name.split(":")[0]
            if base in installed:
                model = installed[base]
                logger.info("[LocalLLM] Using fallback model: %s", model)
                _ollama_status_cache["model"] = model
                return model
                
        if installed:
            first_model = list(installed.values())[0]
            _ollama_status_cache["model"] = first_model
            return first_model
            
        return None
    except Exception:
        return None


def _ollama_chat(prompt: str, system: str = "", history: List[Dict] = None) -> str:
    """Send a chat request to Ollama and return the response."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    for turn in (history or []):
        messages.append({"role": turn.get("speaker", "user"), "content": turn.get("text", "")})
    messages.append({"role": "user", "content": prompt})

    model = get_available_ollama_model()
    if not model:
        raise RuntimeError("No Ollama model available")

    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "num_predict": 120,
                "temperature": 0.3,
            }
        },
        timeout=18,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def process_chat_local(command: str, system_prompt: str = "", history: List[Dict] = None) -> str:
    """
    Main local chat function — replaces Groq chat when API key is invalid or offline.
    Automatically uses the best available Ollama model.
    """
    try:
        if not is_ollama_running() and not ensure_ollama_running():
            return (
                "My local AI brain (Ollama) isn't running. "
                "Download Ollama from ollama.com, then run: ollama pull llama3.2:1b"
            )
        return _ollama_chat(command, system_prompt, history)
    except Exception as exc:
        logger.error("[LocalLLM] Ollama chat error: %s", exc)
        return "I had trouble thinking locally. Make sure Ollama is running."


def classify_intent_local(command: str) -> Optional[Dict]:
    """
    Local intent classification via Ollama — called when Groq LLM classifier fails.
    Returns a structured action dict or None.
    """
    if not is_ollama_running() and not ensure_ollama_running():
        return None

    system = """You are an intent classifier for a voice assistant. 
Given a user command, respond with ONLY a JSON object like:
{"action": "open_app", "app_name": "chrome"}
{"action": "scroll_screen", "direction": "down", "amount": 300}
{"action": "control_system", "type": "volume_up"}
{"action": "chat", "query": "the question"}

Valid actions: open_app, close_app, play_youtube, scroll_screen, control_system, 
search_web, send_whatsapp, get_time, get_date, get_weather, chat, open_url.
Respond with ONLY the JSON, no explanation."""

    try:
        import json
        raw = _ollama_chat(command, system)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            if "action" in data:
                return data
    except Exception as exc:
        logger.error("[LocalLLM] Intent classification error: %s", exc)
    return None
