"""
Hybrid retrieval: BM25 (exact terms, names, jargon) + vector search (meaning),
fused with Reciprocal Rank Fusion, optionally reranked by an LLM.

Works against any object exposing the Chroma collection methods we use
(``get``, ``query``, ``count``), which keeps it unit-testable without a server.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
_STOP = frozenset(
    "a an and are as at be but by for from has have how i in is it its of on or that the "
    "this to was what when where which who will with you your can do does not so if into "
    "about than then them they we our".split()
)


def tokenize(text: str) -> List[str]:
    return [t.strip(".-") for t in _TOKEN.findall(text.lower()) if t.strip(".-") and t not in _STOP]


@dataclass
class Hit:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    # per-retriever rank (1-based) for debugging / eval
    ranks: Dict[str, int] = field(default_factory=dict)

    @property
    def url(self) -> str:
        return str(self.metadata.get("source") or self.metadata.get("url") or "")

    @property
    def title(self) -> str:
        return str(self.metadata.get("title") or self.url or self.id)


class BM25Index:
    """Small in-memory Okapi BM25. Good for tens of thousands of documents."""

    def __init__(self, ids: Sequence[str], texts: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.ids = list(ids)
        self.k1, self.b = k1, b
        self._tf: List[Counter] = [Counter(tokenize(t)) for t in texts]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 0.0
        df: Counter = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self._tf)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 20) -> List[Tuple[str, float]]:
        terms = [t for t in tokenize(query) if t in self._idf]
        if not terms:
            return []
        scored: List[Tuple[str, float]] = []
        for doc_id, tf, dl in zip(self.ids, self._tf, self._len):
            s = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if not f:
                    continue
                norm = f + self.k1 * (1 - self.b + self.b * dl / (self._avg or 1))
                s += self._idf[t] * f * (self.k1 + 1) / norm
            if s > 0:
                scored.append((doc_id, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


def rrf(rank_lists: Sequence[Sequence[str]], k: int = 60) -> Dict[str, float]:
    """Reciprocal Rank Fusion: score = sum(1 / (k + rank))."""
    fused: Dict[str, float] = {}
    for ranking in rank_lists:
        for rank, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    return fused


def build_where(
    domain_id: Optional[str] = None,
    subdomain_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_quality: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Build a Chroma ``where`` filter. Returns None when there are no conditions."""
    conds: List[Dict[str, Any]] = []
    if domain_id:
        conds.append({"domain_id": domain_id.upper()})
    if subdomain_id:
        conds.append({"subdomain_id": subdomain_id.upper()})
    if difficulty:
        conds.append({"difficulty": difficulty.lower()})
    if min_quality is not None:
        conds.append({"helpfulness_score": {"$gte": float(min_quality)}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def best_excerpt(text: str, query: str, max_chars: int = 900) -> str:
    """Return the window of ``text`` densest in query terms (cheap passage selection)."""
    if len(text) <= max_chars:
        return text
    terms = set(tokenize(query))
    if not terms:
        return text[:max_chars]
    step = max(max_chars // 3, 1)
    best_start, best_score = 0, -1
    for start in range(0, len(text) - max_chars + step, step):
        window = text[start : start + max_chars].lower()
        score = sum(window.count(t) for t in terms)
        if score > best_score:
            best_start, best_score = start, score
    chunk = text[best_start : best_start + max_chars]
    return ("…" if best_start else "") + chunk + ("…" if best_start + max_chars < len(text) else "")


class HybridRetriever:
    def __init__(self, collection: Any, reranker: Any = None, rrf_k: int = 60):
        self.collection = collection
        self.reranker = reranker
        self.rrf_k = rrf_k
        self._bm25_cache: Dict[str, Tuple[BM25Index, Dict[str, Hit]]] = {}

    def _bm25_for(self, where: Optional[Dict[str, Any]]) -> Tuple[BM25Index, Dict[str, Hit]]:
        key = f"{self.collection.count()}|{json.dumps(where, sort_keys=True, default=str)}"
        if key not in self._bm25_cache:
            if len(self._bm25_cache) > 32:
                self._bm25_cache.clear()
            data = self.collection.get(where=where, include=["documents", "metadatas"])
            ids = data.get("ids") or []
            docs = data.get("documents") or []
            metas = data.get("metadatas") or [{}] * len(ids)
            hits = {i: Hit(id=i, text=d or "", metadata=m or {}) for i, d, m in zip(ids, docs, metas)}
            self._bm25_cache[key] = (BM25Index(ids, [h.text for h in hits.values()]), hits)
        return self._bm25_cache[key]

    def search(
        self,
        query: str,
        *,
        where: Optional[Dict[str, Any]] = None,
        k: int = 8,
        pool: int = 40,
        rerank: bool = True,
    ) -> List[Hit]:
        by_id: Dict[str, Hit] = {}

        # Vector leg
        vec_ids: List[str] = []
        res = self.collection.query(
            query_texts=[query],
            n_results=pool,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        for i, d, m in zip(
            (res.get("ids") or [[]])[0],
            (res.get("documents") or [[]])[0],
            (res.get("metadatas") or [[]])[0],
        ):
            vec_ids.append(i)
            by_id[i] = Hit(id=i, text=d or "", metadata=m or {})

        # Keyword leg
        index, corpus = self._bm25_for(where)
        bm_ids = [i for i, _ in index.search(query, k=pool)]
        for i in bm_ids:
            by_id.setdefault(i, corpus[i])

        fused = rrf([vec_ids, bm_ids], k=self.rrf_k)
        for rank, i in enumerate(vec_ids, 1):
            by_id[i].ranks["vector"] = rank
        for rank, i in enumerate(bm_ids, 1):
            by_id[i].ranks["bm25"] = rank
        ordered = sorted(by_id.values(), key=lambda h: fused[h.id], reverse=True)
        for h in ordered:
            h.score = fused[h.id]

        if rerank and self.reranker is not None and len(ordered) > 1:
            return self.reranker.rerank(query, ordered[:pool], top_n=k)
        return ordered[:k]
