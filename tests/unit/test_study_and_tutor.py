import pytest
from pydantic import ValidationError

from src.agents.study_agent import (
    Quiz, QuizQuestion, infer_level, replan, score_quiz, summarize_progress,
)
from src.agents.curriculum_agent import CurriculumAgent
from src.agents.tutor_agent import Citation, TutorAgent, TutorReply, verify_citations
from src.models.curriculum_schema import Curriculum
from src.retrieval import HybridRetriever
from tests.fakes import ScriptedLLM, make_corpus
from tests.unit.test_curriculum_agent import curriculum, module


def q(concept, level, correct=0):
    return QuizQuestion(prompt=concept, options=["a", "b", "c"], correct_index=correct,
                        concept=concept, difficulty=level, explanation="because")


def test_question_validates_correct_index():
    with pytest.raises(ValidationError):
        QuizQuestion(prompt="p", options=["a", "b", "c"], correct_index=3, concept="c", difficulty="beginner", explanation="e")


def test_scoring_and_level_inference():
    quiz = Quiz(questions=[q("a", "beginner"), q("b", "beginner"), q("c", "intermediate"), q("d", "advanced")])
    r = score_quiz(quiz, [0, 0, 0, 1])          # last one wrong
    assert r.correct == 3 and r.missed_concepts == ["d"] and r.level == "intermediate"
    assert score_quiz(quiz, [1, 1, 0, 0]).level == "beginner"
    assert score_quiz(quiz, [None, 0, 0, 0]).missed_concepts == ["a"]
    with pytest.raises(ValueError):
        score_quiz(quiz, [0])


def test_infer_level_needs_all_lower_levels_secure():
    assert infer_level({"beginner": [False, False], "advanced": [True, True]}) == "beginner"
    assert infer_level({"beginner": [True], "intermediate": [True], "advanced": [True]}) == "advanced"
    assert infer_level({}) == "beginner"


def test_summarize_progress_buckets():
    c = Curriculum.model_validate(curriculum(module("A"), module("B", "intermediate", ["A"]), module("C", "advanced", ["B"])))
    text = summarize_progress(c, {
        "A": {"completed": True, "quiz_score": 0.9},
        "B": {"completed": True, "quiz_score": 0.3, "missed_concepts": ["chords"]},
    })
    assert "Mastered" in text and "A" in text.split("Mastered")[1].splitlines()[0]
    assert "Struggling" in text and "chords" in text
    assert "Not yet started: C" in text


def test_replan_passes_progress_to_agent():
    c = Curriculum.model_validate(curriculum(module("A")))
    llm = ScriptedLLM([("search_resources", {"query": "x"}), ("submit_curriculum", {"curriculum": curriculum(module("Remedial"))})])
    agent = CurriculumAgent(llm, HybridRetriever(make_corpus()))
    result = replan(agent, c, {"A": {"completed": True, "quiz_score": 0.2, "missed_concepts": ["scales"]}})
    assert result.ok
    assert "re-plan" in llm.prompts[0] and "scales" in llm.prompts[0]


# ---- tutor ----------------------------------------------------------------
SOURCES = {"https://x.com/a": "Middle C sits near the centre of the keyboard.  It is the\nusual anchor for beginners."}


def test_verify_citations_keeps_only_real_quotes():
    reply = TutorReply(answer="a", citations=[
        Citation(url="https://x.com/a", quote="middle c sits near the centre"),
        Citation(url="https://x.com/a", quote="It is the usual anchor"),     # whitespace/newline tolerant
        Citation(url="https://x.com/a", quote="Middle C is always red"),      # fabricated
        Citation(url="https://other.com", quote="Middle C"),                  # wrong source
    ])
    v = verify_citations(reply, SOURCES)
    assert len(v.citations) == 2 and v.dropped_citations == 2 and v.grounded is False


def test_verified_reply_grounded_only_when_all_citations_survive():
    ok = verify_citations(TutorReply(answer="a", citations=[Citation(url="https://x.com/a", quote="Middle C sits")]), SOURCES)
    none = verify_citations(TutorReply(answer="a", citations=[]), SOURCES)
    assert ok.grounded and not none.grounded


def test_tutor_uses_whole_lesson_when_url_given_and_verifies():
    corpus = make_corpus()
    llm = ScriptedLLM(structured_queue=[TutorReply(answer="Try this", citations=[
        Citation(url="https://youtube.com/watch?v=v1", quote="middle c hand position"),
        Citation(url="https://youtube.com/watch?v=v1", quote="totally made up"),
    ])])
    tutor = TutorAgent(llm, HybridRetriever(corpus))
    reply = tutor.answer("where is middle c?", lesson_url="https://youtube.com/watch?v=v1",
                         history=[{"role": "learner", "content": "hi"}])
    assert len(reply.citations) == 1 and reply.dropped_citations == 1 and not reply.grounded
    assert "learn piano basics keys" in llm.prompts[0] and "learner: hi" in llm.prompts[0]


def test_tutor_refuses_to_guess_without_sources():
    tutor = TutorAgent(ScriptedLLM(), HybridRetriever(make_corpus()))
    # domain filter matches nothing -> no sources -> no LLM call
    reply = tutor.answer("anything", domain_id="NOPE")
    assert not reply.grounded and "won't guess" in reply.answer
