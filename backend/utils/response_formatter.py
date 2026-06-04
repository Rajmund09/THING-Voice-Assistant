"""
response_formatter.py — THING v4.0
Legacy shim — delegates to response_manager.
Keeps backward compatibility in case any old import exists.
"""

from backend.utils.response_manager import format_premium_response


def format_response(text: str) -> str:
    """Legacy shim. Delegates to format_premium_response."""
    return format_premium_response(text)
