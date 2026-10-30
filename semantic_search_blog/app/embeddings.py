import logging
import os

import ollama

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBEDDING_DIM = 768   # nomic-embed-text output dimension
CHUNK_SIZE = 900      # characters
CHUNK_OVERLAP = 120   # characters


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level windows."""
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    """Return one embedding per text using Ollama (local, no API cost)."""
    if not texts:
        return []
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    logger.info("Embedding %d chunks via Ollama model '%s'", len(texts), EMBEDDING_MODEL)
    response = client.embed(model=EMBEDDING_MODEL, input=texts)
    return response.embeddings
