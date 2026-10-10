"""
Deterministic checks for a generated curriculum.

These run inside the agent's ``submit_curriculum`` tool, so a failure goes straight
back to the model as an error it can fix - the LLM never gets to ship an invented
URL or an out-of-order path. Also reused by the eval harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Set
from urllib.parse import urlparse, urlunparse

from src.models.curriculum_schema import DIFFICULTY_RANK, Curriculum


def normalize_url(url: str) -> str:
    """Normalise for comparison: lowercase host, drop fragment and trailing slash."""
    p = urlparse(url.strip())
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", p.query, ""))


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)  # must be fixed
    warnings: List[str] = field(default_factory=list)  # worth surfacing, not blocking

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_curriculum(
    curriculum: Curriculum,
    known_urls: Iterable[str],
    *,
    max_difficulty_jump: int = 1,
) -> ValidationReport:
    report = ValidationReport()
    known: Set[str] = {normalize_url(u) for u in known_urls}

    if not curriculum.modules:
        report.errors.append("Curriculum has no modules.")
        return report

    seen_titles: List[str] = []
    prev_rank = None
    for idx, module in enumerate(curriculum.modules, 1):
        label = f"Module {idx} '{module.title}'"

        if module.title in seen_titles:
            report.errors.append(f"{label}: duplicate module title.")

        for prereq in module.prerequisites:
            if prereq not in seen_titles:
                where = "a later module" if any(m.title == prereq for m in curriculum.modules) else "no module"
                report.errors.append(
                    f"{label}: prerequisite '{prereq}' refers to {where}; "
                    "prerequisites must name EARLIER modules by exact title."
                )

        if not module.resources:
            report.errors.append(f"{label}: needs at least one resource.")
        for res in module.resources:
            if normalize_url(res.url) not in known:
                report.errors.append(
                    f"{label}: resource URL {res.url} was not returned by search_resources. "
                    "Use only URLs from search results."
                )

        if not module.objectives:
            report.errors.append(f"{label}: needs learning objectives.")

        rank = DIFFICULTY_RANK[module.difficulty]
        if prev_rank is not None:
            if rank - prev_rank > max_difficulty_jump:
                report.errors.append(
                    f"{label}: difficulty jumps too far ({module.difficulty}); "
                    "add an intermediate module or lower the level."
                )
            elif rank < prev_rank:
                report.warnings.append(f"{label}: difficulty drops back to {module.difficulty}.")
        prev_rank = rank
        seen_titles.append(module.title)

    return report
