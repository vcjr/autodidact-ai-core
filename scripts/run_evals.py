#!/usr/bin/env python3
"""
Run the curriculum eval suite against the live library.

    python scripts/run_evals.py                          # deterministic metrics only
    python scripts/run_evals.py --judge                  # + LLM-as-judge rubric
    python scripts/run_evals.py --save-baseline          # store results as the baseline
    python scripts/run_evals.py --compare                # exit 1 on regression vs baseline

Judge: set EVAL_JUDGE_PROVIDER to use a different provider than the agent (avoids
a model grading its own work).
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.curriculum_agent import CurriculumAgent  # noqa: E402
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection  # noqa: E402
from src.evals.runner import compare, load_cases, run_eval  # noqa: E402
from src.llm import get_llm  # noqa: E402
from src.retrieval import HybridRetriever, LLMReranker  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(ROOT / "evals" / "cases.jsonl"))
    ap.add_argument("--baseline", default=str(ROOT / "evals" / "baseline.json"))
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--no-rerank", action="store_true")
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--only", help="comma-separated case ids")
    args = ap.parse_args()

    collection = get_or_create_collection(get_chroma_client())
    llm = get_llm()
    retriever = HybridRetriever(collection, reranker=None if args.no_rerank else LLMReranker(llm))
    agent = CurriculumAgent(llm, retriever)

    library_urls = {m.get("source") for m in collection.get(include=["metadatas"])["metadatas"] if m.get("source")}
    cases = load_cases(args.cases)
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c.id in wanted]

    judge_llm = get_llm(os.getenv("EVAL_JUDGE_PROVIDER")) if args.judge else None
    report = run_eval(agent, cases, library_urls, judge_llm)
    report["meta"] = {"provider": llm.provider, "model": llm.model, "when": datetime.now().isoformat(timespec="seconds"),
                      "library_size": len(library_urls)}

    out_dir = ROOT / "reports" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["summary"], indent=2))
    for row in report["cases"]:
        flag = "PASS" if row["metrics"]["passed"] else "FAIL"
        print(f"  [{flag}] {row['id']:<22} calls={row['tool_calls']:<3} {row['seconds']}s {row['error'] or ''}")
    print(f"\nFull report: {out}")

    if args.save_baseline:
        Path(args.baseline).write_text(json.dumps(report, indent=2))
        print(f"Baseline saved: {args.baseline}")
    if args.compare:
        base = json.loads(Path(args.baseline).read_text())
        problems = compare(report, base)
        if problems:
            print("\nREGRESSIONS:\n  " + "\n  ".join(problems))
            return 1
        print("\nNo regressions vs baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
