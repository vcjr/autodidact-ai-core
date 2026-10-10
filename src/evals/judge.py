"""Optional LLM-as-judge for qualities deterministic checks cannot see."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from src.llm.types import LLMClient
from src.models.curriculum_schema import Curriculum


class JudgeVerdict(BaseModel):
    goal_fit: int = Field(ge=1, le=5, description="Does the path actually achieve the learner's stated goal?")
    sequencing: int = Field(ge=1, le=5, description="Is each module teachable given only the earlier ones?")
    level_fit: int = Field(ge=1, le=5, description="Right starting level and pace for the learner?")
    resource_choice: int = Field(ge=1, le=5, description="Do the chosen resources plausibly teach each module?")
    problems: List[str] = Field(description="Concrete problems, empty if none")


SYSTEM = (
    "You are a strict curriculum reviewer. Score each dimension 1-5 (3 = acceptable, 5 = excellent and rare). "
    "Judge only from the curriculum shown. List specific problems; do not praise."
)


def judge_curriculum(llm: LLMClient, query: str, user_level: str | None, curriculum: Curriculum) -> JudgeVerdict:
    prompt = (
        f"Learner request: {query}\nLevel: {user_level or 'unspecified'}\n\n"
        f"Curriculum:\n{curriculum.to_markdown()}"
    )
    return llm.structured(prompt, JudgeVerdict, system=SYSTEM, max_tokens=2048)
