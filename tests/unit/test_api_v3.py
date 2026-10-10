import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agents.curriculum_agent import CurriculumAgent
from src.agents.tutor_agent import Citation, TutorAgent, TutorReply
from src.api import deps
from src.api.v3 import router
from src.llm import LLMRefusal
from src.retrieval import HybridRetriever
from tests.fakes import ScriptedLLM, make_corpus
from tests.unit.test_curriculum_agent import curriculum, module

GOOD = [
    ("search_resources", {"query": "piano"}),
    ("submit_curriculum", {"curriculum": curriculum(module("Basics"))}),
]


def client_with(llm: ScriptedLLM):
    app = FastAPI()
    app.include_router(router)
    retriever = HybridRetriever(make_corpus())
    app.dependency_overrides[deps.llm] = lambda: llm
    app.dependency_overrides[deps.retriever] = lambda: retriever
    app.dependency_overrides[deps.curriculum_agent] = lambda: CurriculumAgent(llm, retriever)
    app.dependency_overrides[deps.tutor_agent] = lambda: TutorAgent(llm, retriever)
    return TestClient(app)


def test_curriculum_ok():
    r = client_with(ScriptedLLM(GOOD)).post("/v3/curriculum", json={"query": "learn piano", "user_level": "beginner"})
    assert r.status_code == 200
    body = r.json()
    assert body["curriculum"]["modules"][0]["title"] == "Basics"
    assert body["markdown"].startswith("# T") and body["tool_calls"] == 2


def test_curriculum_unvalidated_is_422_not_500():
    llm = ScriptedLLM([("submit_curriculum", {"curriculum": curriculum(module("Basics"))})])  # never searched
    r = client_with(llm).post("/v3/curriculum", json={"query": "learn piano"})
    assert r.status_code == 422


def test_request_validation():
    c = client_with(ScriptedLLM())
    assert c.post("/v3/curriculum", json={"query": "x"}).status_code == 422
    assert c.post("/v3/study/review", json={"rating": 9}).status_code == 422


def test_stream_emits_progress_then_result():
    r = client_with(ScriptedLLM(GOOD)).post("/v3/curriculum/stream", json={"query": "learn piano"})
    assert r.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types[0] == "tool_call" and types[-1] == "result" and "tool_result" in types
    assert events[-1]["curriculum"]["modules"]


def test_stream_reports_failures_as_error_event_without_leaking_details():
    class Boom(ScriptedLLM):
        def run_agent(self, *a, **k):
            raise RuntimeError("secret internal detail")

    r = client_with(Boom()).post("/v3/curriculum/stream", json={"query": "learn piano"})
    last = json.loads([l for l in r.text.splitlines() if l.startswith("data: ")][-1][6:])
    assert last["type"] == "error" and "secret" not in last["message"]


def test_refusal_maps_to_422_and_provider_failure_to_502():
    class Refuse(ScriptedLLM):
        def run_agent(self, *a, **k):
            raise LLMRefusal("no")

    class Down(ScriptedLLM):
        def run_agent(self, *a, **k):
            raise __import__("src.llm", fromlist=["LLMError"]).LLMError("upstream 500 with internals")

    assert client_with(Refuse()).post("/v3/curriculum", json={"query": "learn piano"}).status_code == 422
    r = client_with(Down()).post("/v3/curriculum", json={"query": "learn piano"})
    assert r.status_code == 502 and "internals" not in r.text


def test_tutor_returns_verified_citations_only():
    llm = ScriptedLLM(structured_queue=[TutorReply(answer="a", citations=[
        Citation(url="https://youtube.com/watch?v=v1", quote="learn piano basics"),
        Citation(url="https://youtube.com/watch?v=v1", quote="invented"),
    ])])
    r = client_with(llm).post("/v3/tutor", json={"question": "hi", "lesson_url": "https://youtube.com/watch?v=v1"})
    body = r.json()
    assert r.status_code == 200 and len(body["citations"]) == 1 and body["grounded"] is False


QUIZ = {"questions": [
    {"prompt": "p1", "options": ["a", "b", "c"], "correct_index": 0, "concept": "x", "difficulty": "beginner", "explanation": "e"},
    {"prompt": "p2", "options": ["a", "b", "c"], "correct_index": 1, "concept": "y", "difficulty": "intermediate", "explanation": "e"},
]}


def test_diagnostic_then_score_roundtrip():
    c = client_with(ScriptedLLM(structured_queue=[QUIZ]))
    quiz = c.post("/v3/study/diagnostic", json={"topic": "piano"}).json()
    r = c.post("/v3/study/score", json={"quiz": quiz, "answers": [0, 2]})
    assert r.json() == {"score": 0.5, "correct": 1, "total": 2, "missed_concepts": ["y"], "level": "beginner"}
    assert c.post("/v3/study/score", json={"quiz": quiz, "answers": [0]}).status_code == 422


def test_flashcards_and_unknown_lesson():
    cards = {"cards": [{"front": "f", "back": "b", "concept": "c"}]}
    c = client_with(ScriptedLLM(structured_queue=[cards]))
    ok = c.post("/v3/study/flashcards", json={"lesson_url": "https://youtube.com/watch?v=v1", "n": 3})
    assert ok.status_code == 200 and ok.json()["cards"][0]["front"] == "f"
    assert c.post("/v3/study/flashcards", json={"lesson_url": "https://nope"}).status_code == 404


def test_review_roundtrip_advances_card():
    c = client_with(ScriptedLLM())
    first = c.post("/v3/study/review", json={"rating": 3}).json()
    assert first["interval_days"] >= 1 and first["card"]["reps"] == 1
    second = c.post("/v3/study/review", json={"card": first["card"], "rating": 3}).json()
    assert second["card"]["reps"] == 2 and second["card"]["stability"] > first["card"]["stability"]


def test_replan_endpoint():
    llm = ScriptedLLM([("search_resources", {"query": "x"}), ("submit_curriculum", {"curriculum": curriculum(module("Remedial"))})])
    r = client_with(llm).post("/v3/study/replan", json={
        "curriculum": curriculum(module("Basics")),
        "progress": {"Basics": {"completed": True, "quiz_score": 0.2, "missed_concepts": ["scales"]}},
    })
    assert r.status_code == 200 and r.json()["curriculum"]["modules"][0]["title"] == "Remedial"
