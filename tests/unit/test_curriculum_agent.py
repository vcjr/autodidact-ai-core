import pytest

from src.agents.curriculum_agent import CurriculumAgent
from src.agents.curriculum_validation import normalize_url, validate_curriculum
from src.models.curriculum_schema import Curriculum
from src.retrieval import HybridRetriever
from tests.fakes import ScriptedLLM, make_corpus


def module(title, diff="beginner", prereqs=(), urls=("https://youtube.com/watch?v=v1",), hours=3):
    return {
        "title": title, "difficulty": diff, "estimated_hours": hours, "prerequisites": list(prereqs),
        "objectives": ["do the thing"], "practice": "play it",
        "resources": [{"title": "r", "url": u, "why": "fits"} for u in urls],
        "why_it_matters": "next step",
    }


def curriculum(*modules):
    return {"title": "T", "goal": "G", "overview": "O", "modules": list(modules), "next_steps": "N"}


KNOWN = ["https://youtube.com/watch?v=v1", "https://youtube.com/watch?v=v3"]


def test_normalize_url():
    assert normalize_url("HTTPS://YouTube.com/watch?v=a#t=5") == normalize_url("https://youtube.com/watch?v=a")
    assert normalize_url("https://x.com/p/") == "https://x.com/p"


def test_validator_accepts_good_path():
    c = Curriculum.model_validate(curriculum(
        module("Basics"),
        module("Scales", "intermediate", ["Basics"], ["https://youtube.com/watch?v=v3"]),
    ))
    assert validate_curriculum(c, KNOWN).ok


def test_validator_flags_each_failure_mode():
    c = Curriculum.model_validate(curriculum(
        module("A", urls=["https://made.up/video"]),
        module("B", "advanced", ["Z"]),          # jump + unknown prereq
        module("B", "intermediate", ["C"]),      # duplicate title + later prereq
        module("C"),
    ))
    errors = " | ".join(validate_curriculum(c, KNOWN).errors)
    for needle in ["not returned by search_resources", "jumps too far", "prerequisite 'Z'", "duplicate", "later module"]:
        assert needle in errors


def test_validator_warns_on_difficulty_drop_but_passes():
    c = Curriculum.model_validate(curriculum(module("A", "intermediate", urls=KNOWN[:1]), module("B", "beginner", ["A"])))
    report = validate_curriculum(c, KNOWN)
    assert report.ok and report.warnings


def run(script):
    llm = ScriptedLLM(script)
    agent = CurriculumAgent(llm, HybridRetriever(make_corpus()))
    events = []
    return agent.generate("learn piano", on_event=events.append), events


def test_agent_searches_then_submits_valid_curriculum():
    result, events = run([
        ("search_resources", {"query": "piano basics", "domain_id": "MUSIC", "subdomain_id": "PIANO"}),
        ("submit_curriculum", {"curriculum": curriculum(module("Basics"))}),
    ])
    assert result.ok and result.run.stopped_by == "terminal_tool"
    assert result.to_markdown().startswith("# T")
    assert [e["type"] for e in events][:2] == ["tool_call", "tool_result"]


def test_agent_rejects_ungrounded_url_then_accepts_fix():
    bad = ("submit_curriculum", {"curriculum": curriculum(module("Basics", urls=["https://youtube.com/watch?v=INVENTED"]))})
    good = ("submit_curriculum", {"curriculum": curriculum(module("Basics"))})
    result, _ = run([("search_resources", {"query": "piano basics"}), bad, good])
    assert result.ok
    first_submit = [c for c in result.run.tool_calls if c.name == "submit_curriculum"][0]
    assert first_submit.is_error and "not returned by search_resources" in first_submit.output


def test_agent_cannot_cite_urls_without_searching():
    result, _ = run([("submit_curriculum", {"curriculum": curriculum(module("Basics"))})])
    assert not result.ok and "Could not produce" in result.to_markdown()


def test_agent_schema_errors_are_actionable():
    result, _ = run([("submit_curriculum", {"curriculum": {"title": "x"}})])
    assert not result.ok
    assert "Schema errors" in result.run.tool_calls[0].output


def test_empty_search_hints_to_loosen_filters():
    result, _ = run([("search_resources", {"query": "zzzz", "difficulty": "expert", "subdomain_id": "OBOE"})])
    assert "Loosen filters" in result.run.tool_calls[0].output


def test_get_prerequisites_without_graph_is_a_recoverable_error():
    result, _ = run([("get_prerequisites", {"domain_id": "MUSIC", "subdomain_id": "PIANO", "difficulty": "advanced"})])
    assert result.run.tool_calls[0].is_error


def test_submit_schema_has_hoisted_defs():
    from src.agents.curriculum_agent import _submit_schema
    s = _submit_schema()
    assert "$defs" in s and "$defs" not in s["properties"]["curriculum"]
