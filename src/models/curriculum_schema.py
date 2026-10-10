"""Structured curriculum returned by the agentic curriculum generator."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

DifficultyLevel = Literal["beginner", "intermediate", "advanced", "expert"]
DIFFICULTY_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}


class CurriculumResource(BaseModel):
    title: str
    url: str = Field(description="Must be a URL returned by search_resources; never invented")
    why: str = Field(description="Why this resource fits this module, in one or two sentences")


class CurriculumModule(BaseModel):
    title: str = Field(description="Unique module title")
    difficulty: DifficultyLevel
    estimated_hours: float = Field(description="Realistic study + practice time", gt=0)
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Titles of EARLIER modules this one builds on (empty for the first module)",
    )
    objectives: List[str] = Field(description="2-4 concrete, testable learning objectives")
    resources: List[CurriculumResource] = Field(description="1-4 resources from search results")
    practice: str = Field(description="A concrete exercise or project that proves the skill")
    why_it_matters: str = Field(description="How this module prepares the learner for what follows")


class Curriculum(BaseModel):
    title: str
    goal: str = Field(description="The learner's goal restated in one sentence")
    overview: str
    modules: List[CurriculumModule]
    next_steps: str

    @property
    def total_hours(self) -> float:
        return round(sum(m.estimated_hours for m in self.modules), 1)

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"**Goal:** {self.goal}", "", self.overview, ""]
        lines.append(f"**Modules:** {len(self.modules)} · **Total time:** ~{self.total_hours} hours\n")
        for i, m in enumerate(self.modules, 1):
            lines += [
                "---",
                f"## Module {i}: {m.title}",
                f"**Difficulty:** {m.difficulty} · **Time:** ~{m.estimated_hours}h",
                f"**Prerequisites:** {', '.join(m.prerequisites) if m.prerequisites else 'None'}",
                "",
                "### Objectives",
                *[f"- {o}" for o in m.objectives],
                "",
                "### Resources",
                *[f"- [{r.title}]({r.url}) — {r.why}" for r in m.resources],
                "",
                f"### Practice\n{m.practice}",
                "",
                f"### Why it matters\n{m.why_it_matters}",
                "",
            ]
        lines += ["---", "## Next steps", self.next_steps]
        return "\n".join(lines)
