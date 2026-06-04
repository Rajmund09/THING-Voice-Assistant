"""
about_me_engine.py — THING Jarvis Upgrade
Engine to answer questions about the user professionally.
"""

from backend.modules.profile_manager import profile_manager
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ABOUT_ME_SYSTEM_PROMPT = """You are THING, a professional assistant. 
You have access to the user's personal profile data provided below.
Answer questions about the user (Raj) in a professional, proud, and concise manner.
If you don't know something, say you don't have that information yet but can remember it if they tell you.

User Profile:
{profile_summary}
"""

def get_about_me_response(query: str) -> str:
    """Generates a professional response about the user."""
    summary = profile_manager.get_summary()
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": ABOUT_ME_SYSTEM_PROMPT.format(profile_summary=summary)},
                {"role": "user", "content": query}
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AboutMe] LLM Error: {e}")
        return "I know a lot about Raj, but I'm having trouble retrieving the details right now."
