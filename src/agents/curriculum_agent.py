"""
CurriculumAgent - agentic curriculum generation.

Replaces the fixed Intake -> Scope -> Retrieve -> Generate pipeline. The model is
given tools and decides what to look up, in what order, and when it has enough:

    list_domains         what subjects the library covers
    search_resources     hybrid (BM25 + vector) search, LLM-reranked, filterable
    get_prerequisites    concept-graph neighbours for a domain/subdomain/level
    submit_curriculum    terminal tool; validates and bounces errors back to the model

The final curriculum is validated deterministically (grounded URLs, prerequisite
order, sane difficulty progression) before it is accepted.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from src.agents.curriculum_validation import ValidationReport, normalize_url, validate_curriculum
from src.llm.types import AgentRun, EventCallback, LLMClient, Tool, ToolError
from src.models.curriculum_schema import Curriculum
from src.retrieval.hybrid import HybridRetriever, best_excerpt, build_where

log = logging.getLogger(__name__)

DOMAINS_FILE = Path(__file__).resolve().parents[2] / "data" / "domains_with_subdomains.json"

SYSTEM_PROMPT = """\
You are the Autodidact curriculum designer. You build personalised learning paths for \
self-directed learners, using ONLY resources from the Autodidact library (via tools).

How to work:
1. Work out what the learner wants, their current level, and their constraints. If they gave \
no level, assume a beginner unless the request implies otherwise.
2. Use list_domains if you are unsure how the library is organised, then search_resources \
repeatedly - different angles, different levels. If a filtered search is empty, loosen the \
filters (drop difficulty, then subdomain) rather than giving up.
3. Order modules by true prerequisites: each module should only need things taught earlier. \
Move up one difficulty level at a time.
4. Choose resources for how well they teach, not just keyword match. Prefer 1-3 strong \
resources per module over many weak ones.
5. When the path is ready, call submit_curriculum. If it returns errors, fix exactly those \
and submit again.

