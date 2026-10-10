import json

from src.agents.curriculum_agent import CurriculumAgent
from src.evals.metrics import EvalCase, score_case
from src.evals.runner import compare, load_cases, run_eval
from src.models.curriculum_schema import Curriculum
from src.retrieval import HybridRetriever
from tests.fakes import ScriptedLLM, make_corpus
from tests.unit.test_curriculum_agent import curriculum, module

LIB = ["https://youtube.com/watch?v=v1", "https://youtube.com/watch?v=v3"]


def cur(*mods):
    return Curriculum.model_validate(curriculum(*mods))


def test_score_case_passes_good_curriculum():
    case = EvalCase(id="x", query="q", must_cover=["basics", "scales"])
    c = cur(module("Basics"), module("Scales", "intermediate", ["Basics"], [LIB[1]]))
    m = score_case(case, c, LIB)
    assert m["passed"] and m["grounded_url_rate"] == 1.0 and m["keyword_coverage"] == 1.0


def test_score_case_catches_ungrounded_and_missing_coverage():
    case = EvalCase(id="x", query="q", must_cover=["jazz", "blues"])
    c = cur(module("Basics", urls=["https://fake.example/v"]), module("More", prereqs=["Basics"], urls=["https://fake.example/w"]))
    m = score_case(case, c, LIB)
    assert not m["passed"] and m["grounded_url_rate"] == 0.0 and m["keyword_coverage"] == 0.0


def test_expect_refusal_inverts_success():
    case = EvalCase(id="x", query="q", expect_refusal=True)
    assert score_case(case, None, LIB)["passed"]
    assert not score_case(case, cur(module("Basics"), module("More", prereqs=["Basics"])), LIB)["passed"]
    assert not score_case(EvalCase(id="y", query="q"), None, LIB)["passed"]


def test_cases_file_loads_and_is_wellformed():
    cases = load_cases("evals/cases.jsonl")
    assert len(cases) >= 10 and len({c.id for c in cases}) == len(cases)
    assert any(c.expect_refusal for c in cases)


def test_run_eval_end_to_end_and_compare():
    good = [("search_resources", {"query": "piano"}), ("submit_curriculum", {"curriculum": curriculum(
        module("Basics"), module("More", prereqs=["Basics"]))})]

    class Boom(ScriptedLLM):
        def run_agent(self, *a, **k):
            raise RuntimeError("provider down")

    agent = CurriculumAgent(ScriptedLLM(good), HybridRetriever(make_corpus()))
    cases = [EvalCase(id="ok", query="learn piano"), EvalCase(id="decline", query="underwater", expect_refusal=True)]
    report = run_eval(agent, cases[:1], LIB)
    assert report["summary"]["pass_rate"] == 1.0 and report["cases"][0]["tool_calls"] == 2

    crashed = run_eval(CurriculumAgent(Boom(), HybridRetriever(make_corpus())), cases[:1], LIB)
    assert crashed["summary"]["errors"] == 1 and crashed["summary"]["pass_rate"] == 0.0

    assert compare(crashed, report) and not compare(report, report)
