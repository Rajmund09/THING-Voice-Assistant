from groq import Groq
import os
from dotenv import load_dotenv
from backend.engine.memory_engine import memory
from backend.modules.identity_manager import get_identity_prompt
from backend.security.hallucination_guard import validate_response

load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def process_chat(command: str) -> str:
    """
    Handles natural conversation without tools.
    """
    try:
        from backend.modules.profile_manager import profile_manager
        
        # Build dynamic system prompt with user context
        profile_summary = profile_manager.get_summary()
        CHAT_PROMPT = f"""{get_identity_prompt()}
User Profile Context:
{profile_summary}

Communicate with surgical precision: be SHORT, CONCISE, and NATURAL. Avoid long paragraphs.
Never expose JSON, tags, or internal logic.
"""
        
        # Get sandboxed chat history for conversation flow
        history = memory.get_chat_history()
        messages = [{"role": "system", "content": CHAT_PROMPT}]
        
        # Add user preferences to context if they exist
        prefs = memory.memory.get("preferences", {})
        if prefs:
            pref_str = "User Preferences: " + ", ".join([f"{k}: {v}" for k, v in prefs.items()])
            messages.append({"role": "system", "content": pref_str})

        for turn in history:
            messages.append({"role": turn["speaker"], "content": turn["text"]})
            
        messages.append({"role": "user", "content": command})
        
        from backend.core.connectivity_monitor import monitor as connectivity_monitor
        if connectivity_monitor.is_online():
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=150
            )
            raw_reply = response.choices[0].message.content
        else:
            from backend.engine.local_llm_provider import process_chat_local
            raw_reply = process_chat_local(command, CHAT_PROMPT, history)
        
        # Guard against hallucinations
        reply = validate_response(raw_reply, command)
        
        # Save to sandboxed history
        memory.add_chat("user", command)
        memory.add_chat("assistant", reply)
        
        return reply
        
    except Exception as e:
        print(f"Chat Engine Error: {e}")
        return "I am currently unable to process that."
