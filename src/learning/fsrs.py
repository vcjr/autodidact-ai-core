"""
FSRS-4.5 spaced-repetition scheduler (pure Python, no dependencies).

Implements the published FSRS-4.5 memory model with the default parameters:
  - power-law forgetting curve  R(t, S) = (1 + (19/81) * t / S) ** -0.5   (R(S, S) = 0.9)
  - difficulty / stability updates after each review
  - next interval chosen for a target retention (default 90%)

Ratings: 1 = Again, 2 = Hard, 3 = Good, 4 = Easy.
Default weights are the published FSRS-4.5 defaults; they can be optimised per
learner later from review logs.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

W = (
    0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474,
    0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755,
)
DECAY = -0.5
FACTOR = 19 / 81
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
MAX_INTERVAL_DAYS = 36500


def _clamp_d(d: float) -> float:
    return min(max(d, 1.0), 10.0)


def retrievability(elapsed_days: float, stability: float) -> float:
    """Probability of recall after ``elapsed_days`` for a memory of given stability."""
    return (1 + FACTOR * max(elapsed_days, 0.0) / stability) ** DECAY


def next_interval(stability: float, desired_retention: float = 0.9) -> int:
    """Days until predicted recall drops to ``desired_retention`` (at least 1)."""
    days = stability / FACTOR * (desired_retention ** (1 / DECAY) - 1)
    return int(min(max(round(days), 1), MAX_INTERVAL_DAYS))


@dataclass
class Card:
    stability: float = 0.0
    difficulty: float = 0.0
    reps: int = 0
    lapses: int = 0
    last_review: Optional[datetime] = None
    due: Optional[datetime] = None

    @property
    def is_new(self) -> bool:
        return self.reps == 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["last_review"] = self.last_review.isoformat() if self.last_review else None
        d["due"] = self.due.isoformat() if self.due else None
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Card":
        def parse(v):
            return datetime.fromisoformat(v) if v else None

        return cls(
            stability=d.get("stability", 0.0),
            difficulty=d.get("difficulty", 0.0),
            reps=d.get("reps", 0),
            lapses=d.get("lapses", 0),
            last_review=parse(d.get("last_review")),
            due=parse(d.get("due")),
        )


def review(
    card: Card,
    rating: int,
    now: Optional[datetime] = None,
    desired_retention: float = 0.9,
) -> Card:
    """Return the updated card after a review (the input card is not mutated)."""
    if rating not in (AGAIN, HARD, GOOD, EASY):
        raise ValueError("rating must be 1 (Again), 2 (Hard), 3 (Good) or 4 (Easy)")
    now = now or datetime.now(timezone.utc)

    if card.is_new:
        stability = W[rating - 1]
        difficulty = _clamp_d(W[4] - W[5] * (rating - 3))
        lapses = card.lapses + (1 if rating == AGAIN else 0)
    else:
        elapsed = max((now - card.last_review).total_seconds() / 86400, 0.0) if card.last_review else 0.0
        r = retrievability(elapsed, card.stability)
        d0_good = W[4]  # D0(3)
        difficulty = _clamp_d(W[7] * d0_good + (1 - W[7]) * (card.difficulty - W[6] * (rating - 3)))
        if rating == AGAIN:
            stability = (
                W[11] * card.difficulty ** -W[12] * ((card.stability + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r))
            )
            # a lapse never yields a stability above the previous one
            stability = min(stability, card.stability)
            lapses = card.lapses + 1
        else:
            hard_penalty = W[15] if rating == HARD else 1.0
            easy_bonus = W[16] if rating == EASY else 1.0
            growth = (
                math.exp(W[8]) * (11 - card.difficulty) * card.stability ** -W[9]
                * (math.exp(W[10] * (1 - r)) - 1) * hard_penalty * easy_bonus
            )
            stability = card.stability * (1 + growth)
            lapses = card.lapses

    stability = max(stability, 0.01)
    due = now + timedelta(days=next_interval(stability, desired_retention) if rating != AGAIN else 1)
    return Card(
        stability=stability, difficulty=difficulty, reps=card.reps + 1,
        lapses=lapses, last_review=now, due=due,
    )
