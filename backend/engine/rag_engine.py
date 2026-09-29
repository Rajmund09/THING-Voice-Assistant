"""
rag_engine.py — THING v6.1
Personal RAG (Retrieval-Augmented Generation) Knowledge Base.

Lets THING answer questions about YOU using your own documents/notes.
Uses ChromaDB (local vector DB) + sentence-transformers (local embeddings).
No internet required. No API key needed.

Usage:
  - Add documents: rag_engine.add_document("My name is Raj...", source="about_me")
  - Query: rag_engine.query("what is my name?")
  - Auto-indexes: profile, memory, contacts on startup

Directory: knowledge_base/ (gitignored)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base")
COLLECTION_NAME = "thing_personal_kb"


class RAGEngine:
    """Local vector knowledge base for personal context retrieval."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._embedder = None
        self._ready = False

    def _init(self):
        """Lazy init — don't load heavy models at import time."""
        if self._ready:
            return True
        try:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(KB_DIR, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=KB_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("[RAG] ChromaDB initialized at %s", KB_DIR)
            self._ready = True
            return True
        except Exception as exc:
            logger.error("[RAG] ChromaDB init failed: %s", exc)
            return False

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Local embeddings via sentence-transformers (no internet needed)."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[RAG] Embedder loaded: all-MiniLM-L6-v2")
        return self._embedder.encode(texts, convert_to_numpy=True).tolist()

    def add_document(self, text: str, source: str = "manual", doc_id: str = None) -> bool:
        """
        Add a document to the knowledge base.
        Splits long text into chunks of ~300 words.
        """
        if not self._init():
            return False
        try:
            chunks = _chunk_text(text, max_words=300)
            ids, docs, metas = [], [], []
            for i, chunk in enumerate(chunks):
                chunk_id = doc_id or f"{source}_{hash(chunk) & 0xFFFFFF}"
                if i > 0:
                    chunk_id = f"{chunk_id}_{i}"
                ids.append(chunk_id)
                docs.append(chunk)
                metas.append({"source": source})

            embeddings = self._embed(docs)
            self._collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
            logger.info("[RAG] Added %d chunks from source='%s'", len(chunks), source)
            return True
        except Exception as exc:
            logger.error("[RAG] add_document error: %s", exc)
            return False

    def query(self, question: str, n_results: int = 3) -> str:
        """
        Retrieve the most relevant context for a question.
        Returns a formatted context string to inject into the LLM prompt.
        """
        if not self._init():
            return ""
        try:
            emb = self._embed([question])
            results = self._collection.query(
                query_embeddings=emb,
                n_results=min(n_results, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]

            # Filter by relevance (cosine distance < 0.5 = relevant)
            relevant = [
                doc for doc, dist in zip(docs, distances)
                if dist < 0.5
            ]
            if not relevant:
                return ""

            context = "\n\n".join(f"[Context {i+1}]: {doc}" for i, doc in enumerate(relevant))
            return context
        except Exception as exc:
            logger.error("[RAG] query error: %s", exc)
            return ""

    def sync_profile(self):
        """Index the user's profile from profile_manager into the knowledge base."""
        try:
            from backend.modules.profile_manager import profile_manager
            profile = profile_manager.profile
            lines = []
            for key, val in profile.items():
                if val and val != "Unknown":
                    lines.append(f"{key}: {val}")
            if lines:
                text = "User Profile:\n" + "\n".join(lines)
                self.add_document(text, source="profile", doc_id="user_profile_v1")
                logger.info("[RAG] Synced user profile (%d fields)", len(lines))
        except Exception as exc:
            logger.error("[RAG] sync_profile error: %s", exc)

    def sync_memory(self):
        """Index recent command history into the knowledge base."""
        try:
            from backend.engine.memory_engine import memory
            history = memory.get_recent_commands(50)
            if history:
                lines = [f"Command: {h['cmd']} → Result: {h['res']}" for h in history]
                text = "Recent Interactions:\n" + "\n".join(lines)
                self.add_document(text, source="memory", doc_id="command_history_v1")
                logger.info("[RAG] Synced %d commands from memory", len(history))
        except Exception as exc:
            logger.error("[RAG] sync_memory error: %s", exc)

    def add_text_file(self, filepath: str) -> bool:
        """Index any plain text file into the knowledge base."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            source = Path(filepath).stem
            return self.add_document(text, source=source)
        except Exception as exc:
            logger.error("[RAG] add_text_file error: %s", exc)
            return False

    def count(self) -> int:
        """Returns number of documents in the knowledge base."""
        if not self._init():
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def clear(self):
        """Clear all documents from the knowledge base."""
        if not self._init():
            return
        try:
            self._client.delete_collection(COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(COLLECTION_NAME)
            logger.info("[RAG] Knowledge base cleared")
        except Exception as exc:
            logger.error("[RAG] clear error: %s", exc)


def _chunk_text(text: str, max_words: int = 300) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    step = max_words - 50  # 50-word overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks


# Global singleton
rag_engine = RAGEngine()
