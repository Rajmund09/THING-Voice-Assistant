import datetime

def get_info(query: str) -> str:
    """Gets real-time information."""
    query = query.lower()
    if "time" in query:
        return f"It's {datetime.datetime.now().strftime('%I:%M %p')}."
    elif "date" in query or "day" in query:
        return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
    
    # We could integrate Wikipedia or Weather API here.
    return f"I don't have real-time data for {query} yet."
