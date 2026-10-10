"""Lazily-built singletons for the v3 API. Overridable in tests via FastAPI dependency_overrides."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from src.agents.curriculum_agent import CurriculumAgent
from src.agents.tutor_agent import TutorAgent
from src.llm import LLMClient, get_llm
from src.retrieval import HybridRetriever, LLMReranker

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def llm() -> LLMClient:
    return get_llm()


@lru_cache(maxsize=1)
def retriever() -> HybridRetriever:
    from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection

    collection = get_or_create_collection(get_chroma_client())
    reranker = None if os.getenv("RERANK", "1") == "0" else LLMReranker(llm())
    return HybridRetriever(collection, reranker=reranker)


@lru_cache(maxsize=1)
def curriculum_agent() -> CurriculumAgent:
    graph = None
    try:
        from src.knowledge_graph.concept_graph import ConceptGraph

        candidate = ConceptGraph()
        graph = candidate if candidate.load_cache() else None
    except Exception as exc:  # the graph is an optional enhancement
        log.warning("Concept graph unavailable: %s", exc)
    return CurriculumAgent(llm(), retriever(), concept_graph=graph)


@lru_cache(maxsize=1)
def tutor_agent() -> TutorAgent:
    return TutorAgent(llm(), retriever())
