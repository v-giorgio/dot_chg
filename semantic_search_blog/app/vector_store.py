import json
import logging
import os
from pathlib import Path

import faiss
import numpy as np

from .embeddings import EMBEDDING_DIM

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_INDEX = str(_ROOT / "blog_index.faiss")
_DEFAULT_META = str(_ROOT / "blog_meta.json")


class FAISSStore:
    """Vector store backed by FAISS (IndexFlatIP + L2 norm = cosine similarity).

    Metadata (url, title, chunk_text, chunk_index) is persisted alongside the
    FAISS index in a JSON file, keyed by insertion order.
    """

    def __init__(
        self,
        index_path: str | None = None,
        meta_path: str | None = None,
    ):
        self._index_path = index_path or os.getenv("FAISS_INDEX_PATH", _DEFAULT_INDEX)
        self._meta_path = meta_path or os.getenv("FAISS_META_PATH", _DEFAULT_META)
        self._load_or_create()

    def _load_or_create(self) -> None:
        if os.path.exists(self._index_path) and os.path.exists(self._meta_path):
            self._index = faiss.read_index(self._index_path)
            with open(self._meta_path, encoding="utf-8") as f:
                self._meta: list[dict] = json.load(f)
            logger.info("FAISS index loaded: %d vectors", self._index.ntotal)
        else:
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._meta = []
            logger.info("FAISS index created (empty).")

    def _save(self) -> None:
        faiss.write_index(self._index, self._index_path)
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False)

    def insert(self, records: list[dict]) -> int:
        vectors = np.array([r["vector"] for r in records], dtype="float32")
        faiss.normalize_L2(vectors)
        self._index.add(vectors)
        for r in records:
            self._meta.append({
                "url": r["url"],
                "title": r["title"],
                "chunk_text": r["chunk_text"],
                "chunk_index": r["chunk_index"],
            })
        self._save()
        return len(records)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        vec = np.array([query_vector], dtype="float32")
        faiss.normalize_L2(vec)
        scores, indices = self._index.search(vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self._meta[idx]
            results.append({
                "score": round(float(score), 4),
                "url": meta["url"],
                "title": meta["title"],
                "chunk": meta["chunk_text"],
                "chunk_index": meta["chunk_index"],
            })
        return results

    def count(self) -> int:
        return self._index.ntotal

    def drop(self) -> None:
        self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self._meta = []
        self._save()
        logger.info("FAISS index cleared.")
