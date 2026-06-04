"""
local_llm_provider.py — THING v5.5
Provides local LLM inference fallback using Ollama.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "phi3:mini"
TIMEOUT = 15.0

def _query_ollama(messages: List[Dict[str, str]], json_format: bool = False) -> Optional[str]:
    data = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0 if json_format else 0.6,
        }
    }
    
    if json_format:
        data["format"] = "json"

    req = urllib.request.Request(
        OLLAMA_URL, 
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {}).get('content')
    except Exception as e:
        logger.error("[LocalLLM] Ollama connection error: %s", e)
        return None

def classify_intent_local(command: str, system_prompt: str, context_str: str) -> Optional[str]:
    user_input_with_context = f"Conversation Context: {context_str}\nUser Command: {command}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input_with_context}
    ]
    return _query_ollama(messages, json_format=True)

def process_chat_local(command: str, system_prompt: str, history: List[Dict[str, str]]) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["speaker"], "content": turn["text"]})
    messages.append({"role": "user", "content": command})
    
    response = _query_ollama(messages, json_format=False)
    if response:
        return response.strip()
    return "I am currently offline and my local model is unreachable."
