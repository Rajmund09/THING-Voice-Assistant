"""
media_matcher.py — THING Jarvis Upgrade
Fuzzy matching for song titles and query normalization.
"""

import re
from fuzzywuzzy import fuzz

def normalize_query(query: str) -> str:
    """
    Cleans up messy YouTube queries:
    - Removes pipes (|) and dashes (-)
    - Removes 'feat', 'ft', 'official', 'video', 'lyrics'
    - Removes extra whitespace
    """
    q = query.lower()
    
    # Remove common clutter
    clutter = [
        r"\|", r"-", r"feat\.?", r"ft\.?", r"official", r"video", r"lyrics", 
        r"audio", r"hd", r"4k", r"\[.*?\]", r"\(.*?\)"
    ]
    
    for pattern in clutter:
        q = re.sub(pattern, " ", q)
        
    # Remove extra spaces
    q = " ".join(q.split())
    
    return q

def is_match(query: str, found_title: str, threshold: int = 70) -> bool:
    """Checks if the found title matches the query closely enough."""
    q = normalize_query(query)
    t = normalize_query(found_title)
    
    score = fuzz.token_set_ratio(q, t)
    return score >= threshold
