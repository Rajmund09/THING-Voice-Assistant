"""
sms_ops.py — THING v4.6
Handles sending "normal" SMS messages using the system's default protocol.
On Windows, this typically triggers the Phone Link app.
"""

import webbrowser
import urllib.parse
import logging

logger = logging.getLogger(__name__)

def send_sms(phone_number: str, message: str) -> str:
    """
    Sends a normal SMS message using the 'sms:' protocol.
    This opens the default system messaging app (e.g., Phone Link on Windows).
    """
    if not phone_number:
        return "No phone number specified."
    if not message:
        return "No message specified."

    # Clean the phone number (remove spaces, dashes, etc.)
    clean_number = "".join(filter(lambda x: x.isdigit() or x == '+', phone_number))
    
    try:
        # Construct the SMS protocol URL
        # Format: sms:+1234567890?body=Hello
        encoded_msg = urllib.parse.quote(message)
        url = f"sms:{clean_number}?body={encoded_msg}"
        
        logger.info("Opening SMS protocol: %s", url)
        
        # Open the protocol handler
        webbrowser.open(url)
        
        return f"Opening your messaging app to send a normal message to {phone_number}."

    except Exception as e:
        logger.error("Error triggering SMS: %s", e)
        return f"Failed to open messaging app: {str(e)}"
