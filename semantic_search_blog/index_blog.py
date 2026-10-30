#!/usr/bin/env python
"""CLI pipeline: crawl dotgroup.com.br/blog → chunk → embed → index in Milvus.

Usage:
    python index_blog.py
    python index_blog.py --max-posts 5
    python index_blog.py --reset
"""
import argparse
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from app.crawler import crawl
from app.embeddings import chunk_text, embed
from app.vector_store import FAISSStore

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index dotgroup blog into Milvus.")
    parser.add_argument("--max-posts", type=int, default=None, metavar="N",
                        help="Stop after N posts (useful for testing).")
    parser.add_argument("--reset", action="store_true",
                        help="Drop and recreate the collection before indexing.")
    args = parser.parse_args()

    store = FAISSStore()

    if args.reset:
        print("Dropping existing collection…")
        store.drop()
        store = FAISSStore()

    print("Starting blog crawl…")
    posts_ok = 0
    total_chunks = 0

    for post in crawl(max_posts=args.max_posts):
        chunks = chunk_text(post.content)
        if not chunks:
            print(f"  [SKIP] No chunks: {post.url}")
            continue

        try:
            vectors = embed(chunks)
        except Exception as exc:
            print(f"  [ERROR] Embedding failed for {post.url}: {exc}")
            continue

        records = [
            {
                "vector": vec,
                "url": post.url,
                "title": post.title[:511],
                "chunk_text": chunk[:8191],
                "chunk_index": i,
            }
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        inserted = store.insert(records)
        total_chunks += inserted
        posts_ok += 1
        print(f"  [{posts_ok}] {post.title!r} — {inserted} chunks")

    print(f"\nDone. Posts indexed: {posts_ok} | Total chunks in store: {store.count()}")


if __name__ == "__main__":
    main()
