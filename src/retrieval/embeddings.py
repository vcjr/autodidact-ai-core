"""
Embedding providers for ChromaDB.

- ``local``  sentence-transformers all-mpnet-base-v2 (768d). Requires the heavy
             ``sentence-transformers``/``torch`` stack. Kept as the default so existing
             collections keep working.
- ``gemini`` Gemini embeddings via ``google-genai`` (no local model, no torch).

A collection is bound to the embedding model that built it, so every provider gets
its own collection name (see ``collection_name_for``). Move data between them with
``scripts/migrate_embeddings.py``.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
from chromadb import Documents, EmbeddingFunction, Embeddings

LEGACY_COLLECTION = "autodidact_ai_core_v2"  # local mpnet, 768d
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_DIMENSIONS = 768
_BATCH = 100


class GeminiEmbeddingFunction(EmbeddingFunction[Documents]):
    """Chroma embedding function backed by Gemini embeddings."""

    def __init__(
        self,
        model: str = GEMINI_EMBEDDING_MODEL,
        dimensions: int = GEMINI_DIMENSIONS,
        client: Optional[Any] = None,
    ):
        self.model = model
        self.dimensions = dimensions
        if client is None:
            from google import genai

            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.client = client

    def _embed(self, texts: List[str], task_type: str) -> Embeddings:
        from google.genai import types

        vectors: List[np.ndarray] = []
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            result = self.client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=self.dimensions
                ),
            )
            for emb in result.embeddings:
                vec = np.asarray(emb.values, dtype=np.float32)
                # Truncated (<3072d) Gemini embeddings are not unit-length; normalise.
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm else vec)
        return vectors

    def __call__(self, input: Documents) -> Embeddings:
        return self._embed(list(input), "RETRIEVAL_DOCUMENT")

    def embed_query(self, input: Documents) -> Embeddings:
        return self._embed(list(input), "RETRIEVAL_QUERY")

    @staticmethod
    def name() -> str:
        return "autodidact_gemini"

    def get_config(self) -> Dict[str, Any]:
        return {"model": self.model, "dimensions": self.dimensions}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "GeminiEmbeddingFunction":
        return GeminiEmbeddingFunction(config["model"], config["dimensions"])

    def default_space(self):  # type: ignore[override]
        return "cosine"

    def supported_spaces(self):  # type: ignore[override]
        return ["cosine", "l2", "ip"]


def embedding_provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "local").lower()


def collection_name_for(provider: Optional[str] = None) -> str:
    provider = (provider or embedding_provider()).lower()
    if provider == "local":
        return LEGACY_COLLECTION
    if provider == "gemini":
        return f"autodidact_ai_core_v3_gemini_{GEMINI_DIMENSIONS}"
    raise ValueError(f"Unknown EMBEDDING_PROVIDER '{provider}' (expected 'local' or 'gemini')")


def get_embedding_function(provider: Optional[str] = None):
    provider = (provider or embedding_provider()).lower()
    if provider == "local":
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-mpnet-base-v2", device="cpu"
        )
    if provider == "gemini":
        return GeminiEmbeddingFunction()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER '{provider}' (expected 'local' or 'gemini')")