Hard rules:
- Every resource URL must come from a search_resources result in this session. Never invent \
or modify URLs.
- If the library lacks material for part of the goal, say so in the overview and cover only \
what you can ground - do not fill gaps from memory.
- Estimated hours must be realistic and include practice time.
"""


def _submit_schema() -> Dict[str, Any]:
    """Tool input schema wrapping the Curriculum model, with $defs hoisted to the root."""
    inner = Curriculum.model_json_schema()
    defs = inner.pop("$defs", {})
    return {
        "type": "object",
        "properties": {"curriculum": inner},
        "required": ["curriculum"],
        "$defs": defs,
    }


class CurriculumResult:
    """Outcome of one agent run."""

    def __init__(self, curriculum: Optional[Curriculum], run: AgentRun, report: Optional[ValidationReport]):
        self.curriculum = curriculum
        self.run = run
        self.report = report

    @property
    def ok(self) -> bool:
        return self.curriculum is not None

    def to_markdown(self) -> str:
        if self.curriculum is None:
            return (
                "Could not produce a validated curriculum from the current library.\n\n"
                + (self.run.text or "")
            )
        md = self.curriculum.to_markdown()
        if self.report and self.report.warnings:
            md += "\n\n> Notes: " + " ".join(self.report.warnings)
        return md


class CurriculumAgent:
    def __init__(
        self,
        llm: LLMClient,
        retriever: HybridRetriever,
        concept_graph: Any = None,
        max_steps: int = 14,
    ):
        self.llm = llm
        self.retriever = retriever
        self.concept_graph = concept_graph
        self.max_steps = max_steps

    # ------------------------------------------------------------------ tools
    def _build_tools(self, state: Dict[str, Any]) -> List[Tool]:
        known_urls: Dict[str, str] = state["known_urls"]  # normalized -> original

        def list_domains(_: Dict[str, Any]) -> Any:
            try:
                data = json.loads(DOMAINS_FILE.read_text())
            except Exception as exc:
                raise ToolError(f"Domain list unavailable: {exc}")
            return data

        def search_resources(args: Dict[str, Any]) -> Any:
            query = str(args.get("query", "")).strip()
            if not query:
                raise ToolError("'query' is required")
            where = build_where(
                args.get("domain_id"),
                args.get("subdomain_id"),
                args.get("difficulty"),
                args.get("min_quality"),
            )
            k = max(1, min(int(args.get("k", 6)), 10))
            hits = self.retriever.search(query, where=where, k=k)
            out = []
            for h in hits:
                if h.url:
                    known_urls[normalize_url(h.url)] = h.url
                out.append(
                    {
                        "title": h.title,
                        "url": h.url,
                        "domain": h.metadata.get("domain_id"),
                        "subdomain": h.metadata.get("subdomain_id"),
                        "difficulty": h.metadata.get("difficulty"),
                        "quality": h.metadata.get("helpfulness_score"),
                        "excerpt": best_excerpt(h.text, query, 600),
                    }
                )
            if not out:
                return {"results": [], "hint": "No matches. Loosen filters (drop difficulty/subdomain) or rephrase."}
            return {"results": out}

        def get_prerequisites(args: Dict[str, Any]) -> Any:
            if self.concept_graph is None:
                raise ToolError("Concept graph not available; infer prerequisites from search results.")
            domain, sub, diff = (str(args.get(k, "")) for k in ("domain_id", "subdomain_id", "difficulty"))
            concept_id = f"{domain.upper()}_{sub.upper()}_{diff.lower()}"
            try:
                path = self.concept_graph.find_learning_path(target_concept=concept_id)
            except Exception as exc:
                raise ToolError(f"No graph path for {concept_id}: {exc}")
            if not path:
                raise ToolError(f"No graph path for {concept_id}.")
            return {"target": concept_id, "learning_path": path}

        def submit_curriculum(args: Dict[str, Any]) -> Any:
            payload = args.get("curriculum", args)
            try:
                curriculum = Curriculum.model_validate(payload)
            except ValidationError as exc:
                raise ToolError("Schema errors:\n" + "\n".join(
                    f"- {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:12]
                ))
            report = validate_curriculum(curriculum, known_urls.keys())
            if not report.ok:
                raise ToolError(
                    "Curriculum rejected. Fix these and call submit_curriculum again:\n"
                    + "\n".join(f"- {e}" for e in report.errors)
                )
            state["curriculum"], state["report"] = curriculum, report
            return {"status": "accepted", "modules": len(curriculum.modules), "warnings": report.warnings}

        return [
            Tool(
                "list_domains",
                "List the subject domains and subdomains available in the library, with their ids.",
                {"type": "object", "properties": {}, "additionalProperties": False},
                list_domains,
            ),
            Tool(
                "search_resources",
                "Search the library for learning resources (videos, articles, discussions). Hybrid "
                "keyword+semantic search. Filters are optional; ids are uppercase (e.g. MUSIC / PIANO), "
                "difficulty is lowercase.",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to find, in natural language"},
                        "domain_id": {"type": "string"},
                        "subdomain_id": {"type": "string"},
                        "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced", "expert"]},
                        "min_quality": {"type": "number", "description": "Minimum helpfulness score 0-1"},
                        "k": {"type": "integer", "description": "Results to return (1-10, default 6)"},
                    },
                    "required": ["query"],
                },
                search_resources,
            ),
            Tool(
                "get_prerequisites",
                "Ask the concept graph for the ordered prerequisite path leading to a domain/subdomain/difficulty.",
                {
                    "type": "object",
                    "properties": {
                        "domain_id": {"type": "string"},
                        "subdomain_id": {"type": "string"},
                        "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced", "expert"]},
                    },
                    "required": ["domain_id", "subdomain_id", "difficulty"],
                },
                get_prerequisites,
            ),
            Tool(
                "submit_curriculum",
                "Submit the finished curriculum. It is validated; on errors fix them and resubmit.",
                _submit_schema(),
                submit_curriculum,
                terminal=True,
            ),
        ]

    # -------------------------------------------------------------------- run
    def generate(
        self,
        query: str,
        *,
        user_level: Optional[str] = None,
        learner_context: Optional[str] = None,
        on_event: Optional[EventCallback] = None,
    ) -> CurriculumResult:
        state: Dict[str, Any] = {"known_urls": {}, "curriculum": None, "report": None}
        tools = self._build_tools(state)

        prompt = f"Learner request: {query}"
        if user_level:
            prompt += f"\nSelf-reported level: {user_level}"
        if learner_context:
            prompt += f"\nWhat we know about the learner:\n{learner_context}"

        run = self.llm.run_agent(
            prompt, tools, system=SYSTEM_PROMPT, max_steps=self.max_steps, on_event=on_event
        )
        return CurriculumResult(state["curriculum"], run, state["report"])
