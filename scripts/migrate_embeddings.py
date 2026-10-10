#!/usr/bin/env python3
"""
Copy a collection into a new one under a different embedding provider.

A Chroma collection is bound to the embedding model that built it, so switching
EMBEDDING_PROVIDER means re-embedding. Documents and metadata are copied as-is;
the source collection is not modified.

    python scripts/migrate_embeddings.py --to gemini            # local -> gemini
    python scripts/migrate_embeddings.py --to local --from gemini
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db_utils.chroma_client import get_chroma_client  # noqa: E402
from src.retrieval.embeddings import collection_name_for, get_embedding_function  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default="local", choices=["local", "gemini"])
    ap.add_argument("--to", dest="dst", required=True, choices=["local", "gemini"])
    ap.add_argument("--batch", type=int, default=100)
    args = ap.parse_args()
    if args.src == args.dst:
        print("Source and destination providers are the same; nothing to do.")
        return 1

    client = get_chroma_client()
    src = client.get_collection(collection_name_for(args.src), embedding_function=get_embedding_function(args.src))
    dst = client.get_or_create_collection(
        collection_name_for(args.dst),
        embedding_function=get_embedding_function(args.dst),
        metadata={"embedding_provider": args.dst},
    )
    total = src.count()
    print(f"Migrating {total} documents: {src.name} -> {dst.name}")

    for offset in range(0, total, args.batch):
        page = src.get(limit=args.batch, offset=offset, include=["documents", "metadatas"])
        if not page["ids"]:
            break
        dst.upsert(ids=page["ids"], documents=page["documents"], metadatas=page["metadatas"])
        print(f"  {min(offset + args.batch, total)}/{total}")

    ok = dst.count() == total
    print("Done." if ok else f"WARNING: destination has {dst.count()} docs, expected {total}")
    print(f"Set EMBEDDING_PROVIDER={args.dst} to use the new collection.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
