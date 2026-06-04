import re

# Keywords indicating local system/browser commands
LOCAL_KEYWORDS = [
    "open", "close", "play", "pause", "volume", "brightness", "scroll", 
    "type", "send", "screenshot", "camera", "lock", "shutdown", "restart",
    "stop", "cancel", "abort"
]

# Keywords indicating realtime web search
LIVE_KEYWORDS = [
    "weather", "price", "score", "match", "latest", "news", "today", "now", "election"
]

# Keywords indicating factual knowledge questions
KNOWLEDGE_KEYWORDS = [
    "who is", "what is", "where is", "when did", "how to", "tell me about", "explain"
]

# Keywords indicating fast-path conversational greetings
FAST_CHAT_WORDS = {
    "hello", "hi", "hey", "hola", "namaste", "howdy", "whats up", "what's up",
    "how are you", "how are you doing", "good morning", "good afternoon", "good evening",
    "good night", "thank you", "thanks", "thanks a lot", "thank you so much",
    "who are you", "what is your name", "who made you", "hi there", "hey there",
    "yo", "morning", "night", "bye", "goodbye", "see ya", "hey thing", "hello thing"
}

def is_fast_chat(command: str) -> bool:
    """
    Returns True if the command is a pure greeting or short conversational phrase
    that should skip the intent classifier LLM.
    """
    cmd = command.lower().strip()
    # Remove simple punctuation (keep it very fast)
    if not cmd: return False
    
    # Strip common punctuation like ?, !, .
    for char in "?!.":
        cmd = cmd.replace(char, "")
    
    # Check if the entire command is in our fast-path set
    if cmd in FAST_CHAT_WORDS:
        return True
        
    # Pattern: "hi [anything]" where [anything] is very short
    if cmd.startswith("hi ") and len(cmd) < 10:
        return True
        
    return False

def classify_query(command: str) -> str:
    """Routes the command into LOCAL, LIVE_DATA, KNOWLEDGE, or CHAT."""
    if is_fast_chat(command):
        return "CHAT"
        
    cmd_lower = command.lower().strip()
    
    # 1. Local Commands (Fastest path)
    if any(cmd_lower.startswith(k) or k in cmd_lower.split() for k in LOCAL_KEYWORDS):
        return "LOCAL"
        
    # 2. Live Data
    if any(k in cmd_lower for k in LIVE_KEYWORDS):
        return "LIVE_DATA"
        
    # 3. Knowledge
    if any(cmd_lower.startswith(k) for k in KNOWLEDGE_KEYWORDS):
        return "KNOWLEDGE"
        
    # 4. Fallback to Chat Persona
    return "CHAT"
