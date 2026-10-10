"""
Deterministic metrics for a generated curriculum. No LLM involved, so they are
cheap, reproducible and safe to gate CI on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.agents.curriculum_validation import normalize_url, validate_curriculum
from src.models.curriculum_schema import Curriculum


@dataclass
class EvalCase:
    id: str
    query: str
    user_level: Optional[str] = None
    # expectations (all optional)
    min_modules: int = 2
    max_modules: int = 12
    must_cover: List[str] = field(default_factory=list)  # keywords expected somewhere in the path
    expect_refusal: bool = False  # topic the library does NOT cover: agent should say so, not invent

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvalCase":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _text_of(curriculum: Curriculum) -> str:
    parts = [curriculum.title, curriculum.goal, curriculum.overview]
    for m in curriculum.modules:
        parts += [m.title, m.practice, *m.objectives]
    return " ".join(parts).lower()


def score_case(
    case: EvalCase,
    curriculum: Optional[Curriculum],
    library_urls: Iterable[str],
) -> Dict[str, Any]:
    """
    Returns metric name -> value (bool or float 0..1). ``passed`` is the AND of the
    hard checks. For ``expect_refusal`` cases, success means *no* curriculum.
    """
    if case.expect_refusal:
        ok = curriculum is None
        return {"produced_curriculum": curriculum is not None, "correctly_declined": ok, "passed": ok}

    if curriculum is None:
        return {"produced_curriculum": False, "passed": False}

    library = {normalize_url(u) for u in library_urls}
    urls = [r.url for m in curriculum.modules for r in m.resources]
    grounded = sum(normalize_url(u) in library for u in urls) / len(urls) if urls else 0.0
    report = validate_curriculum(curriculum, library)  # independent re-check against the WHOLE library
    text = _text_of(curriculum)
    coverage = (
        sum(k.lower() in text for k in case.must_cover) / len(case.must_cover) if case.must_cover else 1.0
    )
    in_range = case.min_modules <= len(curriculum.modules) <= case.max_modules

    metrics: Dict[str, Any] = {
        "produced_curriculum": True,
        "grounded_url_rate": round(grounded, 3),
        "validator_ok": report.ok,
        "validator_errors": len(report.errors),
        "module_count_in_range": in_range,
        "keyword_coverage": round(coverage, 3),
        "total_hours": curriculum.total_hours,
    }
    metrics["passed"] = bool(grounded == 1.0 and report.ok and in_range and coverage >= 0.5)
    return metrics
