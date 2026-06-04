"""
mail_builder.py — THING Jarvis Upgrade
Intelligent email content generation using Groq.
"""

from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MAIL_GEN_PROMPT = """You are THING's Smart Mail Builder.
The user wants to write an email but might only give a topic.
Generate a professional subject and body for the email.

Topic: {topic}
Recipient Context: {context}

Respond ONLY in JSON format:
{{
  "subject": "...",
  "body": "..."
}}
"""

def generate_mail_content(topic: str, context: str = "") -> dict:
    """Auto-generates email subject and body based on a topic."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": MAIL_GEN_PROMPT.format(topic=topic, context=context)}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[MailBuilder] Error: {e}")
        return {
            "subject": f"Regarding: {topic}",
            "body": f"Dear recipient,\n\nI am writing regarding {topic}.\n\nBest regards,\nRaj"
        }
