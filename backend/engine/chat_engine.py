"""
chat_engine.py — THING v6.1
AI chat engine with priority stack:
  1. RAG: retrieve personal context from local knowledge base
  2. Ollama: local LLM (no API key needed) — PRIMARY
  3. Groq: cloud LLM — FALLBACK if Ollama isn't installed

This means THING works even if your Groq key expires.
"""

import os
import logging
from dotenv import load_dotenv
from backend.engine.memory_engine import memory
from backend.modules.identity_manager import get_identity_prompt

load_dotenv(override=True)
logger = logging.getLogger(__name__)


def process_chat(command: str) -> str:
    """
    Handles natural conversation.
    Priority: Ollama (local) → Groq (cloud fallback).
    Always injects RAG context when available.
    """
    try:
        from backend.modules.profile_manager import profile_manager
        profile_summary = profile_manager.get_summary()

        # ── Build system prompt ──────────────────────────────────
        CHAT_PROMPT = f"""{get_identity_prompt()}
User Profile Context:
{profile_summary}

Communicate with surgical precision: be SHORT, CONCISE, and NATURAL. Avoid long paragraphs.
Never expose JSON, tags, or internal logic.
"""

        # ── RAG: inject personal knowledge context ───────────────
        rag_context = ""
        try:
            from backend.engine.rag_engine import rag_engine
            rag_context = rag_engine.query(command, n_results=2)
            if rag_context:
                CHAT_PROMPT += f"\n\nRelevant Personal Context (use this to answer accurately):\n{rag_context}"
                logger.debug("[Chat] RAG context injected (%d chars)", len(rag_context))
        except Exception as rag_exc:
            logger.debug("[Chat] RAG unavailable: %s", rag_exc)

        # ── Build message history ─────────────────────────────────
        history = memory.get_chat_history()
        prefs = memory.memory.get("preferences", {})

        # ── Try Ollama first (local, no API key needed) ──────────
        try:
            from backend.engine.local_llm_provider import is_ollama_running, process_chat_local
            if is_ollama_running():
                logger.debug("[Chat] Using Ollama (local)")
                raw_reply = process_chat_local(command, CHAT_PROMPT, history)
                reply = _validate(raw_reply, command)
                _save_to_memory(command, reply)
                return reply
        except Exception as ollama_exc:
            logger.warning("[Chat] Ollama failed: %s — trying Groq", ollama_exc)

        # ── Try Groq (cloud fallback) ─────────────────────────────
        try:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
            messages = [{"role": "system", "content": CHAT_PROMPT}]
            if prefs:
                pref_str = "User Preferences: " + ", ".join(f"{k}: {v}" for k, v in prefs.items())
                messages.append({"role": "system", "content": pref_str})
            for turn in history:
                messages.append({"role": turn["speaker"], "content": turn["text"]})
            messages.append({"role": "user", "content": command})

            response = client.chat.completions.create(
                model=os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant"),
                messages=messages,
                max_tokens=150,
            )
            raw_reply = response.choices[0].message.content
            logger.debug("[Chat] Used Groq (cloud)")
            reply = _validate(raw_reply, command)
            _save_to_memory(command, reply)
            return reply
        except Exception as groq_exc:
            logger.error("[Chat] Groq failed: %s", groq_exc)

        # ── Both failed ───────────────────────────────────────────
        return (
            "My AI brain is offline. "
            "Install Ollama from ollama.com and run: ollama pull gemma2:2b — "
            "then I'll work without any API key."
        )

    except Exception as exc:
        logger.error("[Chat] Unexpected error: %s", exc)
        return "I am currently unable to process that."


def _validate(text: str, command: str) -> str:
    """Run hallucination guard if available, else return as-is."""
    try:
        from backend.security.hallucination_guard import validate_response
        return validate_response(text, command)
    except Exception:
        return text


def _save_to_memory(command: str, reply: str):
    """Persist turn to memory."""
    try:
        memory.add_chat("user", command)
        memory.add_chat("assistant", reply)
    except Exception:
        pass
