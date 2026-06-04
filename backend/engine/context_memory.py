"""
context_memory.py — THING Jarvis Upgrade
Processes conversation history to extract and store user preferences.
"""

import json
import os
from typing import Dict, Any, Optional

PREFERENCE_KEYWORDS = [
    "remember", "call me", "my favorite", "i like", "don't like", 
    "i am", "my name is", "i work at", "my birthday is"
]

def extract_preferences(user_text: str) -> Dict[str, str]:
    """
    Very basic NLP to extract preferences. 
    In a real system, this would use an LLM call.
    """
    text = user_text.lower().strip()
    prefs = {}
    
    # 1. "Remember you are developed by Raj" -> Special Case
    if "developed by" in text or "who made you" in text:
        # Handled by identity_manager, but we can store it too
        pass
        
    # 2. "Remember my name is X"
    match = re.search(r"my name is (\w+)", text)
    if match: prefs["user_name"] = match.group(1).capitalize()
    
    # 3. "Call me X"
    match = re.search(r"call me (\w+)", text)
    if match: prefs["nickname"] = match.group(1).capitalize()
    
    # 4. "My favorite X is Y"
    match = re.search(r"my favorite (\w+) is (\w+)", text)
    if match: prefs[f"fav_{match.group(1)}"] = match.group(2)
    
    return prefs

import re # Need re
