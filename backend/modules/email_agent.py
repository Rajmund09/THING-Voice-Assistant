"""
email_agent.py — THING Jarvis Upgrade
Handles guided email flow, content generation, and secure sending.
"""

import os
import re
import yagmail
from typing import Dict, Any, Optional
from backend.engine.state_manager import state_manager, AssistantState
from backend.modules.mail_builder import generate_mail_content
from backend.engine.entity_resolver import resolve_contact


# ── Simple email/contact validation ──────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_GARBAGE_PHRASES = [
    "who should", "what should", "where should", "send to you",
    "i don't know", "not sure", "never mind", "forget it",
]

def _looks_like_valid_recipient(text: str) -> bool:
    """
    Returns True if the text looks like a real name or email.
    Returns False if the user clearly answered the question with a question.
    """
    t = text.lower().strip()
    if not t or len(t) < 2:
        return False
    # Reject if it matches a known garbage pattern
    if any(phrase in t for phrase in _GARBAGE_PHRASES):
        return False
    # Must either contain an @ (email) or be a short plausible name (≤ 4 words)
    if "@" in t:
        return bool(_EMAIL_RE.search(t))
    # Name: 1-4 words, no special characters
    words = t.split()
    if len(words) > 5:
        return False
    return True


def _extract_email_from_text(text: str) -> str:
    """Pull the first email address from arbitrary text."""
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else text

class EmailAgent:
    def __init__(self):
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS") # Use App Password

    def start_flow(self, recipient: str = None, topic: str = None, subject: str = None, content: str = None):
        """Initializes or continues an email workflow."""
        
        # ── Reset if called with a fresh recipient while already composing ──
        # This lets "send mail to X@y.com" escape a stuck flow.
        if (
            state_manager.current_state == AssistantState.EMAIL_COMPOSING
            and recipient
            and _looks_like_valid_recipient(recipient)
        ):
            # Start over cleanly with the new recipient
            state_manager.context["email"] = {
                "recipient": recipient,
                "topic": topic,
                "subject": subject,
                "body": content,
                "step": "check_recipient"
            }
        elif state_manager.current_state != AssistantState.EMAIL_COMPOSING:
            state_manager.set_state(AssistantState.EMAIL_COMPOSING)
            state_manager.context["email"] = {
                "recipient": recipient,
                "topic": topic,
                "subject": subject,
                "body": content,
                "step": "check_recipient"
            }

        email_ctx = state_manager.context["email"]

        # Step 1: Check Recipient
        if not email_ctx["recipient"]:
            email_ctx["step"] = "ask_recipient"
            return "Who should I send this email to?"

        # Step 2: Check Topic (Smart Generation)
        if not email_ctx.get("topic") and not email_ctx.get("body"):
            email_ctx["step"] = "ask_topic"
            return "What would you like the email to be about?"

        if email_ctx.get("topic") and (not email_ctx.get("subject") or not email_ctx.get("body")):
            generated = generate_mail_content(email_ctx.get("topic"), email_ctx.get("recipient"))
            email_ctx["subject"] = email_ctx.get("subject") or generated.get("subject")
            email_ctx["body"] = email_ctx.get("body") or generated.get("body")
            # Clear topic after generation so we don't regenerate if they just edit via UI
            email_ctx["topic"] = None

        if not email_ctx.get("subject"):
            email_ctx["step"] = "ask_subject"
            return f"What should be the subject for the email to {email_ctx['recipient']}?"

        if not email_ctx.get("body"):
            email_ctx["step"] = "ask_body"
            return "What would you like to say in the message?"

        # Step 3: Review
        email_ctx["step"] = "review"
        return {
            "type": "email_review",
            "recipient": email_ctx["recipient"],
            "subject": email_ctx["subject"],
            "body": email_ctx["body"],
            "message": f"I've prepared the email for {email_ctx['recipient']}. Would you like me to send it?"
        }

    def handle_input(self, text: str) -> str:
        """Processes user input during the email flow."""
        email_ctx = state_manager.context.get("email")
        if not email_ctx:
            return "I'm sorry, I lost track of the email. Should we start over?"

        step = email_ctx["step"]

        if step == "ask_recipient":
            resolved = resolve_contact(text) or text
            # Validate — reject if user answered the question with gibberish
            if not _looks_like_valid_recipient(resolved):
                return "That doesn't look like a valid name or email address. Who should I send this to?"
            # If it contains an email anywhere, extract it cleanly
            if "@" in resolved:
                resolved = _extract_email_from_text(resolved)
            email_ctx["recipient"] = resolved
            return self.start_flow()

        if step == "ask_topic":
            email_ctx["topic"] = text
            return self.start_flow()

        if step == "ask_subject":
            email_ctx["subject"] = text
            return self.start_flow()

        if step == "ask_body":
            email_ctx["body"] = text
            return self.start_flow()

        if step == "review":
            if any(w in text.lower() for w in ["yes", "send", "proceed", "do it"]):
                return self.send_email()
            if any(w in text.lower() for w in ["no", "cancel", "stop"]):
                state_manager.clear_active_app()
                state_manager.set_state(AssistantState.IDLE)
                state_manager.context.pop("email", None)
                return "Email cancelled."
            
            # Handle edits
            if "subject" in text.lower():
                email_ctx["step"] = "ask_subject"
                return "What should be the new subject?"
            if "body" in text.lower() or "content" in text.lower() or "message" in text.lower():
                email_ctx["step"] = "ask_topic"
                email_ctx["body"] = None
                return "What should the new message be about?"
            if "recipient" in text.lower() or "to" in text.lower():
                email_ctx["step"] = "ask_recipient"
                return "Who should be the new recipient?"

        return "I didn't quite catch that. Should I send the email, or would you like to edit it?"

    def send_email(self) -> str:
        """Sends the composed email using yagmail."""
        email_ctx = state_manager.context.get("email")
        try:
            if not self.user or not self.password:
                state_manager.context.pop("email", None)
                state_manager.set_state(AssistantState.IDLE)
                return "I don't have your email credentials. Please set EMAIL_USER and EMAIL_PASS in the .env file."

            # Final recipient validation before sending
            recipient = email_ctx.get("recipient", "")
            if not _looks_like_valid_recipient(recipient):
                state_manager.context.pop("email", None)
                state_manager.set_state(AssistantState.IDLE)
                return f"'{recipient}' is not a valid email address. Email cancelled. Please try again with a valid address."

            # Extract raw email if embedded in a sentence
            if "@" in recipient:
                recipient = _extract_email_from_text(recipient)
                email_ctx["recipient"] = recipient

            yag = yagmail.SMTP(self.user, self.password)
            yag.send(
                to=recipient,
                subject=email_ctx["subject"],
                contents=email_ctx["body"]
            )
            state_manager.context.pop("email", None)
            state_manager.set_state(AssistantState.IDLE)
            return "Email sent successfully."
        except Exception as e:
            print(f"[Email] Send Error: {e}")
            # CRITICAL: always reset state on failure so conversation is not stuck
            state_manager.context.pop("email", None)
            state_manager.set_state(AssistantState.IDLE)
            return f"Failed to send email: {e}. Please try again with 'send mail to [address]'."


# Singleton
email_agent = EmailAgent()
