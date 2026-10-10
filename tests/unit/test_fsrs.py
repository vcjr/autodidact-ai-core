from datetime import datetime, timedelta, timezone

import pytest

from src.learning.fsrs import AGAIN, EASY, GOOD, HARD, Card, next_interval, retrievability, review

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_forgetting_curve_is_90_percent_at_stability():
    assert retrievability(10, 10) == pytest.approx(0.9, abs=1e-9)
    assert retrievability(0, 10) == 1.0
    assert retrievability(20, 10) < retrievability(10, 10)


def test_interval_matches_stability_at_default_retention_and_scales():
    assert next_interval(10.0, 0.9) == 10
    assert next_interval(10.0, 0.8) > next_interval(10.0, 0.9) > next_interval(10.0, 0.95)
    assert next_interval(0.001) == 1


def test_first_review_initial_values_ordered_by_rating():
    cards = {r: review(Card(), r, T0) for r in (AGAIN, HARD, GOOD, EASY)}
    assert cards[AGAIN].stability < cards[HARD].stability < cards[GOOD].stability < cards[EASY].stability
    assert cards[AGAIN].difficulty > cards[GOOD].difficulty > cards[EASY].difficulty
    assert cards[AGAIN].lapses == 1 and cards[GOOD].lapses == 0
    assert cards[AGAIN].due == T0 + timedelta(days=1)


def test_successful_review_at_due_date_grows_stability_monotonically():
    card = review(Card(), GOOD, T0)
    now = card.due
    prev = card.stability
    for _ in range(4):
        card = review(card, GOOD, now)
        assert card.stability > prev
        prev, now = card.stability, card.due


def test_rating_ordering_on_reviewed_card():
    base = review(Card(), GOOD, T0)
    t = base.due
    out = {r: review(base, r, t) for r in (AGAIN, HARD, GOOD, EASY)}
    assert out[AGAIN].stability < out[HARD].stability < out[GOOD].stability < out[EASY].stability
    assert out[AGAIN].lapses == 1
    assert out[AGAIN].stability <= base.stability


def test_difficulty_stays_in_bounds_and_input_not_mutated():
    card = Card()
    snapshot = card.to_dict()
    now = T0
    for _ in range(30):
        card = review(card, AGAIN, now)
        now = card.due
        assert 1.0 <= card.difficulty <= 10.0
    assert Card().to_dict() == snapshot


def test_reviewing_early_helps_less_than_on_time():
    base = review(Card(), GOOD, T0)
    early = review(base, GOOD, T0 + timedelta(days=1))
    on_time = review(base, GOOD, base.due)
    assert early.stability < on_time.stability


def test_roundtrip_serialisation_and_bad_rating():
    c = review(Card(), GOOD, T0)
    assert Card.from_dict(c.to_dict()) == c
    with pytest.raises(ValueError):
        review(Card(), 5)
