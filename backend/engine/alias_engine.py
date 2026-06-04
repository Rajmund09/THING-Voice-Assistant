"""
alias_engine.py — THING Jarvis Upgrade
Maps shorthand commands and app names to their canonical forms.
"""

APP_ALIASES = {
    "wp": "whatsapp",
    "wtsp": "whatsapp",
    "vs": "vscode",
    "vsc": "vscode",
    "yt": "youtube",
    "ig": "instagram",
    "fb": "facebook",
    "gh": "github",
    "ms": "microsoft",
    "word": "winword",
    "ppt": "powerpnt",
    "excel": "excel",
    "calc": "calculator",
    "cmd": "terminal",
    "ps": "powershell",
}

COMMAND_ALIASES = {
    "mail": "send email",
    "msg": "send message",
    "text": "send message",
    "play": "play youtube",
}

def resolve_alias(word: str) -> str:
    """Resolves a single word alias."""
    word_lower = word.lower().strip()
    return APP_ALIASES.get(word_lower, word_lower)

def expand_command(command: str) -> str:
    """Expands aliases within a command string."""
    words = command.lower().split()
    if not words:
        return command
        
    # Check first word for command aliases
    first_word = words[0]
    if first_word in COMMAND_ALIASES:
        words[0] = COMMAND_ALIASES[first_word]
        
    # Check all words for app aliases
    resolved_words = [APP_ALIASES.get(w, w) for w in words]
    
    return " ".join(resolved_words)
