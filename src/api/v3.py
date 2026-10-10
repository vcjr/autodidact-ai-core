"""
v3 API: agentic curriculum, tutor, quizzes/flashcards, re-planning, spaced repetition.

Mounted by api_v2.py. All agent access goes through ``Depends`` providers in
``src.api.deps`` so tests can swap in fakes.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents import study_agent
from src.agents.curriculum_agent import CurriculumAgent, CurriculumResult
from src.agents.tutor_agent import TutorAgent, VerifiedReply
from src.api import deps
from src.learning import fsrs
from src.llm import LLMClient, LLMError, LLMRefusal
from src.models.curriculum_schema import Curriculum

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v3", tags=["v3"])


# ----------------------------------------------------------------- schemas
class CurriculumRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    user_level: Optional[str] = Field(None, max_length=50)
    learner_context: Optional[str] = Field(None, max_length=4000, description="e.g. diagnostic results")


class CurriculumResponseV3(BaseModel):
    curriculum: Curriculum
    markdown: str
    warnings: List[str]
    steps: int
    tool_calls: int


class TutorRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[Dict[str, str]] = Field(default_factory=list, max_length=40)
    lesson_url: Optional[str] = None
    domain_id: Optional[str] = None


class DiagnosticRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    n: int = Field(6, ge=3, le=12)


class ScoreRequest(BaseModel):
    quiz: study_agent.Quiz
    answers: List[Optional[int]]


class LessonRequest(BaseModel):
    lesson_url: str
    n: int = Field(8, ge=1, le=20)


class ReplanRequest(BaseModel):
    curriculum: Curriculum
    progress: Dict[str, Dict[str, Any]]


class ReviewRequest(BaseModel):
    card: Optional[Dict[str, Any]] = Field(None, description="Previous card state; omit for a new card")
    rating: int = Field(..., ge=1, le=4, description="1 Again, 2 Hard, 3 Good, 4 Easy")
    desired_retention: float = Field(0.9, ge=0.7, le=0.99)


# ----------------------------------------------------------------- helpers
def _result_payload(result: CurriculumResult) -> CurriculumResponseV3:
    if result.curriculum is None:
        raise HTTPException(
            status_code=422,
            detail="Couldn't build a validated curriculum from the current library. "
                   "Try a broader goal or index more content for this topic.",
        )
    return CurriculumResponseV3(
        curriculum=result.curriculum,
        markdown=result.to_markdown(),
        warnings=result.report.warnings if result.report else [],
        steps=result.run.steps,
        tool_calls=len(result.run.tool_calls),
    )


def _llm_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LLMRefusal):
        return HTTPException(status_code=422, detail="The model declined this request.")
    log.exception("LLM call failed")
    return HTTPException(status_code=502, detail="The AI provider failed. Please retry.")


def _lesson_text(lesson_url: str, retriever) -> str:
    data = retriever.collection.get(where={"source": lesson_url}, include=["documents"])
    docs = data.get("documents") or []
    if not docs:
        raise HTTPException(status_code=404, detail="Lesson not found in library.")
    return docs[0]


def _lesson_meta(lesson_url: str, retriever) -> str:
    data = retriever.collection.get(where={"source": lesson_url}, include=["metadatas"])
    metas = data.get("metadatas") or [{}]
    return (metas[0] or {}).get("title") or lesson_url


# --------------------------------------------------------------- curriculum
@router.post("/curriculum", response_model=CurriculumResponseV3)
def create_curriculum(req: CurriculumRequest, agent: CurriculumAgent = Depends(deps.curriculum_agent)):
    try:
        result = agent.generate(req.query, user_level=req.user_level, learner_context=req.learner_context)
    except LLMError as exc:
        raise _llm_errors(exc)
    return _result_payload(result)


@router.post("/curriculum/stream")
def stream_curriculum(req: CurriculumRequest, agent: CurriculumAgent = Depends(deps.curriculum_agent)):
    """Server-sent events: tool_call / tool_result / text progress, then one `result` or `error`."""
    q: "queue.Queue[Any]" = queue.Queue()
    done = object()

    def work() -> None:
        try:
            result = agent.generate(
                req.query, user_level=req.user_level, learner_context=req.learner_context, on_event=q.put
            )
            try:
                payload = _result_payload(result)
                q.put({"type": "result", **json.loads(payload.model_dump_json())})
            except HTTPException as exc:
                q.put({"type": "error", "message": exc.detail})
        except LLMRefusal:
            q.put({"type": "error", "message": "The model declined this request."})
        except Exception:
            log.exception("curriculum stream failed")
            q.put({"type": "error", "message": "Something went wrong generating your curriculum."})
        finally:
            q.put(done)

    threading.Thread(target=work, daemon=True).start()

    def events():
        while True:
            item = q.get()
            if item is done:
                break
            yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/study/replan", response_model=CurriculumResponseV3)
def replan(req: ReplanRequest, agent: CurriculumAgent = Depends(deps.curriculum_agent)):
    try:
        result = study_agent.replan(agent, req.curriculum, req.progress)
    except LLMError as exc:
        raise _llm_errors(exc)
    return _result_payload(result)


# -------------------------------------------------------------------- tutor
@router.post("/tutor", response_model=VerifiedReply)
def tutor(req: TutorRequest, agent: TutorAgent = Depends(deps.tutor_agent)):
    try:
        return agent.answer(
            req.question, history=req.history, lesson_url=req.lesson_url, domain_id=req.domain_id
        )
    except LLMError as exc:
        raise _llm_errors(exc)


# -------------------------------------------------------------------- study
@router.post("/study/diagnostic", response_model=study_agent.Quiz)
def diagnostic(req: DiagnosticRequest, model: LLMClient = Depends(deps.llm)):
    try:
        return study_agent.generate_diagnostic(model, req.topic, req.n)
    except LLMError as exc:
        raise _llm_errors(exc)


@router.post("/study/score")
def score(req: ScoreRequest):
    try:
        result = study_agent.score_quiz(req.quiz, req.answers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "score": result.score, "correct": result.correct, "total": result.total,
        "missed_concepts": result.missed_concepts, "level": result.level,
    }


@router.post("/study/quiz", response_model=study_agent.Quiz)
def lesson_quiz(req: LessonRequest, model: LLMClient = Depends(deps.llm), r=Depends(deps.retriever)):
    text = _lesson_text(req.lesson_url, r)
    try:
        return study_agent.generate_lesson_quiz(model, _lesson_meta(req.lesson_url, r), text, req.n)
    except LLMError as exc:
        raise _llm_errors(exc)


@router.post("/study/flashcards", response_model=study_agent.FlashcardSet)
def flashcards(req: LessonRequest, model: LLMClient = Depends(deps.llm), r=Depends(deps.retriever)):
    text = _lesson_text(req.lesson_url, r)
    try:
        return study_agent.generate_flashcards(model, _lesson_meta(req.lesson_url, r), text, req.n)
    except LLMError as exc:
        raise _llm_errors(exc)


@router.post("/study/review")
def review(req: ReviewRequest):
    """Apply one FSRS review. The client stores the returned card and sends it back next time."""
    card = fsrs.Card.from_dict(req.card) if req.card else fsrs.Card()
    updated = fsrs.review(card, req.rating, datetime.now(timezone.utc), req.desired_retention)
    return {"card": updated.to_dict(), "interval_days": (updated.due - updated.last_review).days}
