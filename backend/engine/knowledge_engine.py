from duckduckgo_search import DDGS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def fetch_knowledge(query: str, realtime: bool = False) -> str:
    """
    Fetches answers to questions.
    If realtime=True, forces a web search.
    Otherwise, uses Groq directly (with fallback to web search if it doesn't know).
    """
    if realtime:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
                if results:
                    snippet = results[0].get("body", "")
                    title = results[0].get("title", "")
                    # Summarize with Groq for a clean answer
                    return summarize_with_groq(query, snippet)
                return "I couldn't find live data for that."
        except Exception as e:
            return "Web search is currently unavailable."
            
    else:
        # Ask Groq first
        try:
            messages = [
                {"role": "system", "content": "You are THING, a highly intelligent assistant. Answer factual questions accurately and concisely in 1-2 sentences. DO NOT say 'Based on the context' or 'As an AI'."},
                {"role": "user", "content": query}
            ]
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception:
            return "My reasoning engine is offline."

def summarize_with_groq(query: str, context: str) -> str:
    """Uses Groq to summarize raw search results into a natural spoken answer."""
    try:
        messages = [
            {"role": "system", "content": "You are THING, a voice assistant. Summarize the provided web context to answer the user's query in 1-2 short, natural sentences."},
            {"role": "user", "content": f"Query: {query}\nContext: {context}"}
        ]
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=100
        )
        return response.choices[0].message.content
    except:
        return context # Fallback to raw snippet
