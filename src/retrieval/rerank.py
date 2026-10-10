"""LLM reranking of retrieval candidates (biggest relevance win after hybrid search)."""

from __future__ import annotations

import logging
from typing import List

from pydantic import BaseModel, Field

from src.llm.types import LLMClient
from src.retrieval.hybrid import Hit, best_excerpt

log = logging.getLogger(__name__)


class RankedItem(BaseModel):
    id: str
    relevance: int = Field(description="0 (irrelevant) to 10 (exactly what the learner needs)")
    reason: str = Field(description="One short sentence")


class Ranking(BaseModel):
    ranked: List[RankedItem]


SYSTEM = (
    "You rank learning resources for relevance to a learner's search. Prefer resources that "
    "teach the requested topic directly and clearly at the stated level over resources that "
    "merely mention it. Return every candidate id you were given exactly once."
)


class LLMReranker:
    def __init__(self, llm: LLMClient, excerpt_chars: int = 700, min_relevance: int = 0):
        self.llm = llm
        self.excerpt_chars = excerpt_chars
        self.min_relevance = min_relevance

    def rerank(self, query: str, hits: List[Hit], top_n: int = 8) -> List[Hit]:
        if len(hits) <= 1:
            return hits[:top_n]
        candidates = "\n\n".join(
            f"[id={h.id}] {h.title}\n"
            f"difficulty={h.metadata.get('difficulty', '?')} platform={h.metadata.get('platform', '?')}\n"
            f"{best_excerpt(h.text, query, self.excerpt_chars)}"
            for h in hits
        )
        prompt = f"Search: {query}\n\nCandidates:\n\n{candidates}"
        try:
            ranking = self.llm.structured(prompt, Ranking, system=SYSTEM, max_tokens=4096)
        except Exception as exc:  # never let rerank break retrieval
            log.warning("Rerank failed (%s); keeping fused order", exc)
            return hits[:top_n]

        by_id = {h.id: h for h in hits}
        scored = {}
        for item in ranking.ranked:
            if item.id in by_id and item.id not in scored:
                scored[item.id] = item.relevance
        if not scored:
            return hits[:top_n]
        # Stable: LLM relevance first, fused order breaks ties; unscored hits go last.
        order = {h.id: n for n, h in enumerate(hits)}
        final = sorted(hits, key=lambda h: (-scored.get(h.id, -1), order[h.id]))
        final = [h for h in final if scored.get(h.id, -1) >= self.min_relevance]
        for h in final:
            h.ranks["rerank"] = scored.get(h.id, -1)
        return final[:top_n]
