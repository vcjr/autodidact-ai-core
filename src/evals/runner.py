"""Run eval cases against a CurriculumAgent, aggregate, and compare to a baseline."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.agents.curriculum_agent import CurriculumAgent
from src.evals.judge import judge_curriculum
from src.evals.metrics import EvalCase, score_case
from src.llm.types import LLMClient


def load_cases(path: str | Path) -> List[EvalCase]:
    cases = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(EvalCase.from_dict(json.loads(line)))
    return cases


def run_eval(
    agent: CurriculumAgent,
    cases: Iterable[EvalCase],
    library_urls: Iterable[str],
    judge_llm: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    library = list(library_urls)
    results: List[Dict[str, Any]] = []
    for case in cases:
        started = time.time()
        error = None
        try:
            outcome = agent.generate(case.query, user_level=case.user_level)
            curriculum = outcome.curriculum
            steps, tool_calls = outcome.run.steps, len(outcome.run.tool_calls)
        except Exception as exc:  # one bad case must not abort the suite
            curriculum, steps, tool_calls, error = None, 0, 0, f"{type(exc).__name__}: {exc}"
        metrics = score_case(case, curriculum, library)
        row: Dict[str, Any] = {
            "id": case.id, "metrics": metrics, "steps": steps, "tool_calls": tool_calls,
            "seconds": round(time.time() - started, 1), "error": error,
        }
        if judge_llm is not None and curriculum is not None:
            try:
                row["judge"] = judge_curriculum(judge_llm, case.query, case.user_level, curriculum).model_dump()
            except Exception as exc:
                row["judge_error"] = str(exc)
        results.append(row)
    return {"summary": summarize(results), "cases": results}


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(results) or 1
    summary: Dict[str, Any] = {
        "cases": len(results),
        "pass_rate": round(sum(r["metrics"]["passed"] for r in results) / n, 3),
        "errors": sum(1 for r in results if r["error"]),
        "avg_tool_calls": round(sum(r["tool_calls"] for r in results) / n, 1),
    }
    graded = [r["metrics"] for r in results if "grounded_url_rate" in r["metrics"]]
    if graded:
        summary["avg_grounded_url_rate"] = round(sum(m["grounded_url_rate"] for m in graded) / len(graded), 3)
        summary["avg_keyword_coverage"] = round(sum(m["keyword_coverage"] for m in graded) / len(graded), 3)
    judged = [r["judge"] for r in results if "judge" in r]
    if judged:
        for dim in ("goal_fit", "sequencing", "level_fit", "resource_choice"):
            summary[f"judge_{dim}"] = round(sum(j[dim] for j in judged) / len(judged), 2)
    return summary


def compare(current: Dict[str, Any], baseline: Dict[str, Any], tolerance: float = 0.05) -> List[str]:
    """Return regression messages (empty list = no regression). Higher is better for all gated keys."""
    regressions = []
    for key in ("pass_rate", "avg_grounded_url_rate", "avg_keyword_coverage"):
        cur, base = current["summary"].get(key), baseline["summary"].get(key)
        if cur is not None and base is not None and cur < base - tolerance:
            regressions.append(f"{key}: {cur} < baseline {base} (tolerance {tolerance})")
    return regressions
